from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class InferenceEndpointMonitoringSummary:
    endpoint_id: UUID
    endpoint_name: str
    route_path: str
    status: str
    deployment_id: UUID
    deployment_revision_id: UUID
    latest_window_seconds: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class ProjectMonitoringSummary:
    project_id: UUID
    inference_endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    active_alert_count: int
    error_rate: float
    max_p95_latency_ms: float
