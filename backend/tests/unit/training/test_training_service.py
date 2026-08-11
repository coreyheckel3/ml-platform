from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from forgeml.modules.administration.domain.entities import AuditLogEntry, AuditLogEvent
from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.application.services import (
    ExecuteNextTrainingRunsCommand,
    ExecuteTrainingRunCommand,
    RecordTrainingHeartbeatCommand,
    RecordTrainingResultCommand,
    StartTrainingRunCommand,
    TrainingRetryPolicy,
    TrainingRunService,
)
from forgeml.modules.training.domain.entities import (
    TrainingArtifact,
    TrainingExecutionResult,
    TrainingOrchestrationStatus,
    TrainingRun,
    TrainingRunEvent,
    TrainingRunLog,
    TrainingRunStatus,
)
from forgeml.platform.domain.errors import (
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.mlflow import MLflowRunRecord, MLflowSyncResult
from forgeml.platform.security.rbac import Principal


class FakeTrainingRunRepository:
    def __init__(self) -> None:
        self.training_runs: dict[UUID, TrainingRun] = {}
        self.events: list[TrainingRunEvent] = []
        self.logs: list[TrainingRunLog] = []
        self.experiments: set[tuple[UUID, UUID, UUID]] = set()
        self.dataset_versions: set[tuple[UUID, UUID]] = set()
        self.feature_sets: set[tuple[UUID, UUID]] = set()

    def add_training_run(self, training_run: TrainingRun) -> TrainingRun:
        self.training_runs[training_run.id] = training_run
        return training_run

    def get_training_run(self, training_run_id: UUID) -> TrainingRun | None:
        return self.training_runs.get(training_run_id)

    def list_training_runs(self, organization_id: UUID, project_id: UUID) -> list[TrainingRun]:
        return [
            run
            for run in self.training_runs.values()
            if run.organization_id == organization_id and run.project_id == project_id
        ]

    def list_runnable_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        runs = [
            run
            for run in self.training_runs.values()
            if run.organization_id == organization_id
            and run.status in {TrainingRunStatus.REQUESTED, TrainingRunStatus.QUEUED}
            and (run.next_retry_at is None or run.next_retry_at <= now)
            and (project_id is None or run.project_id == project_id)
        ]
        return runs[:limit]

    def list_expired_running_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        runs = [
            run
            for run in self.training_runs.values()
            if run.organization_id == organization_id
            and run.status == TrainingRunStatus.RUNNING
            and run.lease_expires_at is not None
            and run.lease_expires_at <= now
            and (project_id is None or run.project_id == project_id)
        ]
        return runs[:limit]

    def claim_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        training_run = self.training_runs.get(training_run_id)
        if training_run is None or training_run.status not in {
            TrainingRunStatus.REQUESTED,
            TrainingRunStatus.QUEUED,
        }:
            return None
        if training_run.next_retry_at is not None and training_run.next_retry_at > heartbeat_at:
            return None
        claimed = replace(
            training_run,
            status=TrainingRunStatus.RUNNING,
            attempt_count=training_run.attempt_count + 1,
            worker_id=worker_id,
            lease_expires_at=lease_expires_at,
            last_heartbeat_at=heartbeat_at,
            started_at=heartbeat_at,
            completed_at=None,
            next_retry_at=None,
        )
        self.training_runs[training_run_id] = claimed
        return claimed

    def heartbeat_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        training_run = self.training_runs.get(training_run_id)
        if (
            training_run is None
            or training_run.status != TrainingRunStatus.RUNNING
            or training_run.worker_id != worker_id
        ):
            return None
        heartbeat = replace(
            training_run,
            lease_expires_at=lease_expires_at,
            last_heartbeat_at=heartbeat_at,
        )
        self.training_runs[training_run_id] = heartbeat
        return heartbeat

    def update_training_run(self, training_run: TrainingRun) -> TrainingRun:
        self.training_runs[training_run.id] = training_run
        return training_run

    def add_event(self, event: TrainingRunEvent) -> TrainingRunEvent:
        self.events.append(event)
        return event

    def list_events(self, training_run_id: UUID) -> list[TrainingRunEvent]:
        return [event for event in self.events if event.training_run_id == training_run_id]

    def add_log(self, log: TrainingRunLog) -> TrainingRunLog:
        self.logs.append(log)
        return log

    def next_log_sequence(self, training_run_id: UUID) -> int:
        sequences = [log.sequence for log in self.logs if log.training_run_id == training_run_id]
        return (max(sequences) if sequences else 0) + 1

    def list_logs(self, training_run_id: UUID) -> list[TrainingRunLog]:
        return [log for log in self.logs if log.training_run_id == training_run_id]

    def experiment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
    ) -> bool:
        return (organization_id, project_id, experiment_id) in self.experiments

    def dataset_version_belongs_to_project(self, project_id: UUID, version_id: UUID) -> bool:
        return (project_id, version_id) in self.dataset_versions

    def feature_set_belongs_to_project(self, project_id: UUID, feature_set_id: UUID) -> bool:
        return (project_id, feature_set_id) in self.feature_sets


