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


class SimulateCanaryTrafficRequest(BaseModel):
    canary_revision_id: str
    request_count: int = Field(default=1000, ge=1, le=100000)
    canary_percentage: int | None = Field(default=None, ge=1, le=99)
    routing_seed: str = Field(default="forgeml-canary-simulation", min_length=1, max_length=160)


class DeploymentCanarySimulationAllocationResponse(BaseModel):
    deployment_revision_id: str
    revision: int
    traffic_percentage: int
    simulated_request_count: int


class DeploymentCanarySimulationResponse(BaseModel):
    deployment_id: str
    canary_revision_id: str
    request_count: int
    routing_seed: str
    allocations: list[DeploymentCanarySimulationAllocationResponse]
    metadata: dict[str, object]


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
