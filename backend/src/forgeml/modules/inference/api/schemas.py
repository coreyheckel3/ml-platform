from pydantic import BaseModel, Field


class CreateInferenceEndpointRequest(BaseModel):
    deployment_id: str
    deployment_revision_id: str
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    route_path: str | None = Field(default=None, max_length=160)


class InferenceEndpointResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    deployment_id: str
    deployment_revision_id: str
    name: str
    slug: str
    route_path: str
    description: str
    status: str
    created_by: str


class InferenceEndpointListResponse(BaseModel):
    items: list[InferenceEndpointResponse]
    next_cursor: str | None = None


class PredictRequest(BaseModel):
    request_id: str | None = Field(default=None, max_length=128)
    payload: dict[str, object] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    log_id: str
    endpoint_id: str
    deployment_revision_id: str
    request_id: str
    status: str
    latency_ms: float
    output_payload: dict[str, object]


class InferenceRequestLogResponse(BaseModel):
    id: str
    endpoint_id: str
    deployment_revision_id: str
    request_id: str
    status: str
    latency_ms: float
    input_payload: dict[str, object]
    output_payload: dict[str, object]
    error_message: str | None


class InferenceRequestLogListResponse(BaseModel):
    items: list[InferenceRequestLogResponse]
    next_cursor: str | None = None


class RecordInferenceMetricSnapshotRequest(BaseModel):
    window_seconds: int = Field(gt=0, le=86_400)
    prediction_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    p50_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)


class InferenceMetricSnapshotResponse(BaseModel):
    id: str
    endpoint_id: str
    window_seconds: int
    prediction_count: int
    error_count: int
    p50_latency_ms: float
    p95_latency_ms: float


class InferenceMetricSnapshotListResponse(BaseModel):
    items: list[InferenceMetricSnapshotResponse]
    next_cursor: str | None = None
