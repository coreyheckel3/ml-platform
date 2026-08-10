from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from forgeml.modules.administration.application.audit import record_user_audit_event
from forgeml.modules.administration.repositories.interfaces import AuditEventRecorder
from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.domain.entities import (
    TrainingExecutionResult,
    TrainingRun,
    TrainingRunEvent,
    TrainingRunLog,
    TrainingRunStatus,
)
from forgeml.modules.training.domain.policies import (
    validate_metrics,
    validate_run_name,
    validate_terminal_status,
    validate_training_log,
    validate_training_run_request,
)
from forgeml.modules.training.repositories.interfaces import (
    ExperimentRunRecorder,
    TrainingJobRunner,
    TrainingRunRepository,
    TrainingWorkflowOrchestrator,
)
from forgeml.platform.domain.errors import (
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.mlflow import (
    MLflowSyncResult,
    MLflowTrackingGateway,
    build_training_run_mlflow_record,
    failed_mlflow_sync_result,
    mlflow_sync_result_payload,
)
from forgeml.platform.observability.metrics import (
    mlflow_tracking_sync_total,
    training_worker_claims_total,
    training_worker_expired_leases_total,
    training_worker_heartbeats_total,
    training_worker_retries_total,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class TrainingRetryPolicy:
    max_attempts: int = 3
    base_backoff_seconds: int = 60
    max_backoff_seconds: int = 1_800
    lease_seconds: int = 900

    def lease_expires_at(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self.lease_seconds)

    def next_retry_at(self, now: datetime, attempt_count: int) -> datetime:
        exponent = max(attempt_count - 1, 0)
        delay_seconds = min(
            self.max_backoff_seconds,
            self.base_backoff_seconds * (2**exponent),
        )
        return now + timedelta(seconds=delay_seconds)


@dataclass(frozen=True)
class StartTrainingRunCommand:
    organization_id: UUID
    project_id: UUID
    experiment_id: UUID
    run_name: str
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    algorithm: str
    model_type: str
    objective_metric_name: str
    hyperparameters: dict[str, object]
    requested_by: UUID


@dataclass(frozen=True)
class RecordTrainingResultCommand:
    training_run_id: UUID
    status: TrainingRunStatus
    metrics: dict[str, float]
    evaluation_report: dict[str, object]
    error_message: str | None = None


@dataclass(frozen=True)
class ExecuteTrainingRunCommand:
    training_run_id: UUID


@dataclass(frozen=True)
class RecordTrainingHeartbeatCommand:
    training_run_id: UUID
    worker_id: str


@dataclass(frozen=True)
class ExecuteNextTrainingRunsCommand:
    organization_id: UUID
    project_id: UUID | None = None
    max_runs: int = 1
    worker_id: str = "local-training-worker"
    recover_expired_leases: bool = True


@dataclass(frozen=True)
class TrainingWorkerRunSummary:
    worker_id: str
    scanned: int
    executed: int
    succeeded: int
    failed: int
    skipped: int
    training_run_ids: list[UUID]
    retried: int = 0
    dead_lettered: int = 0
    expired_leases_requeued: int = 0
    expired_leases_dead_lettered: int = 0
    heartbeats: int = 0


class TrainingRunService:
    def __init__(
        self,
        *,
        training_runs: TrainingRunRepository,
        experiment_runs: ExperimentRunRecorder,
        orchestrator: TrainingWorkflowOrchestrator,
        artifact_bucket: str,
        runner: TrainingJobRunner | None = None,
        audit_log: AuditEventRecorder | None = None,
        retry_policy: TrainingRetryPolicy | None = None,
        mlflow_tracking: MLflowTrackingGateway | None = None,
        mlflow_experiment_prefix: str = "forgeml",
    ) -> None:
        self._training_runs = training_runs
        self._experiment_runs = experiment_runs
        self._orchestrator = orchestrator
        self._artifact_bucket = artifact_bucket
        self._runner = runner
        self._audit_log = audit_log
        self._retry_policy = retry_policy or TrainingRetryPolicy()
        self._mlflow_tracking = mlflow_tracking
        self._mlflow_experiment_prefix = mlflow_experiment_prefix
        _validate_retry_policy(self._retry_policy)

    def start_training_run(
        self,
        command: StartTrainingRunCommand,
        principal: Principal,
    ) -> TrainingRun:
        self._require(principal, "training_runs:create")
        self._require_same_organization(command.organization_id, principal)
        validate_run_name(command.run_name)
        validate_training_run_request(
            algorithm=command.algorithm,
            model_type=command.model_type,
            objective_metric_name=command.objective_metric_name,
            hyperparameters=command.hyperparameters,
            dataset_version_id=command.dataset_version_id,
            feature_set_id=command.feature_set_id,
        )
        if not self._training_runs.experiment_belongs_to_project(
            command.organization_id,
            command.project_id,
            command.experiment_id,
        ):
            raise ResourceNotFoundError("Experiment was not found.")
        has_dataset = _has_dataset_version_reference(command, self._training_runs)
        if command.dataset_version_id and not has_dataset:
            raise ResourceNotFoundError("Dataset version was not found.")
        if command.feature_set_id and not self._training_runs.feature_set_belongs_to_project(
            command.project_id,
            command.feature_set_id,
        ):
            raise ResourceNotFoundError("Feature set was not found.")

        now = _utcnow()
        training_run_id = uuid4()
        experiment_run_id = uuid4()
        artifact_uri = f"s3://{self._artifact_bucket}/training-runs/{training_run_id}"
        self._experiment_runs.add_experiment_run(
            ExperimentRun(
                id=experiment_run_id,
                experiment_id=command.experiment_id,
                project_id=command.project_id,
                run_name=command.run_name.strip(),
                status=ExperimentRunStatus.RUNNING,
                model_type=command.model_type.strip(),
                started_by=command.requested_by,
                dataset_version_id=command.dataset_version_id,
                feature_set_id=command.feature_set_id,
                parameters={
                    "algorithm": command.algorithm.strip(),
                    "objective_metric_name": command.objective_metric_name.strip(),
                    **command.hyperparameters,
                },
                metrics={},
                artifact_uri=artifact_uri,
                evaluation_report={},
                error_message=None,
            )
        )
        planned = TrainingRun(
            id=training_run_id,
            organization_id=command.organization_id,
            project_id=command.project_id,
            experiment_id=command.experiment_id,
            experiment_run_id=experiment_run_id,
            dataset_version_id=command.dataset_version_id,
            feature_set_id=command.feature_set_id,
            algorithm=command.algorithm.strip(),
            model_type=command.model_type.strip(),
            objective_metric_name=command.objective_metric_name.strip(),
            hyperparameters=command.hyperparameters,
            status=TrainingRunStatus.REQUESTED,
            requested_by=command.requested_by,
            artifact_uri=artifact_uri,
            orchestrator_run_id="",
            metrics={},
            error_message=None,
            attempt_count=0,
            max_attempts=self._retry_policy.max_attempts,
            queued_at=now,
        )
        orchestrator_run_id = self._orchestrator.trigger_training(planned)
        queued = replace(
            planned,
            status=TrainingRunStatus.QUEUED,
            orchestrator_run_id=orchestrator_run_id,
        )
        saved = self._training_runs.add_training_run(queued)
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=saved.id,
                event_type="queued",
                message="Training run was submitted to the workflow orchestrator.",
                metadata={"orchestrator_run_id": saved.orchestrator_run_id},
            )
        )
        self._record_log(
            training_run_id=saved.id,
            level="info",
            logger="training.scheduler",
            message="Training run was queued for execution.",
            metadata={
                "orchestrator_run_id": saved.orchestrator_run_id,
                "algorithm": saved.algorithm,
                "model_type": saved.model_type,
                "objective_metric_name": saved.objective_metric_name,
            },
        )
        record_user_audit_event(
            self._audit_log,
            organization_id=saved.organization_id,
            actor_id=command.requested_by,
            action="training_runs.queue",
            resource_type="training_run",
            resource_id=saved.id,
            metadata={
                "project_id": str(saved.project_id),
                "experiment_id": str(saved.experiment_id),
                "experiment_run_id": str(saved.experiment_run_id),
                "dataset_version_id": (
                    str(saved.dataset_version_id) if saved.dataset_version_id else None
                ),
                "feature_set_id": str(saved.feature_set_id) if saved.feature_set_id else None,
                "algorithm": saved.algorithm,
                "model_type": saved.model_type,
                "objective_metric_name": saved.objective_metric_name,
                "orchestrator_run_id": saved.orchestrator_run_id,
            },
        )
        return saved

    def list_training_runs(self, project_id: UUID, principal: Principal) -> list[TrainingRun]:
        self._require(principal, "training_runs:read")
        return self._training_runs.list_training_runs(UUID(principal.organization_id), project_id)

    def get_training_run(self, training_run_id: UUID, principal: Principal) -> TrainingRun:
        self._require(principal, "training_runs:read")
        return self._get_scoped_training_run(training_run_id, principal)

    def record_result(
        self,
        command: RecordTrainingResultCommand,
        principal: Principal,
    ) -> TrainingRun:
        self._require(principal, "training_runs:write")
        training_run = self._get_scoped_training_run(command.training_run_id, principal)
        return self._record_terminal_result(
            training_run,
            status=command.status,
            metrics=command.metrics,
            evaluation_report=command.evaluation_report,
            error_message=command.error_message,
        )

    def execute_training_run(
        self,
        command: ExecuteTrainingRunCommand,
        principal: Principal,
    ) -> TrainingRun:
        self._require(principal, "training_runs:write")
        training_run = self._get_scoped_training_run(command.training_run_id, principal)
        if training_run.status not in {
            TrainingRunStatus.REQUESTED,
            TrainingRunStatus.QUEUED,
        }:
            raise DomainValidationError("Only requested or queued training runs can execute.")
        if self._runner is None or not self._runner.can_run(training_run):
            raise DomainValidationError("No training runner is configured for this run.")

        return self._execute_claimed_training_run(
            training_run,
            worker_id="manual-training-execution",
        )

    def execute_next_training_runs(
        self,
        command: ExecuteNextTrainingRunsCommand,
        principal: Principal,
    ) -> TrainingWorkerRunSummary:
        self._require(principal, "training_runs:write")
        self._require_same_organization(command.organization_id, principal)
        if command.max_runs < 1 or command.max_runs > 100:
            raise DomainValidationError("Worker max_runs must be between 1 and 100.")
        if self._runner is None:
            raise DomainValidationError("No training runner is configured for this worker.")

        now = _utcnow()
        expired_leases_requeued = 0
        expired_leases_dead_lettered = 0
        if command.recover_expired_leases:
            expired_leases_requeued, expired_leases_dead_lettered = (
                self._recover_expired_training_run_leases(command, now=now)
            )
        candidates = self._training_runs.list_runnable_training_runs(
            command.organization_id,
            command.project_id,
            limit=command.max_runs * 10,
            now=now,
        )
        executed_runs: list[TrainingRun] = []
        skipped = 0
        for candidate in candidates:
            if len(executed_runs) >= command.max_runs:
                break
            if not self._runner.can_run(candidate):
                skipped += 1
                continue
            try:
                executed_runs.append(
                    self._execute_claimed_training_run(
                        candidate,
                        worker_id=command.worker_id,
                    )
                )
            except DomainValidationError:
                skipped += 1
        return TrainingWorkerRunSummary(
            worker_id=command.worker_id,
            scanned=len(candidates),
            executed=len(executed_runs),
            succeeded=sum(
                run.status == TrainingRunStatus.SUCCEEDED for run in executed_runs
            ),
            failed=sum(run.status == TrainingRunStatus.FAILED for run in executed_runs),
            skipped=skipped,
            training_run_ids=[run.id for run in executed_runs],
            retried=sum(
                run.status == TrainingRunStatus.QUEUED and run.next_retry_at is not None
                for run in executed_runs
            ),
            dead_lettered=sum(
                run.status == TrainingRunStatus.DEAD_LETTERED for run in executed_runs
            ),
            expired_leases_requeued=expired_leases_requeued,
            expired_leases_dead_lettered=expired_leases_dead_lettered,
            heartbeats=len(executed_runs),
        )

    def record_worker_heartbeat(
        self,
        command: RecordTrainingHeartbeatCommand,
        principal: Principal,
    ) -> TrainingRun:
        self._require(principal, "training_runs:write")
        training_run = self._get_scoped_training_run(command.training_run_id, principal)
        if training_run.status != TrainingRunStatus.RUNNING:
            raise DomainValidationError("Only running training runs can accept worker heartbeats.")
        heartbeat = self._heartbeat_claimed_training_run(
            training_run,
            worker_id=command.worker_id,
        )
        if heartbeat is None:
            raise DomainValidationError("Training run heartbeat was rejected.")
        return heartbeat

    def _execute_claimed_training_run(
        self,
        training_run: TrainingRun,
        *,
        worker_id: str,
    ) -> TrainingRun:
        if self._runner is None or not self._runner.can_run(training_run):
            raise DomainValidationError("No training runner is configured for this run.")
        now = _utcnow()
        claimed = self._training_runs.claim_training_run(
            training_run.id,
            worker_id=worker_id,
            lease_expires_at=self._retry_policy.lease_expires_at(now),
            heartbeat_at=now,
        )
        if claimed is None:
            training_worker_claims_total.labels(outcome="rejected").inc()
            raise DomainValidationError("Training run is no longer executable.")
        training_worker_claims_total.labels(outcome="claimed").inc()
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=claimed.id,
                event_type="running",
                message="Training run execution started.",
                metadata={
                    "orchestrator_run_id": claimed.orchestrator_run_id,
                    "worker_id": worker_id,
                },
            )
        )
        self._record_log(
            training_run_id=claimed.id,
            level="info",
            logger="training.worker",
            message="Worker claimed training run.",
            metadata={
                "worker_id": worker_id,
                "orchestrator_run_id": claimed.orchestrator_run_id,
                "attempt_count": claimed.attempt_count,
                "max_attempts": claimed.max_attempts,
                "lease_expires_at": _datetime_isoformat(claimed.lease_expires_at),
            },
        )
        heartbeat = self._heartbeat_claimed_training_run(claimed, worker_id=worker_id)
        if heartbeat is not None:
            claimed = heartbeat
        self._record_log(
            training_run_id=claimed.id,
            level="info",
            logger="training.runner",
            message="Training runner execution started.",
            metadata={
                "runner": self._runner.__class__.__name__,
                "algorithm": claimed.algorithm,
                "model_type": claimed.model_type,
            },
        )

        try:
            execution_result = self._runner.run(claimed)
            if execution_result.artifacts:
                self._record_log(
                    training_run_id=claimed.id,
                    level="info",
                    logger="training.artifacts",
                    message="Training runner produced artifacts.",
                    metadata={
                        "artifact_count": len(execution_result.artifacts),
                        "artifacts": [
                            {
                                "name": artifact.name,
                                "artifact_type": artifact.artifact_type,
                                "uri": artifact.uri,
                            }
                            for artifact in execution_result.artifacts
                        ],
                    },
                )
        except Exception as exc:  # noqa: BLE001
            self._record_log(
                training_run_id=claimed.id,
                level="error",
                logger="training.runner",
                message="Training runner raised an exception.",
                metadata={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "runner": self._runner.__class__.__name__,
                },
            )
            execution_result = TrainingExecutionResult(
                status=TrainingRunStatus.FAILED,
                metrics={},
                evaluation_report={},
                artifacts=[],
                runner_name=self._runner.__class__.__name__,
                external_run_id=claimed.orchestrator_run_id,
                error_message=str(exc),
            )
        if execution_result.status == TrainingRunStatus.FAILED:
            return self._schedule_retry_or_dead_letter(
                claimed,
                metrics=execution_result.metrics,
                evaluation_report=_with_execution_metadata(execution_result),
                error_message=execution_result.error_message or "Training runner failed.",
                worker_id=worker_id,
            )
        return self._record_terminal_result(
            claimed,
            status=execution_result.status,
            metrics=execution_result.metrics,
            evaluation_report=_with_execution_metadata(execution_result),
            error_message=execution_result.error_message,
        )

    def _heartbeat_claimed_training_run(
        self,
        training_run: TrainingRun,
        *,
        worker_id: str,
    ) -> TrainingRun | None:
        now = _utcnow()
        heartbeat = self._training_runs.heartbeat_training_run(
            training_run.id,
            worker_id=worker_id,
            lease_expires_at=self._retry_policy.lease_expires_at(now),
            heartbeat_at=now,
        )
        if heartbeat is None:
            training_worker_heartbeats_total.labels(outcome="rejected").inc()
            return None
        training_worker_heartbeats_total.labels(outcome="recorded").inc()
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=heartbeat.id,
                event_type="heartbeat",
                message="Training worker heartbeat was recorded.",
                metadata={
                    "worker_id": worker_id,
                    "last_heartbeat_at": _datetime_isoformat(heartbeat.last_heartbeat_at),
                    "lease_expires_at": _datetime_isoformat(heartbeat.lease_expires_at),
                },
            )
        )
        self._record_log(
            training_run_id=heartbeat.id,
            level="debug",
            logger="training.worker",
            message="Training worker heartbeat was recorded.",
            metadata={
                "worker_id": worker_id,
                "lease_expires_at": _datetime_isoformat(heartbeat.lease_expires_at),
            },
        )
        return heartbeat

    def _schedule_retry_or_dead_letter(
        self,
        training_run: TrainingRun,
        *,
        metrics: dict[str, float],
        evaluation_report: dict[str, object],
        error_message: str,
        worker_id: str,
    ) -> TrainingRun:
        validate_metrics(metrics)
        if training_run.attempt_count < training_run.max_attempts:
            now = _utcnow()
            next_retry_at = self._retry_policy.next_retry_at(now, training_run.attempt_count)
            retry = replace(
                training_run,
                status=TrainingRunStatus.QUEUED,
                metrics={**training_run.metrics, **metrics},
                error_message=error_message,
                worker_id=None,
                lease_expires_at=None,
                queued_at=now,
                completed_at=None,
                next_retry_at=next_retry_at,
            )
            saved = self._training_runs.update_training_run(retry)
            training_worker_retries_total.labels(outcome="scheduled").inc()
            self._training_runs.add_event(
                TrainingRunEvent(
                    id=uuid4(),
                    training_run_id=saved.id,
                    event_type="retry_scheduled",
                    message="Training run attempt failed and was scheduled for retry.",
                    metadata={
                        "worker_id": worker_id,
                        "attempt_count": saved.attempt_count,
                        "max_attempts": saved.max_attempts,
                        "next_retry_at": _datetime_isoformat(saved.next_retry_at),
                        "error_message": error_message,
                    },
                )
            )
            self._record_log(
                training_run_id=saved.id,
                level="warning",
                logger="training.retry",
                message="Training run attempt failed and was scheduled for retry.",
                metadata={
                    "worker_id": worker_id,
                    "attempt_count": saved.attempt_count,
                    "max_attempts": saved.max_attempts,
                    "next_retry_at": _datetime_isoformat(saved.next_retry_at),
                    "error_message": error_message,
                },
            )
            return saved

        training_worker_retries_total.labels(outcome="dead_lettered").inc()
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=training_run.id,
                event_type="retry_exhausted",
                message="Training run exhausted all retry attempts.",
                metadata={
                    "worker_id": worker_id,
                    "attempt_count": training_run.attempt_count,
                    "max_attempts": training_run.max_attempts,
                    "error_message": error_message,
                },
            )
        )
        return self._record_terminal_result(
            training_run,
            status=TrainingRunStatus.DEAD_LETTERED,
            metrics=metrics,
            evaluation_report=evaluation_report,
            error_message=error_message,
        )

    def _recover_expired_training_run_leases(
        self,
        command: ExecuteNextTrainingRunsCommand,
        *,
        now: datetime,
    ) -> tuple[int, int]:
        expired_runs = self._training_runs.list_expired_running_training_runs(
            command.organization_id,
            command.project_id,
            limit=command.max_runs * 10,
            now=now,
        )
        requeued = 0
        dead_lettered = 0
        for expired in expired_runs:
            if expired.attempt_count >= expired.max_attempts:
                training_worker_expired_leases_total.labels(outcome="dead_lettered").inc()
                self._training_runs.add_event(
                    TrainingRunEvent(
                        id=uuid4(),
                        training_run_id=expired.id,
                        event_type="lease_expired",
                        message="Training run lease expired after all attempts.",
                        metadata={
                            "worker_id": expired.worker_id,
                            "attempt_count": expired.attempt_count,
                            "max_attempts": expired.max_attempts,
                            "lease_expires_at": _datetime_isoformat(expired.lease_expires_at),
                        },
                    )
                )
                self._record_terminal_result(
                    expired,
                    status=TrainingRunStatus.DEAD_LETTERED,
                    metrics={},
                    evaluation_report={
                        "training_execution": {
                            "schema_version": "forgeml.training_execution_result.v1",
                            "runner_name": "expired-worker-lease",
                            "external_run_id": expired.orchestrator_run_id,
                            "artifacts": [],
                        }
                    },
                    error_message="Training run lease expired after all attempts.",
                )
                dead_lettered += 1
                continue

            next_retry_at = self._retry_policy.next_retry_at(now, expired.attempt_count)
            retry = replace(
                expired,
                status=TrainingRunStatus.QUEUED,
                error_message="Training run lease expired before completion.",
                worker_id=None,
                lease_expires_at=None,
                queued_at=now,
                completed_at=None,
                next_retry_at=next_retry_at,
            )
            saved = self._training_runs.update_training_run(retry)
            training_worker_expired_leases_total.labels(outcome="requeued").inc()
            self._training_runs.add_event(
                TrainingRunEvent(
                    id=uuid4(),
                    training_run_id=saved.id,
                    event_type="lease_expired",
                    message="Training run lease expired and was returned to the queue.",
                    metadata={
                        "previous_worker_id": expired.worker_id,
                        "attempt_count": saved.attempt_count,
                        "max_attempts": saved.max_attempts,
                        "lease_expires_at": _datetime_isoformat(expired.lease_expires_at),
                        "next_retry_at": _datetime_isoformat(saved.next_retry_at),
                    },
                )
            )
            self._record_log(
                training_run_id=saved.id,
                level="warning",
                logger="training.lease",
                message="Training run lease expired and was returned to the queue.",
                metadata={
                    "previous_worker_id": expired.worker_id,
                    "attempt_count": saved.attempt_count,
                    "max_attempts": saved.max_attempts,
                    "next_retry_at": _datetime_isoformat(saved.next_retry_at),
                },
            )
            requeued += 1
        return requeued, dead_lettered

    def cancel_training_run(self, training_run_id: UUID, principal: Principal) -> TrainingRun:
        self._require(principal, "training_runs:cancel")
        training_run = self._get_scoped_training_run(training_run_id, principal)
        self._orchestrator.cancel_training(training_run)
        canceled = replace(
            training_run,
            status=TrainingRunStatus.CANCELED,
            worker_id=None,
            lease_expires_at=None,
            completed_at=_utcnow(),
            next_retry_at=None,
        )
        saved = self._training_runs.update_training_run(canceled)
        self._experiment_runs.update_experiment_run(
            saved.experiment_run_id,
            ExperimentRunStatus.CANCELED,
            saved.metrics,
            {},
            "Training run was canceled.",
        )
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=saved.id,
                event_type="canceled",
                message="Training run was canceled.",
                metadata={"orchestrator_run_id": saved.orchestrator_run_id},
            )
        )
        self._record_log(
            training_run_id=saved.id,
            level="warning",
            logger="training.scheduler",
            message="Training run was canceled.",
            metadata={
                "orchestrator_run_id": saved.orchestrator_run_id,
                "previous_status": training_run.status.value,
            },
        )
        record_user_audit_event(
            self._audit_log,
            organization_id=saved.organization_id,
            actor_id=principal.user_id,
            action="training_runs.cancel",
            resource_type="training_run",
            resource_id=saved.id,
            metadata={
                "project_id": str(saved.project_id),
                "experiment_id": str(saved.experiment_id),
                "experiment_run_id": str(saved.experiment_run_id),
                "orchestrator_run_id": saved.orchestrator_run_id,
                "previous_status": training_run.status.value,
                "status": saved.status.value,
            },
        )
        return saved

    def list_events(
        self,
        training_run_id: UUID,
        principal: Principal,
    ) -> list[TrainingRunEvent]:
        self._require(principal, "training_runs:read")
        training_run = self._get_scoped_training_run(training_run_id, principal)
        return self._training_runs.list_events(training_run.id)

    def list_logs(
        self,
        training_run_id: UUID,
        principal: Principal,
    ) -> list[TrainingRunLog]:
        self._require(principal, "training_runs:read")
        training_run = self._get_scoped_training_run(training_run_id, principal)
        return self._training_runs.list_logs(training_run.id)

    def _get_scoped_training_run(
        self,
        training_run_id: UUID,
        principal: Principal,
    ) -> TrainingRun:
        training_run = self._training_runs.get_training_run(training_run_id)
        if training_run is None or str(training_run.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Training run was not found.")
        return training_run

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage training runs.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage training runs in another organization.")

    def _record_terminal_result(
        self,
        training_run: TrainingRun,
        *,
        status: TrainingRunStatus,
        metrics: dict[str, float],
        evaluation_report: dict[str, object],
        error_message: str | None,
    ) -> TrainingRun:
        validate_terminal_status(status)
        validate_metrics(metrics)
        now = _utcnow()
        updated = replace(
            training_run,
            status=status,
            metrics={**training_run.metrics, **metrics},
            error_message=error_message,
            worker_id=None,
            lease_expires_at=None,
            completed_at=now,
            next_retry_at=None,
        )
        saved = self._training_runs.update_training_run(updated)
        experiment_run = self._experiment_runs.update_experiment_run(
            saved.experiment_run_id,
            _to_experiment_status(status),
            saved.metrics,
            evaluation_report,
            error_message,
        )
        synced_evaluation_report = self._sync_mlflow_tracking(
            training_run=saved,
            experiment_run=experiment_run,
            status=status,
            evaluation_report=evaluation_report,
        )
        if synced_evaluation_report != evaluation_report:
            self._experiment_runs.update_experiment_run(
                saved.experiment_run_id,
                _to_experiment_status(status),
                saved.metrics,
                synced_evaluation_report,
                error_message,
            )
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=saved.id,
                event_type=status.value,
                message=f"Training run finished with status {status.value}.",
                metadata={"metrics": saved.metrics},
            )
        )
        self._record_log(
            training_run_id=saved.id,
            level=_terminal_log_level(status),
            logger="training.lifecycle",
            message=f"Training run finished with status {status.value}.",
            metadata={
                "status": status.value,
                "metrics": saved.metrics,
                "error_message": error_message,
            },
        )
        return saved

    def _sync_mlflow_tracking(
        self,
        *,
        training_run: TrainingRun,
        experiment_run: ExperimentRun,
        status: TrainingRunStatus,
        evaluation_report: dict[str, object],
    ) -> dict[str, object]:
        if self._mlflow_tracking is None:
            return evaluation_report

        record = build_training_run_mlflow_record(
            experiment_prefix=self._mlflow_experiment_prefix,
            organization_id=training_run.organization_id,
            project_id=training_run.project_id,
            experiment_id=training_run.experiment_id,
            experiment_run_id=training_run.experiment_run_id,
            training_run_id=training_run.id,
            run_name=experiment_run.run_name,
            status=status.value,
            started_at=training_run.started_at,
            completed_at=training_run.completed_at,
            artifact_uri=training_run.artifact_uri,
            algorithm=training_run.algorithm,
            model_type=training_run.model_type,
            objective_metric_name=training_run.objective_metric_name,
            parameters=experiment_run.parameters,
            metrics=training_run.metrics,
            evaluation_report=evaluation_report,
        )
        try:
            result = self._mlflow_tracking.sync_training_run(record)
            mlflow_tracking_sync_total.labels(outcome=result.status).inc()
            self._record_mlflow_sync_observability(training_run, result, level="info")
        except Exception as exc:  # noqa: BLE001
            result = failed_mlflow_sync_result(
                tracking_uri=getattr(self._mlflow_tracking, "_tracking_uri", ""),
                experiment_name=record.experiment_name,
                error_message=str(exc),
            )
            mlflow_tracking_sync_total.labels(outcome="failed").inc()
            self._record_mlflow_sync_observability(training_run, result, level="error")

        return {
            **evaluation_report,
            "mlflow_sync": mlflow_sync_result_payload(result),
        }

    def _record_mlflow_sync_observability(
        self,
        training_run: TrainingRun,
        result: MLflowSyncResult,
        *,
        level: str,
    ) -> None:
        payload = mlflow_sync_result_payload(result)
        event_type = (
            "mlflow_synced" if result.status == "synced" else f"mlflow_sync_{result.status}"
        )
        message = (
            "Training run was synced to MLflow."
            if result.status == "synced"
            else f"Training run MLflow sync finished with status {result.status}."
        )
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=training_run.id,
                event_type=event_type,
                message=message,
                metadata=payload,
            )
        )
        self._record_log(
            training_run_id=training_run.id,
            level=level,
            logger="training.mlflow",
            message=message,
            metadata=payload,
        )

    def _record_log(
        self,
        *,
        training_run_id: UUID,
        level: str,
        logger: str,
        message: str,
        metadata: dict[str, object],
    ) -> TrainingRunLog:
        sequence = self._training_runs.next_log_sequence(training_run_id)
        validate_training_log(
            sequence=sequence,
            level=level,
            logger=logger,
            message=message,
            metadata=metadata,
        )
        return self._training_runs.add_log(
            TrainingRunLog(
                id=uuid4(),
                training_run_id=training_run_id,
                sequence=sequence,
                level=level,
                logger=logger,
                message=message.strip(),
                metadata=metadata,
            )
        )