class FakeExperimentRunRecorder:
    def __init__(self) -> None:
        self.runs: dict[UUID, ExperimentRun] = {}

    def add_experiment_run(self, run: ExperimentRun) -> ExperimentRun:
        self.runs[run.id] = run
        return run

    def update_experiment_run(
        self,
        run_id: UUID,
        status: ExperimentRunStatus,
        metrics: dict[str, float],
        evaluation_report: dict[str, object],
        error_message: str | None,
    ) -> ExperimentRun:
        run = self.runs[run_id]
        updated = ExperimentRun(
            id=run.id,
            experiment_id=run.experiment_id,
            project_id=run.project_id,
            run_name=run.run_name,
            status=status,
            model_type=run.model_type,
            started_by=run.started_by,
            dataset_version_id=run.dataset_version_id,
            feature_set_id=run.feature_set_id,
            parameters=run.parameters,
            metrics=metrics,
            artifact_uri=run.artifact_uri,
            evaluation_report=evaluation_report,
            error_message=error_message,
        )
        self.runs[run_id] = updated
        return updated


class FakeOrchestrator:
    def trigger_training(self, training_run: TrainingRun) -> str:
        return f"workflow:{training_run.id}"

    def cancel_training(self, training_run: TrainingRun) -> str:
        return f"cancel:{training_run.id}"

    def get_training_status(self, training_run: TrainingRun) -> TrainingOrchestrationStatus:
        return TrainingOrchestrationStatus(
            training_run_id=training_run.id,
            orchestrator_run_id=training_run.orchestrator_run_id,
            orchestrator="fake",
            external_status=training_run.status.value,
            mapped_training_status=training_run.status,
            is_terminal=training_run.status
            in {
                TrainingRunStatus.SUCCEEDED,
                TrainingRunStatus.FAILED,
                TrainingRunStatus.CANCELED,
                TrainingRunStatus.DEAD_LETTERED,
            },
            external_url="http://orchestrator.local/runs/workflow-1",
            metadata={"source": "fake-orchestrator"},
            observed_at=datetime.now(tz=UTC),
        )


class FakeRunner:
    def __init__(self, *, can_run: bool = True, should_fail: bool = False) -> None:
        self._can_run = can_run
        self._should_fail = should_fail

    def can_run(self, training_run: TrainingRun) -> bool:
        return self._can_run and training_run.algorithm == "xgboost"

    def run(self, training_run: TrainingRun) -> TrainingExecutionResult:
        if self._should_fail:
            raise RuntimeError("runner failed")
        artifact_uri = "file:///training-artifacts/model.json"
        artifact_path = "/training-artifacts/model.json"
        return TrainingExecutionResult(
            status=TrainingRunStatus.SUCCEEDED,
            metrics={"auc": 0.95},
            evaluation_report={"model_card": {"training_rows": 8}},
            artifacts=[
                TrainingArtifact(
                    name="model",
                    artifact_type="model",
                    uri=artifact_uri,
                    media_type="application/json",
                    metadata={"local_path": artifact_path},
                )
            ],
            runner_name="fake-runner",
            external_run_id=f"fake:{training_run.id}",
        )


class FakeMLflowTrackingGateway:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.records: list[MLflowRunRecord] = []

    def sync_training_run(self, record: MLflowRunRecord) -> MLflowSyncResult:
        self.records.append(record)
        if self.should_fail:
            raise RuntimeError("mlflow unavailable")
        return MLflowSyncResult(
            tracking_uri="memory://forgeml",
            experiment_name=record.experiment_name,
            run_id=f"mlflow:{record.training_run_id}",
            status="synced",
            logged_param_count=len(record.parameters),
            logged_metric_count=len(record.metrics),
            logged_artifact_count=len(record.artifacts),
        )


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.events: list[AuditLogEvent] = []

    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        self.events.append(event)
        return AuditLogEntry(
            id=uuid4(),
            organization_id=event.organization_id,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata=event.metadata,
            created_at=datetime.now(UTC),
        )


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


