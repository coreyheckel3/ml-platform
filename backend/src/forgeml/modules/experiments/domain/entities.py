from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ExperimentStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExperimentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class Experiment:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    owner_user_id: UUID
    status: ExperimentStatus


@dataclass(frozen=True)
class ExperimentRun:
    id: UUID
    experiment_id: UUID
    project_id: UUID
    run_name: str
    status: ExperimentRunStatus
    model_type: str
    started_by: UUID
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    parameters: dict[str, object]
    metrics: dict[str, float]
    artifact_uri: str
    evaluation_report: dict[str, object]
    error_message: str | None


@dataclass(frozen=True)
class ExperimentArtifact:
    id: UUID
    experiment_run_id: UUID
    name: str
    artifact_type: str
    uri: str
    metadata: dict[str, object]
