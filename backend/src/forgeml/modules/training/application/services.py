from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.domain.entities import (
    TrainingRun,
    TrainingRunEvent,
    TrainingRunStatus,
)
from forgeml.modules.training.domain.policies import (
    validate_metrics,
    validate_run_name,
    validate_terminal_status,
    validate_training_run_request,
)
from forgeml.modules.training.repositories.interfaces import (
    ExperimentRunRecorder,
    TrainingRunRepository,
    TrainingWorkflowOrchestrator,
)
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.security.rbac import Principal


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


class TrainingRunService:
    def __init__(
        self,
        *,
        training_runs: TrainingRunRepository,
        experiment_runs: ExperimentRunRecorder,
        orchestrator: TrainingWorkflowOrchestrator,
        artifact_bucket: str,
    ) -> None:
        self._training_runs = training_runs
        self._experiment_runs = experiment_runs
        self._orchestrator = orchestrator
        self._artifact_bucket = artifact_bucket

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
        validate_terminal_status(command.status)
        validate_metrics(command.metrics)
        updated = replace(
            training_run,
            status=command.status,
            metrics={**training_run.metrics, **command.metrics},
            error_message=command.error_message,
        )
        saved = self._training_runs.update_training_run(updated)
        self._experiment_runs.update_experiment_run(
            saved.experiment_run_id,
            _to_experiment_status(command.status),
            saved.metrics,
            command.evaluation_report,
            command.error_message,
        )
        self._training_runs.add_event(
            TrainingRunEvent(
                id=uuid4(),
                training_run_id=saved.id,
                event_type=command.status.value,
                message=f"Training run finished with status {command.status.value}.",
                metadata={"metrics": saved.metrics},
            )
        )
        return saved

    def cancel_training_run(self, training_run_id: UUID, principal: Principal) -> TrainingRun:
        self._require(principal, "training_runs:cancel")
        training_run = self._get_scoped_training_run(training_run_id, principal)
        self._orchestrator.cancel_training(training_run)
        canceled = replace(training_run, status=TrainingRunStatus.CANCELED)
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
        return saved

    def list_events(
        self,
        training_run_id: UUID,
        principal: Principal,
    ) -> list[TrainingRunEvent]:
        self._require(principal, "training_runs:read")
        training_run = self._get_scoped_training_run(training_run_id, principal)
        return self._training_runs.list_events(training_run.id)

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


def _to_experiment_status(status: TrainingRunStatus) -> ExperimentRunStatus:
    if status == TrainingRunStatus.SUCCEEDED:
        return ExperimentRunStatus.SUCCEEDED
    if status == TrainingRunStatus.FAILED:
        return ExperimentRunStatus.FAILED
    return ExperimentRunStatus.CANCELED


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