@dataclass(frozen=True)
class StartedTrainingRunContext:
    repository: FakeTrainingRunRepository
    recorder: FakeExperimentRunRecorder
    service: TrainingRunService
    actor: Principal
    organization_id: UUID
    project_id: UUID
    training_run: TrainingRun


def started_training_run_context(
    *,
    runner: FakeRunner | None,
    retry_policy: TrainingRetryPolicy | None = None,
    mlflow_tracking: FakeMLflowTrackingGateway | None = None,
) -> StartedTrainingRunContext:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        runner=runner,
        retry_policy=retry_policy,
        mlflow_tracking=mlflow_tracking,
        mlflow_experiment_prefix="forgeml-test",
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:read", "training_runs:write"},
    )
    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-depth-6",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={"max_depth": 6},
            requested_by=user_id,
        ),
        actor,
    )
    return StartedTrainingRunContext(
        repository=repository,
        recorder=recorder,
        service=service,
        actor=actor,
        organization_id=organization_id,
        project_id=project_id,
        training_run=training_run,
    )


def test_training_service_creates_linked_experiment_run_and_records_result() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    audit_log = FakeAuditLogRepository()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        audit_log=audit_log,
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:read", "training_runs:write"},
    )

    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-depth-6",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={"max_depth": 6},
            requested_by=user_id,
        ),
        actor,
    )
    completed = service.record_result(
        RecordTrainingResultCommand(
            training_run_id=training_run.id,
            status=TrainingRunStatus.SUCCEEDED,
            metrics={"auc": 0.94},
            evaluation_report={"confusion_matrix": [[90, 4], [6, 30]]},
        ),
        actor,
    )

    assert training_run.status == TrainingRunStatus.QUEUED
    assert training_run.orchestrator_run_id.startswith("workflow:")
    assert recorder.runs[training_run.experiment_run_id].parameters["max_depth"] == 6
    assert completed.metrics["auc"] == 0.94
    assert recorder.runs[training_run.experiment_run_id].status == ExperimentRunStatus.SUCCEEDED
    assert repository.events[0].event_type == "queued"
    assert [event.action for event in audit_log.events] == ["training_runs.queue"]
    assert audit_log.events[0].resource_id == str(training_run.id)
    assert audit_log.events[0].metadata["algorithm"] == "xgboost"


def test_training_service_records_cancel_audit_event() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    audit_log = FakeAuditLogRepository()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        audit_log=audit_log,
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:cancel"},
    )
    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-cancel",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={},
            requested_by=user_id,
        ),
        actor,
    )

    canceled = service.cancel_training_run(training_run.id, actor)

    assert canceled.status == TrainingRunStatus.CANCELED
    assert [event.action for event in audit_log.events] == [
        "training_runs.queue",
        "training_runs.cancel",
    ]
    cancel_event = audit_log.events[-1]
    assert cancel_event.resource_id == str(training_run.id)
    assert cancel_event.metadata["previous_status"] == "queued"
    assert cancel_event.metadata["status"] == "canceled"


def test_training_service_executes_queued_run_with_runner() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        runner=FakeRunner(),
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:read", "training_runs:write"},
    )
    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-depth-6",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={"max_depth": 6},
            requested_by=user_id,
        ),
        actor,
    )

    completed = service.execute_training_run(
        ExecuteTrainingRunCommand(training_run_id=training_run.id),
        actor,
    )

    evaluation_report = recorder.runs[training_run.experiment_run_id].evaluation_report
    assert completed.status == TrainingRunStatus.SUCCEEDED
    assert completed.metrics["auc"] == 0.95
    assert evaluation_report["training_execution"]["schema_version"] == (
        "forgeml.training_execution_result.v1"
    )
    assert evaluation_report["training_execution"]["artifacts"][0]["name"] == "model"
    assert completed.attempt_count == 1
    assert completed.worker_id is None
    assert completed.completed_at is not None
    assert [event.event_type for event in repository.events] == [
        "queued",
        "running",
        "heartbeat",
        "succeeded",
    ]
    assert [log.sequence for log in service.list_logs(training_run.id, actor)] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert [log.message for log in repository.logs] == [
        "Training run was queued for execution.",
        "Worker claimed training run.",
        "Training worker heartbeat was recorded.",
        "Training runner execution started.",
        "Training runner produced artifacts.",
        "Training run finished with status succeeded.",
    ]
    assert repository.logs[-1].metadata["metrics"] == {"auc": 0.95}


