from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class DatasetSourceType(StrEnum):
    UPLOAD = "upload"
    S3 = "s3"
    DATABASE = "database"
    STREAM = "stream"


class DatasetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DatasetVersionStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    FINALIZED = "finalized"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"


class DatasetValidationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Dataset:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    source_type: DatasetSourceType
    status: DatasetStatus


@dataclass(frozen=True)
class SchemaField:
    name: str
    dtype: str
    nullable: bool


@dataclass(frozen=True)
class DatasetSchema:
    dataset_version_id: UUID
    fields: tuple[SchemaField, ...]
    inferred: bool
    schema_hash: str


@dataclass(frozen=True)
class DatasetVersion:
    id: UUID
    dataset_id: UUID
    version: int
    object_uri: str
    content_hash: str
    row_count: int
    size_bytes: int
    status: DatasetVersionStatus
    created_by: UUID


@dataclass(frozen=True)
class DatasetValidationRun:
    id: UUID
    dataset_version_id: UUID
    status: DatasetValidationStatus
    report: dict[str, object]
    error_message: str | None

