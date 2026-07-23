from pydantic import BaseModel, Field


class CreateRegisteredModelRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    task_type: str = Field(min_length=2, max_length=64)


class RegisteredModelResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    task_type: str
    owner_user_id: str
    status: str


class RegisteredModelListResponse(BaseModel):
    items: list[RegisteredModelResponse]
    next_cursor: str | None = None


class RegisterModelVersionRequest(BaseModel):
    training_run_id: str
    model_format: str = Field(min_length=2, max_length=64)
    signature: dict[str, object]


class PromoteTrainingRunRequest(BaseModel):
    training_run_id: str
    model_format: str = Field(min_length=2, max_length=64)
    signature: dict[str, object]


class ModelVersionResponse(BaseModel):
    id: str
    registered_model_id: str
    version: int
    training_run_id: str
    experiment_run_id: str
    artifact_uri: str
    model_format: str
    signature: dict[str, object]
    metrics: dict[str, float]
    status: str
    created_by: str


class ModelVersionListResponse(BaseModel):
    items: list[ModelVersionResponse]
    next_cursor: str | None = None


class RequestModelApprovalRequest(BaseModel):
    comment: str = Field(default="", max_length=2000)


class ReviewModelVersionRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=2000)


class ModelApprovalResponse(BaseModel):
    id: str
    model_version_id: str
    status: str
    requested_by: str
    reviewer_id: str | None
    comment: str
    policy_snapshot: dict[str, object]


class ModelApprovalListResponse(BaseModel):
    items: list[ModelApprovalResponse]
    next_cursor: str | None = None


class ModelLineageResponse(BaseModel):
    id: str
    model_version_id: str
    source_type: str
    source_id: str


class ModelLineageListResponse(BaseModel):
    items: list[ModelLineageResponse]
    next_cursor: str | None = None
