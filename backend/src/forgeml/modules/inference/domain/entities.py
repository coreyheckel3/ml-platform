from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class InferenceEndpointStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class InferenceRequestStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class InferenceEndpoint:
    id: UUID
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    deployment_revision_id: UUID
    name: str
    slug: str
    route_path: str
    description: str
    status: InferenceEndpointStatus
    created_by: UUID


@dataclass(frozen=True)
class InferenceRequestLog:
    id: UUID
    endpoint_id: UUID
    deployment_revision_id: UUID
    request_id: str
    status: InferenceRequestStatus
    latency_ms: float
    input_payload: dict[str, object]
    output_payload: dict[str, object]
    error_message: str | None


@dataclass(frozen=True)
class InferenceMetricSnapshot:
    id: UUID
    endpoint_id: UUID
    window_seconds: int
    prediction_count: int
    error_count: int
    p50_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class DeploymentRevisionServingReference:
    deployment_id: UUID
    deployment_revision_id: UUID
    organization_id: UUID
    project_id: UUID
    deployment_status: str
    revision_status: str
    traffic_percentage: int
    model_version_id: UUID
    model_signature: dict[str, object]


@dataclass(frozen=True)
class InferencePredictionResult:
    output_payload: dict[str, object]
    latency_ms: float


@dataclass(frozen=True)
class InferencePrediction:
    log_id: UUID
    endpoint_id: UUID
    deployment_revision_id: UUID
    request_id: str
    status: InferenceRequestStatus
    latency_ms: float
    output_payload: dict[str, object]
