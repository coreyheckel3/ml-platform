from pydantic import BaseModel, Field


class ProjectLifecycleMetricResponse(BaseModel):
    label: str
    value: str
    detail: str
    tone: str


class ProjectLifecycleStageResponse(BaseModel):
    key: str
    title: str
    status: str
    description: str
    primary_signal: str
    count: int
    last_updated_at: str | None
    route_path: str
    recommended_action: str


class ProjectLifecycleDependencyResponse(BaseModel):
    source_stage: str
    target_stage: str
    status: str
    detail: str


class ProjectLifecycleSummaryResponse(BaseModel):
    schema_version: str = "forgeml.project_lifecycle.v1"
    project_id: str
    project_name: str
    project_slug: str
    project_status: str
    readiness_score: int
    ready_stage_count: int
    total_stage_count: int
    stages: list[ProjectLifecycleStageResponse] = Field(default_factory=list)
    dependencies: list[ProjectLifecycleDependencyResponse] = Field(default_factory=list)
    metrics: list[ProjectLifecycleMetricResponse] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    generated_at: str
