from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RegisteredModelStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ModelVersionStatus(StrEnum):
    CANDIDATE = "candidate"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ModelApprovalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RegisteredModel:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    task_type: str
    owner_user_id: UUID
    status: RegisteredModelStatus


@dataclass(frozen=True)
class ModelVersion:
    id: UUID
    registered_model_id: UUID
    version: int
    training_run_id: UUID
    experiment_run_id: UUID
    artifact_uri: str
    model_format: str
    signature: dict[str, object]
    metrics: dict[str, float]
    status: ModelVersionStatus
    created_by: UUID


@dataclass(frozen=True)
class ModelApproval:
    id: UUID
    model_version_id: UUID
    status: ModelApprovalStatus
    requested_by: UUID
    reviewer_id: UUID | None
    comment: str
    policy_snapshot: dict[str, object]


@dataclass(frozen=True)
class ModelLineage:
    id: UUID
    model_version_id: UUID
    source_type: str
    source_id: str


@dataclass(frozen=True)
class TrainingRunReference:
    id: UUID
    organization_id: UUID
    project_id: UUID
    experiment_id: UUID
    experiment_run_id: UUID
    dataset_version_id: UUID | None
    feature_set_id: UUID | None
    status: str
    artifact_uri: str
    model_type: str
    metrics: dict[str, float]
