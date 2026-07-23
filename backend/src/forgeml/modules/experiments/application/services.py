from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.modules.experiments.domain.policies import (
    build_experiment_slug,
    normalize_model_type,
    validate_artifact,
    validate_experiment_name,
    validate_run_name,
    validate_tracking_payload,
)
from forgeml.modules.experiments.repositories.interfaces import ExperimentRepository
from forgeml.platform.domain.errors import (
    ConflictError,
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateExperimentCommand:
    organization_id: UUID
    project_id: UUID
    owner_user_id: UUID
    name: str
    description: str = ""


@dataclass(frozen=True)
class StartExperimentRunCommand:
    experiment_id: UUID
    run_name: str
    model_type: str
    started_by: UUID
    artifact_uri: str
    dataset_version_id: UUID | None = None
    feature_set_id: UUID | None = None
    parameters: dict[str, object] | None = None


@dataclass(frozen=True)
class LogExperimentMetricsCommand:
    experiment_run_id: UUID
    metrics: dict[str, float]
    evaluation_report: dict[str, object] | None = None


@dataclass(frozen=True)
class LogExperimentArtifactCommand:
    experiment_run_id: UUID
    name: str
    artifact_type: str
    uri: str
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class CompleteExperimentRunCommand:
    experiment_run_id: UUID
    status: ExperimentRunStatus
    metrics: dict[str, float] | None = None
    evaluation_report: dict[str, object] | None = None
    error_message: str | None = None


class ExperimentTrackingService:
    def __init__(self, *, repository: ExperimentRepository) -> None:
        self._repository = repository

    def create_experiment(
        self,
        command: CreateExperimentCommand,
        principal: Principal,
    ) -> Experiment:
        self._require(principal, "experiments:create")
        self._require_same_organization(command.organization_id, principal)
        validate_experiment_name(command.name)
        slug = build_experiment_slug(command.name)
        if self._repository.experiment_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("An experiment with this name already exists in the project.")

        experiment = Experiment(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            owner_user_id=command.owner_user_id,
            status=ExperimentStatus.ACTIVE,
        )
        return self._repository.add_experiment(experiment)

    def list_experiments(self, project_id: UUID, principal: Principal) -> list[Experiment]:
        self._require(principal, "experiments:read")
        return self._repository.list_experiments(UUID(principal.organization_id), project_id)

    def get_experiment(self, experiment_id: UUID, principal: Principal) -> Experiment:
        self._require(principal, "experiments:read")
        return self._get_scoped_experiment(experiment_id, principal)

    def start_run(
        self,
        command: StartExperimentRunCommand,
        principal: Principal,
    ) -> ExperimentRun:
        self._require(principal, "experiment_runs:create")
        experiment = self._get_scoped_experiment(command.experiment_id, principal)
        validate_run_name(command.run_name)
        model_type = normalize_model_type(command.model_type)
        parameters = command.parameters or {}
        validate_tracking_payload(parameters)
        if len(command.artifact_uri.strip()) < 3:
            raise DomainValidationError("Experiment run artifact URI is required.")

        run = ExperimentRun(
            id=uuid4(),
            experiment_id=experiment.id,
            project_id=experiment.project_id,
            run_name=command.run_name.strip(),
            status=ExperimentRunStatus.RUNNING,
            model_type=model_type,
            started_by=command.started_by,
            dataset_version_id=command.dataset_version_id,
            feature_set_id=command.feature_set_id,
            parameters=parameters,
            metrics={},
            artifact_uri=command.artifact_uri.strip(),
            evaluation_report={},
            error_message=None,
        )
        return self._repository.add_run(run)

    def list_runs(self, experiment_id: UUID, principal: Principal) -> list[ExperimentRun]:
        self._require(principal, "experiment_runs:read")
        experiment = self._get_scoped_experiment(experiment_id, principal)
        return self._repository.list_runs(experiment.id)

    def get_run(self, run_id: UUID, principal: Principal) -> ExperimentRun:
        self._require(principal, "experiment_runs:read")
        return self._get_scoped_run(run_id, principal)

    def log_metrics(
        self,
        command: LogExperimentMetricsCommand,
        principal: Principal,
    ) -> ExperimentRun:
        self._require(principal, "experiment_runs:write")
        run = self._get_scoped_run(command.experiment_run_id, principal)
        validate_tracking_payload(run.parameters, command.metrics)
        updated_metrics = {
            **run.metrics,
            **{key: float(value) for key, value in command.metrics.items()},
        }
        updated = replace(
            run,
            metrics=updated_metrics,
            evaluation_report=command.evaluation_report or run.evaluation_report,
        )
        return self._repository.update_run(updated)

    def log_artifact(
        self,
        command: LogExperimentArtifactCommand,
        principal: Principal,
    ) -> ExperimentArtifact:
        self._require(principal, "experiment_artifacts:write")
        run = self._get_scoped_run(command.experiment_run_id, principal)
        validate_artifact(command.name, command.artifact_type, command.uri)
        artifact = ExperimentArtifact(
            id=uuid4(),
            experiment_run_id=run.id,
            name=command.name.strip(),
            artifact_type=command.artifact_type.strip(),
            uri=command.uri.strip(),
            metadata=command.metadata or {},
        )
        return self._repository.add_artifact(artifact)

    def list_artifacts(
        self,
        experiment_run_id: UUID,
        principal: Principal,
    ) -> list[ExperimentArtifact]:
        self._require(principal, "experiment_runs:read")
        run = self._get_scoped_run(experiment_run_id, principal)
        return self._repository.list_artifacts(run.id)

    def complete_run(
        self,
        command: CompleteExperimentRunCommand,
        principal: Principal,
    ) -> ExperimentRun:
        self._require(principal, "experiment_runs:write")
        run = self._get_scoped_run(command.experiment_run_id, principal)
        if command.status not in {
            ExperimentRunStatus.SUCCEEDED,
            ExperimentRunStatus.FAILED,
            ExperimentRunStatus.CANCELED,
        }:
            raise DomainValidationError("Experiment run can only complete to a terminal status.")
        validate_tracking_payload(run.parameters, command.metrics or {})
        updated_metrics = {
            **run.metrics,
            **{key: float(value) for key, value in (command.metrics or {}).items()},
        }
        updated = replace(
            run,
            status=command.status,
            metrics=updated_metrics,
            evaluation_report=command.evaluation_report or run.evaluation_report,
            error_message=command.error_message,
        )
        return self._repository.update_run(updated)

    def _get_scoped_experiment(self, experiment_id: UUID, principal: Principal) -> Experiment:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None or str(experiment.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Experiment was not found.")
        return experiment

    def _get_scoped_run(self, run_id: UUID, principal: Principal) -> ExperimentRun:
        run = self._repository.get_run(run_id)
        if run is None:
            raise ResourceNotFoundError("Experiment run was not found.")
        self._get_scoped_experiment(run.experiment_id, principal)
        return run

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage experiments.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage experiments in another organization.")
