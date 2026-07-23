from typing import Protocol
from uuid import UUID

from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
)


class ExperimentRepository(Protocol):
    def add_experiment(self, experiment: Experiment) -> Experiment:
        raise NotImplementedError

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        raise NotImplementedError

    def list_experiments(self, organization_id: UUID, project_id: UUID) -> list[Experiment]:
        raise NotImplementedError

    def experiment_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        raise NotImplementedError

    def add_run(self, run: ExperimentRun) -> ExperimentRun:
        raise NotImplementedError

    def get_run(self, run_id: UUID) -> ExperimentRun | None:
        raise NotImplementedError

    def list_runs(self, experiment_id: UUID) -> list[ExperimentRun]:
        raise NotImplementedError

    def update_run(self, run: ExperimentRun) -> ExperimentRun:
        raise NotImplementedError

    def add_artifact(self, artifact: ExperimentArtifact) -> ExperimentArtifact:
        raise NotImplementedError

    def list_artifacts(self, experiment_run_id: UUID) -> list[ExperimentArtifact]:
        raise NotImplementedError