def _to_experiment_status(status: TrainingRunStatus) -> ExperimentRunStatus:
    if status == TrainingRunStatus.SUCCEEDED:
        return ExperimentRunStatus.SUCCEEDED
    if status in {TrainingRunStatus.FAILED, TrainingRunStatus.DEAD_LETTERED}:
        return ExperimentRunStatus.FAILED
    return ExperimentRunStatus.CANCELED


def _terminal_log_level(status: TrainingRunStatus) -> str:
    if status in {TrainingRunStatus.FAILED, TrainingRunStatus.DEAD_LETTERED}:
        return "error"
    if status == TrainingRunStatus.CANCELED:
        return "warning"
    return "info"


def _has_dataset_version_reference(
    command: StartTrainingRunCommand,
    training_runs: TrainingRunRepository,
) -> bool:
    if command.dataset_version_id is None:
        return False
    return training_runs.dataset_version_belongs_to_project(
        command.project_id,
        command.dataset_version_id,
    )


def _with_execution_metadata(result: TrainingExecutionResult) -> dict[str, object]:
    return {
        **result.evaluation_report,
        "training_execution": {
            "schema_version": "forgeml.training_execution_result.v1",
            "runner_name": result.runner_name,
            "external_run_id": result.external_run_id,
            "artifacts": [asdict(artifact) for artifact in result.artifacts],
        },
    }


def _validate_retry_policy(policy: TrainingRetryPolicy) -> None:
    if policy.max_attempts < 1 or policy.max_attempts > 100:
        raise ValueError("Training retry max_attempts must be between 1 and 100.")
    if policy.base_backoff_seconds < 0:
        raise ValueError("Training retry base_backoff_seconds cannot be negative.")
    if policy.max_backoff_seconds < policy.base_backoff_seconds:
        raise ValueError(
            "Training retry max_backoff_seconds must be greater than base_backoff_seconds."
        )
    if policy.lease_seconds < 1:
        raise ValueError("Training worker lease_seconds must be positive.")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _datetime_isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
