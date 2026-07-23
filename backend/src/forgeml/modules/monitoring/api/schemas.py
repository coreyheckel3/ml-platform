from pydantic import BaseModel


class InferenceEndpointMonitoringSummaryResponse(BaseModel):
    endpoint_id: str
    endpoint_name: str
    route_path: str
    status: str
    deployment_id: str
    deployment_revision_id: str
    latest_window_seconds: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float


class InferenceEndpointMonitoringSummaryListResponse(BaseModel):
    items: list[InferenceEndpointMonitoringSummaryResponse]
    next_cursor: str | None = None


class ProjectMonitoringSummaryResponse(BaseModel):
    project_id: str
    inference_endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    active_alert_count: int
    error_rate: float
    max_p95_latency_ms: float
