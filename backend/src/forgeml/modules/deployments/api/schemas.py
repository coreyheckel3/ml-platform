from pydantic import BaseModel, Field


class CreateDeploymentRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    environment: str = Field(min_length=3, max_length=32)


class DeploymentResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    environment: str
    status: str
    created_by: str


class DeploymentListResponse(BaseModel):
    items: list[DeploymentResponse]
    next_cursor: str | None = None


class CreateDeploymentRevisionRequest(BaseModel):
    model_version_id: str
    serving_image: str = Field(min_length=3, max_length=512)
    runtime_config: dict[str, object] = Field(default_factory=dict)
    traffic_percentage: int = Field(ge=0, le=100)


class DeploymentRevisionResponse(BaseModel):
    id: str
    deployment_id: str
    model_version_id: str
    revision: int
    serving_image: str
    runtime_config: dict[str, object]
    traffic_percentage: int
    status: str
    orchestrator_deployment_id: str
    created_by: str


class DeploymentRevisionListResponse(BaseModel):
    items: list[DeploymentRevisionResponse]
    next_cursor: str | None = None


class UpdateDeploymentTrafficRequest(BaseModel):
    traffic_percentage: int = Field(ge=0, le=100)


class RecordDeploymentHealthRequest(BaseModel):
    status: str = Field(pattern="^(healthy|degraded|unhealthy)$")
    latency_ms: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    details: dict[str, object] = Field(default_factory=dict)


class DeploymentHealthCheckResponse(BaseModel):
    id: str
    deployment_revision_id: str
    status: str
    latency_ms: float
    error_rate: float
    details: dict[str, object]


class DeploymentHealthCheckListResponse(BaseModel):
    items: list[DeploymentHealthCheckResponse]
    next_cursor: str | None = None


class RollbackDeploymentRequest(BaseModel):
    target_revision_id: str


class DeploymentEventResponse(BaseModel):
    id: str
    deployment_id: str
    deployment_revision_id: str | None
    event_type: str
    message: str
    metadata: dict[str, object]


class DeploymentEventListResponse(BaseModel):
    items: list[DeploymentEventResponse]
    next_cursor: str | None = None
