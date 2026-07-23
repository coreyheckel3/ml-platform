from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class TrainingRunStatus(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class TrainingRun:
    id: UUID
    organization_id: UUID
    project_id: UUID
    experiment_id: UUID
    experiment_run_id: UUID
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    algorithm: str
    model_type: str
    objective_metric_name: str
    hyperparameters: dict[str, object]
    status: TrainingRunStatus
    requested_by: UUID
    artifact_uri: str
    orchestrator_run_id: str
    metrics: dict[str, float]
    error_message: str | None


@dataclass(frozen=True)
class TrainingRunEvent:
    id: UUID
    training_run_id: UUID
    event_type: str
    message: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class TrainingArtifact:
    name: str
    artifact_type: str
    uri: str
    media_type: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class TrainingExecutionResult:
    status: TrainingRunStatus
    metrics: dict[str, float]
    evaluation_report: dict[str, object]
    artifacts: list[TrainingArtifact]
    runner_name: str
    external_run_id: str
    error_message: str | None = None
