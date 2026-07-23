from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.application.services import (
    ExecuteNextTrainingRunsCommand,
    ExecuteTrainingRunCommand,
    RecordTrainingResultCommand,
    StartTrainingRunCommand,
    TrainingRunService,
)
from forgeml.modules.training.domain.entities import (
    TrainingArtifact,
    TrainingExecutionResult,
    TrainingRun,
    TrainingRunEvent,
    TrainingRunStatus,
)
from forgeml.platform.domain.errors import (
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


class FakeTrainingRunRepository:
    def __init__(self) -> None:
        self.training_runs: dict[UUID, TrainingRun] = {}
        self.events: list[TrainingRunEvent] = []
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
    ) -> list[TrainingRun]:
        runs = [
            run
            for run in self.training_runs.values()
            if run.organization_id == organization_id
            and run.status in {TrainingRunStatus.REQUESTED, TrainingRunStatus.QUEUED}
            and (project_id is None or run.project_id == project_id)
        ]
        return runs[:limit]

    def claim_training_run(self, training_run_id: UUID) -> TrainingRun | None:
        training_run = self.training_runs.get(training_run_id)
        if training_run is None or training_run.status not in {
            TrainingRunStatus.REQUESTED,
            TrainingRunStatus.QUEUED,
        }:
            return None
        claimed = replace(training_run, status=TrainingRunStatus.RUNNING)
        self.training_runs[training_run_id] = claimed
        return claimed

    def update_training_run(self, training_run: TrainingRun) -> TrainingRun:
        self.training_runs[training_run.id] = training_run
        return training_run

    def add_event(self, event: TrainingRunEvent) -> TrainingRunEvent:
        self.events.append(event)
        return event

    def list_events(self, training_run_id: UUID) -> list[TrainingRunEvent]:
        return [event for event in self.events if event.training_run_id == training_run_id]

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


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_training_service_creates_linked_experiment_run_and_records_result() -> None:
    repository = FakeTrainingRunRepository()
    recorder = FakeExperimentRunRecorder()
    service = TrainingRunService(
        training_runs=repository,
        experiment_runs=recorder,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
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
    assert [event.event_type for event in repository.events] == [
        "queued",
        "running",
        "succeeded",
    ]


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
    assert summary.training_run_ids == [supported_run.id]
    assert repository.training_runs[unsupported_run.id].status == TrainingRunStatus.QUEUED
    assert repository.training_runs[supported_run.id].status == TrainingRunStatus.SUCCEEDED
    running_events = [event for event in repository.events if event.event_type == "running"]
    assert running_events[0].metadata["worker_id"] == "worker-a"


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
