from datetime import datetime
from typing import Protocol
from uuid import UUID

from forgeml.modules.experiments.domain.entities import ExperimentRun, ExperimentRunStatus
from forgeml.modules.training.domain.entities import (
    TrainingExecutionResult,
    TrainingOrchestrationStatus,
    TrainingRun,
    TrainingRunEvent,
    TrainingRunLog,
)


class TrainingRunRepository(Protocol):
    def add_training_run(self, training_run: TrainingRun) -> TrainingRun:
        raise NotImplementedError

    def get_training_run(self, training_run_id: UUID) -> TrainingRun | None:
        raise NotImplementedError

    def list_training_runs(self, organization_id: UUID, project_id: UUID) -> list[TrainingRun]:
        raise NotImplementedError

    def list_runnable_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        raise NotImplementedError

    def list_expired_running_training_runs(
        self,
        organization_id: UUID,
        project_id: UUID | None,
        limit: int,
        now: datetime,
    ) -> list[TrainingRun]:
        raise NotImplementedError

    def claim_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        raise NotImplementedError

    def heartbeat_training_run(
        self,
        training_run_id: UUID,
        *,
        worker_id: str,
        lease_expires_at: datetime,
        heartbeat_at: datetime,
    ) -> TrainingRun | None:
        raise NotImplementedError

    def update_training_run(self, training_run: TrainingRun) -> TrainingRun:
        raise NotImplementedError

    def add_event(self, event: TrainingRunEvent) -> TrainingRunEvent:
        raise NotImplementedError

    def list_events(self, training_run_id: UUID) -> list[TrainingRunEvent]:
        raise NotImplementedError

    def add_log(self, log: TrainingRunLog) -> TrainingRunLog:
        raise NotImplementedError

    def next_log_sequence(self, training_run_id: UUID) -> int:
        raise NotImplementedError

    def list_logs(self, training_run_id: UUID) -> list[TrainingRunLog]:
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

    def get_training_status(self, training_run: TrainingRun) -> TrainingOrchestrationStatus:
        raise NotImplementedError


class TrainingJobRunner(Protocol):
    def can_run(self, training_run: TrainingRun) -> bool:
        raise NotImplementedError

    def run(self, training_run: TrainingRun) -> TrainingExecutionResult:
        raise NotImplementedError
