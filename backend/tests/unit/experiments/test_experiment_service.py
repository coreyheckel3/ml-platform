from uuid import UUID, uuid4

import pytest

from forgeml.modules.experiments.application.services import (
    CompleteExperimentRunCommand,
    CreateExperimentCommand,
    ExperimentTrackingService,
    LogExperimentArtifactCommand,
    LogExperimentMetricsCommand,
    StartExperimentRunCommand,
)
from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
)
from forgeml.platform.domain.errors import ConflictError, PermissionDeniedError
from forgeml.platform.security.rbac import Principal


class FakeExperimentRepository:
    def __init__(self) -> None:
        self.experiments: dict[UUID, Experiment] = {}
        self.runs: dict[UUID, ExperimentRun] = {}
        self.artifacts: list[ExperimentArtifact] = []

    def add_experiment(self, experiment: Experiment) -> Experiment:
        self.experiments[experiment.id] = experiment
        return experiment

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        return self.experiments.get(experiment_id)

    def list_experiments(self, organization_id: UUID, project_id: UUID) -> list[Experiment]:
        return [
            experiment
            for experiment in self.experiments.values()
            if experiment.organization_id == organization_id and experiment.project_id == project_id
        ]

    def experiment_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return any(
            experiment.organization_id == organization_id
            and experiment.project_id == project_id
            and experiment.slug == slug
            for experiment in self.experiments.values()
        )

    def add_run(self, run: ExperimentRun) -> ExperimentRun:
        self.runs[run.id] = run
        return run

    def get_run(self, run_id: UUID) -> ExperimentRun | None:
        return self.runs.get(run_id)

    def list_runs(self, experiment_id: UUID) -> list[ExperimentRun]:
        return [run for run in self.runs.values() if run.experiment_id == experiment_id]

    def update_run(self, run: ExperimentRun) -> ExperimentRun:
        self.runs[run.id] = run
        return run

    def add_artifact(self, artifact: ExperimentArtifact) -> ExperimentArtifact:
        self.artifacts.append(artifact)
        return artifact

    def list_artifacts(self, experiment_run_id: UUID) -> list[ExperimentArtifact]:
        return [
            artifact
            for artifact in self.artifacts
            if artifact.experiment_run_id == experiment_run_id
        ]


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_experiment_service_tracks_run_metrics_artifacts_and_completion() -> None:
    repository = FakeExperimentRepository()
    service = ExperimentTrackingService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(
        organization_id,
        user_id,
        {
            "experiments:create",
            "experiments:read",
            "experiment_runs:create",
            "experiment_runs:read",
            "experiment_runs:write",
            "experiment_artifacts:write",
        },
    )

    experiment = service.create_experiment(
        CreateExperimentCommand(
            organization_id=organization_id,
            project_id=project_id,
            owner_user_id=user_id,
            name="Fraud Risk Baseline",
            description="Baseline fraud models.",
        ),
        actor,
    )
    run = service.start_run(
        StartExperimentRunCommand(
            experiment_id=experiment.id,
            run_name="xgb-depth-6",
            model_type="xgboost",
            started_by=user_id,
            artifact_uri="s3://forgeml/experiments/run-1",
            dataset_version_id=uuid4(),
            feature_set_id=uuid4(),
            parameters={"max_depth": 6},
        ),
        actor,
    )
    measured = service.log_metrics(
        LogExperimentMetricsCommand(
            experiment_run_id=run.id,
            metrics={"auc": 0.94},
            evaluation_report={"threshold": 0.71},
        ),
        actor,
    )
    artifact = service.log_artifact(
        LogExperimentArtifactCommand(
            experiment_run_id=run.id,
            name="model",
            artifact_type="pickle",
            uri="s3://forgeml/experiments/run-1/model.pkl",
            metadata={"sha256": "abc"},
        ),
        actor,
    )
    completed = service.complete_run(
        CompleteExperimentRunCommand(
            experiment_run_id=run.id,
            status=ExperimentRunStatus.SUCCEEDED,
            metrics={"precision": 0.88},
            evaluation_report={"approved": True},
        ),
        actor,
    )

    assert experiment.slug == "fraud-risk-baseline"
    assert measured.metrics["auc"] == 0.94
    assert artifact.name == "model"
    assert completed.status == ExperimentRunStatus.SUCCEEDED
    assert completed.metrics["precision"] == 0.88


def test_experiment_service_rejects_duplicate_experiment_slug() -> None:
    repository = FakeExperimentRepository()
    service = ExperimentTrackingService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"experiments:create"})
    command = CreateExperimentCommand(
        organization_id=organization_id,
        project_id=project_id,
        owner_user_id=user_id,
        name="Movie Ranker",
    )

    service.create_experiment(command, actor)

    with pytest.raises(ConflictError):
        service.create_experiment(command, actor)


def test_experiment_service_requires_permissions() -> None:
    service = ExperimentTrackingService(repository=FakeExperimentRepository())
    organization_id = uuid4()
    user_id = uuid4()

    with pytest.raises(PermissionDeniedError):
        service.create_experiment(
            CreateExperimentCommand(
                organization_id=organization_id,
                project_id=uuid4(),
                owner_user_id=user_id,
                name="Semantic Search",
            ),
            principal(organization_id, user_id, {"experiments:read"}),
        )