def test_training_service_syncs_terminal_run_to_mlflow() -> None:
    mlflow_tracking = FakeMLflowTrackingGateway()
    context = started_training_run_context(
        runner=FakeRunner(),
        mlflow_tracking=mlflow_tracking,
    )

    completed = context.service.execute_training_run(
        ExecuteTrainingRunCommand(training_run_id=context.training_run.id),
        context.actor,
    )

    evaluation_report = context.recorder.runs[
        context.training_run.experiment_run_id
    ].evaluation_report
    assert completed.status == TrainingRunStatus.SUCCEEDED
    assert len(mlflow_tracking.records) == 1
    record = mlflow_tracking.records[0]
    assert record.experiment_name.startswith("forgeml-test/organizations/")
    assert record.metrics == {"auc": 0.95}
    assert record.parameters["max_depth"] == "6"
    assert record.artifacts[0].name == "model"
    assert evaluation_report["mlflow_sync"]["status"] == "synced"
    assert evaluation_report["mlflow_sync"]["logged_artifact_count"] == 1
    assert "mlflow_synced" in [event.event_type for event in context.repository.events]
    assert "Training run was synced to MLflow." in [
        log.message for log in context.repository.logs
    ]


def test_training_service_records_mlflow_failure_without_failing_training_run() -> None:
    mlflow_tracking = FakeMLflowTrackingGateway(should_fail=True)
    context = started_training_run_context(
        runner=FakeRunner(),
        mlflow_tracking=mlflow_tracking,
    )

    completed = context.service.execute_training_run(
        ExecuteTrainingRunCommand(training_run_id=context.training_run.id),
        context.actor,
    )

    evaluation_report = context.recorder.runs[
        context.training_run.experiment_run_id
    ].evaluation_report
    assert completed.status == TrainingRunStatus.SUCCEEDED
    assert len(mlflow_tracking.records) == 1
    assert evaluation_report["mlflow_sync"]["status"] == "failed"
    assert evaluation_report["mlflow_sync"]["error_message"] == "mlflow unavailable"
    assert "mlflow_sync_failed" in [event.event_type for event in context.repository.events]
    assert context.repository.logs[-2].logger == "training.mlflow"
    assert context.repository.logs[-2].level == "error"


def test_training_service_polls_orchestration_status() -> None:
    context = started_training_run_context(runner=FakeRunner())

    status = context.service.get_orchestration_status(context.training_run.id, context.actor)

    assert status.training_run_id == context.training_run.id
    assert status.orchestrator == "fake"
    assert status.external_status == "queued"
    assert status.mapped_training_status == TrainingRunStatus.QUEUED
    assert status.is_terminal is False
    assert status.external_url == "http://orchestrator.local/runs/workflow-1"


def test_training_service_rejects_execution_without_matching_runner() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        runner=FakeRunner(can_run=False),
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:write"},
    )
    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-depth-6",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={},
            requested_by=user_id,
        ),
        actor,
    )

    with pytest.raises(DomainValidationError):
        service.execute_training_run(
            ExecuteTrainingRunCommand(training_run_id=training_run.id),
            actor,
        )

    assert repository.training_runs[training_run.id].status == TrainingRunStatus.QUEUED


