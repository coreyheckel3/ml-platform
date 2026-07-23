from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class FeatureSetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class FeaturePipelineStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class FeatureMaterializationStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class FeatureSet:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    entity_key: str
    status: FeatureSetStatus


@dataclass(frozen=True)
class FeatureDefinition:
    id: UUID
    feature_set_id: UUID
    name: str
    dtype: str
    description: str
    nullable: bool
    constraints: dict[str, object]


@dataclass(frozen=True)
class FeaturePipeline:
    id: UUID
    feature_set_id: UUID
    name: str
    source_dataset_id: UUID | None
    code_ref: str
    schedule_cron: str | None
    status: FeaturePipelineStatus


@dataclass(frozen=True)
class FeatureMaterialization:
    id: UUID
    feature_set_id: UUID
    pipeline_id: UUID
    version: int
    offline_uri: str
    online_ref: str | None
    orchestrator_run_id: str
    status: FeatureMaterializationStatus


@dataclass(frozen=True)
class FeatureLineage:
    id: UUID
    feature_set_id: UUID
    upstream_type: str
    upstream_id: str

