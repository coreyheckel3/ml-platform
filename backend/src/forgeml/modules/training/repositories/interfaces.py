from typing import Protocol
from uuid import UUID

from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.domain.entities import TrainingRun, TrainingRunEvent


class TrainingRunRepository(Protocol):
    def add_training_run(self, training_run: TrainingRun) -> TrainingRun:
        raise NotImplementedError

    def get_training_run(self, training_run_id: UUID) -> TrainingRun | None:
        raise NotImplementedError

    def list_training_runs(self, organization_id: UUID, project_id: UUID) -> list[TrainingRun]:
        raise NotImplementedError

    def update_training_run(self, training_run: TrainingRun) -> TrainingRun:
        raise NotImplementedError

    def add_event(self, event: TrainingRunEvent) -> TrainingRunEvent:
        raise NotImplementedError

    def list_events(self, training_run_id: UUID) -> list[TrainingRunEvent]:
        raise NotImplementedError

    def experiment_belongs_to_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
    ) -> bool:
        raise NotImplementedError

    def dataset_version_belongs_to_project(self, project_id: UUID, version_id: UUID) -> bool:
        raise NotImplementedError

    def feature_set_belongs_to_project(self, project_id: UUID, feature_set_id: UUID) -> bool:
        raise NotImplementedError


class ExperimentRunRecorder(Protocol):
    def add_experiment_run(self, run: ExperimentRun) -> ExperimentRun:
        raise NotImplementedError

    def update_experiment_run(
        self,
        run_id: UUID,
        status: ExperimentRunStatus,
        metrics: dict[str, float],
        evaluation_report: dict[str, object],
        error_message: str | None,
    ) -> ExperimentRun:
        raise NotImplementedError


class TrainingWorkflowOrchestrator(Protocol):
    def trigger_training(self, training_run: TrainingRun) -> str:
        raise NotImplementedError

    def cancel_training(self, training_run: TrainingRun) -> str:
        raise NotImplementedError
