from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class DeploymentEnvironment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DeploymentRevisionStatus(StrEnum):
    REQUESTED = "requested"
    DEPLOYING = "deploying"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentHealthStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class Deployment:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    environment: DeploymentEnvironment
    status: DeploymentStatus
    created_by: UUID


@dataclass(frozen=True)
class DeploymentRevision:
    id: UUID
    deployment_id: UUID
    model_version_id: UUID
    revision: int
    serving_image: str
    runtime_config: dict[str, object]
    traffic_percentage: int
    status: DeploymentRevisionStatus
    orchestrator_deployment_id: str
    created_by: UUID


@dataclass(frozen=True)
class DeploymentHealthCheck:
    id: UUID
    deployment_revision_id: UUID
    status: DeploymentHealthStatus
    latency_ms: float
    error_rate: float
    details: dict[str, object]


@dataclass(frozen=True)
class DeploymentEvent:
    id: UUID
    deployment_id: UUID
    deployment_revision_id: UUID | None
    event_type: str
    message: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class ModelVersionDeploymentReference:
    id: UUID
    registered_model_id: UUID
    organization_id: UUID
    project_id: UUID
    version: int
    status: str
    artifact_uri: str
    model_format: str