def test_training_service_worker_executes_next_supported_queued_run() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        runner=FakeRunner(),
    )
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    user_id = uuid4()
    repository.experiments.add((organization_id, project_id, experiment_id))
    repository.dataset_versions.add((project_id, dataset_version_id))
    actor = principal(
        organization_id,
        user_id,
        {"training_runs:create", "training_runs:write"},
    )
    unsupported_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-lightgbm-baseline",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="lightgbm",
            model_type="lightgbm",
            objective_metric_name="auc",
            hyperparameters={},
            requested_by=user_id,
        ),
        actor,
    )
    supported_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
            run_name="fraud-xgb-depth-6",
            dataset_version_id=dataset_version_id,
            feature_set_id=None,
            algorithm="xgboost",
            model_type="xgboost",
            objective_metric_name="auc",
            hyperparameters={"max_depth": 6},
            requested_by=user_id,
        ),
        actor,
    )

    summary = service.execute_next_training_runs(
        ExecuteNextTrainingRunsCommand(
            organization_id=organization_id,
            project_id=project_id,
            max_runs=1,
            worker_id="worker-a",
        ),
        actor,
    )

    assert summary.scanned == 2
    assert summary.executed == 1
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.skipped == 1
    assert summary.heartbeats == 1
    assert summary.retried == 0
    assert summary.dead_lettered == 0
    assert summary.training_run_ids == [supported_run.id]
    assert repository.training_runs[unsupported_run.id].status == TrainingRunStatus.QUEUED
    assert repository.training_runs[supported_run.id].status == TrainingRunStatus.SUCCEEDED
    running_events = [event for event in repository.events if event.event_type == "running"]
    assert running_events[0].metadata["worker_id"] == "worker-a"


def test_training_service_worker_schedules_retry_for_failed_attempt() -> None:
    context = started_training_run_context(
        runner=FakeRunner(should_fail=True),
        retry_policy=TrainingRetryPolicy(
            max_attempts=3,
            base_backoff_seconds=60,
            max_backoff_seconds=60,
            lease_seconds=30,
        ),
    )

    summary = context.service.execute_next_training_runs(
        ExecuteNextTrainingRunsCommand(
            organization_id=context.organization_id,
            project_id=context.project_id,
            max_runs=1,
            worker_id="worker-a",
        ),
        context.actor,
    )

    retry = context.repository.training_runs[context.training_run.id]
    assert summary.executed == 1
    assert summary.retried == 1
    assert summary.dead_lettered == 0
    assert retry.status == TrainingRunStatus.QUEUED
    assert retry.attempt_count == 1
    assert retry.worker_id is None
    assert retry.lease_expires_at is None
    assert retry.next_retry_at is not None
    assert context.recorder.runs[retry.experiment_run_id].status == ExperimentRunStatus.RUNNING
    assert "retry_scheduled" in [event.event_type for event in context.repository.events]
    assert context.repository.logs[-1].message == (
        "Training run attempt failed and was scheduled for retry."
    )


def test_training_service_worker_dead_letters_after_retry_budget() -> None:
    context = started_training_run_context(
        runner=FakeRunner(should_fail=True),
        retry_policy=TrainingRetryPolicy(
            max_attempts=1,
            base_backoff_seconds=0,
            max_backoff_seconds=0,
            lease_seconds=30,
        ),
    )

    summary = context.service.execute_next_training_runs(
        ExecuteNextTrainingRunsCommand(
            organization_id=context.organization_id,
            project_id=context.project_id,
            max_runs=1,
            worker_id="worker-a",
        ),
        context.actor,
    )

    dead_lettered = context.repository.training_runs[context.training_run.id]
    assert summary.executed == 1
    assert summary.retried == 0
    assert summary.dead_lettered == 1
    assert dead_lettered.status == TrainingRunStatus.DEAD_LETTERED
    assert dead_lettered.attempt_count == 1
    assert dead_lettered.completed_at is not None
    assert dead_lettered.worker_id is None
    assert context.recorder.runs[dead_lettered.experiment_run_id].status == (
        ExperimentRunStatus.FAILED
    )
    assert [event.event_type for event in context.repository.events][-2:] == [
        "retry_exhausted",
        "dead_lettered",
    ]


def test_training_service_records_worker_heartbeat() -> None:
    context = started_training_run_context(runner=FakeRunner())
    heartbeat_at = datetime.now(tz=UTC)
    running = replace(
        context.training_run,
        status=TrainingRunStatus.RUNNING,
        attempt_count=1,
        worker_id="worker-a",
        lease_expires_at=heartbeat_at + timedelta(seconds=30),
        last_heartbeat_at=heartbeat_at,
    )
    context.repository.training_runs[running.id] = running

    heartbeat = context.service.record_worker_heartbeat(
        RecordTrainingHeartbeatCommand(
            training_run_id=running.id,
            worker_id="worker-a",
        ),
        context.actor,
    )

    assert heartbeat.status == TrainingRunStatus.RUNNING
    assert heartbeat.worker_id == "worker-a"
    assert heartbeat.last_heartbeat_at is not None
    assert heartbeat.lease_expires_at is not None
    assert context.repository.events[-1].event_type == "heartbeat"


