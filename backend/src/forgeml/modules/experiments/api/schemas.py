from pydantic import BaseModel, Field


class CreateExperimentRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)


class ExperimentResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    owner_user_id: str
    status: str


class ExperimentListResponse(BaseModel):
    items: list[ExperimentResponse]
    next_cursor: str | None = None


class StartExperimentRunRequest(BaseModel):
    run_name: str = Field(min_length=3, max_length=160)
    model_type: str = Field(min_length=2, max_length=64)
    artifact_uri: str = Field(min_length=3, max_length=2048)
    dataset_version_id: str | None = None
    feature_set_id: str | None = None
    parameters: dict[str, object] = Field(default_factory=dict)


class ExperimentRunResponse(BaseModel):
    id: str
    experiment_id: str
    project_id: str
    run_name: str
    status: str
    model_type: str
    started_by: str
    dataset_version_id: str | None
    feature_set_id: str | None
    parameters: dict[str, object]
    metrics: dict[str, float]
    artifact_uri: str
    evaluation_report: dict[str, object]
    error_message: str | None


class ExperimentRunListResponse(BaseModel):
    items: list[ExperimentRunResponse]
    next_cursor: str | None = None


class LogExperimentMetricsRequest(BaseModel):
    metrics: dict[str, float] = Field(min_length=1, max_length=500)
    evaluation_report: dict[str, object] | None = None


class LogExperimentArtifactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    artifact_type: str = Field(min_length=2, max_length=64)
    uri: str = Field(min_length=3, max_length=2048)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExperimentArtifactResponse(BaseModel):
    id: str
    experiment_run_id: str
    name: str
    artifact_type: str
    uri: str
    metadata: dict[str, object]


class ExperimentArtifactListResponse(BaseModel):
    items: list[ExperimentArtifactResponse]
    next_cursor: str | None = None


class CompleteExperimentRunRequest(BaseModel):
    status: str = Field(pattern="^(succeeded|failed|canceled)$")
    metrics: dict[str, float] = Field(default_factory=dict)
    evaluation_report: dict[str, object] | None = None
    error_message: str | None = Field(default=None, max_length=2000)