def test_training_service_recovers_expired_running_lease() -> None:
    context = started_training_run_context(runner=FakeRunner(can_run=False))
    expired_at = datetime.now(tz=UTC) - timedelta(seconds=5)
    running = replace(
        context.training_run,
        status=TrainingRunStatus.RUNNING,
        attempt_count=1,
        worker_id="worker-a",
        lease_expires_at=expired_at,
        last_heartbeat_at=expired_at - timedelta(seconds=30),
    )
    context.repository.training_runs[running.id] = running

    summary = context.service.execute_next_training_runs(
        ExecuteNextTrainingRunsCommand(
            organization_id=context.organization_id,
            project_id=context.project_id,
            max_runs=1,
            worker_id="worker-b",
        ),
        context.actor,
    )

    recovered = context.repository.training_runs[running.id]
    assert summary.expired_leases_requeued == 1
    assert summary.expired_leases_dead_lettered == 0
    assert summary.executed == 0
    assert recovered.status == TrainingRunStatus.QUEUED
    assert recovered.worker_id is None
    assert recovered.lease_expires_at is None
    assert recovered.next_retry_at is not None
    assert context.repository.events[-1].event_type == "lease_expired"


def test_training_service_dead_letters_expired_lease_after_retry_budget() -> None:
    context = started_training_run_context(
        runner=FakeRunner(can_run=False),
        retry_policy=TrainingRetryPolicy(max_attempts=1, lease_seconds=30),
    )
    expired_at = datetime.now(tz=UTC) - timedelta(seconds=5)
    running = replace(
        context.training_run,
        status=TrainingRunStatus.RUNNING,
        attempt_count=1,
        max_attempts=1,
        worker_id="worker-a",
        lease_expires_at=expired_at,
        last_heartbeat_at=expired_at - timedelta(seconds=30),
    )
    context.repository.training_runs[running.id] = running

    summary = context.service.execute_next_training_runs(
        ExecuteNextTrainingRunsCommand(
            organization_id=context.organization_id,
            project_id=context.project_id,
            max_runs=1,
            worker_id="worker-b",
        ),
        context.actor,
    )

    recovered = context.repository.training_runs[running.id]
    assert summary.expired_leases_requeued == 0
    assert summary.expired_leases_dead_lettered == 1
    assert recovered.status == TrainingRunStatus.DEAD_LETTERED
    assert recovered.completed_at is not None
    assert context.recorder.runs[recovered.experiment_run_id].status == (
        ExperimentRunStatus.FAILED
    )


def test_training_service_worker_validates_batch_size() -> None:
    service = TrainingRunService(
        training_runs=FakeTrainingRunRepository(),
        experiment_runs=FakeExperimentRunRecorder(),
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
        runner=FakeRunner(),
    )
    organization_id = uuid4()

    with pytest.raises(DomainValidationError):
        service.execute_next_training_runs(
            ExecuteNextTrainingRunsCommand(organization_id=organization_id, max_runs=0),
            principal(organization_id, uuid4(), {"training_runs:write"}),
        )


def test_training_service_rejects_unknown_experiment() -> None:
    service = TrainingRunService(
        training_runs=FakeTrainingRunRepository(),
        experiment_runs=FakeExperimentRunRecorder(),
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
    )
    organization_id = uuid4()
    user_id = uuid4()

    with pytest.raises(ResourceNotFoundError):
        service.start_training_run(
            StartTrainingRunCommand(
                organization_id=organization_id,
                project_id=uuid4(),
                experiment_id=uuid4(),
                run_name="fraud-xgb-depth-6",
                dataset_version_id=uuid4(),
                feature_set_id=None,
                algorithm="xgboost",
                model_type="xgboost",
                objective_metric_name="auc",
                hyperparameters={},
                requested_by=user_id,
            ),
            principal(organization_id, user_id, {"training_runs:create"}),
        )


def test_training_service_requires_permissions() -> None:
    service = TrainingRunService(
        training_runs=FakeTrainingRunRepository(),
        experiment_runs=FakeExperimentRunRecorder(),
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
    )
    organization_id = uuid4()
    user_id = uuid4()

    with pytest.raises(PermissionDeniedError):
        service.list_training_runs(
            uuid4(),
            principal(organization_id, user_id, {"training_runs:create"}),
        )
