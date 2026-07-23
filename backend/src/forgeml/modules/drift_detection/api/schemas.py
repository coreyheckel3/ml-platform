from pydantic import BaseModel, Field


class CreateDriftProfileRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    model_version_id: str | None = None
    dataset_version_id: str | None = None
    baseline_profile: dict[str, object]


class DriftProfileResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    model_version_id: str | None
    dataset_version_id: str | None
    baseline_profile: dict[str, object]
    status: str
    created_by: str


class DriftProfileListResponse(BaseModel):
    items: list[DriftProfileResponse]
    next_cursor: str | None = None


class RunDriftReportRequest(BaseModel):
    endpoint_id: str
    window_seconds: int = Field(default=3600, gt=0, le=86_400)
    drift_threshold: float = Field(default=0.2, ge=0, le=1)
    sample_limit: int = Field(default=200, ge=1, le=10_000)
    report_uri: str = Field(default="", max_length=2048)


class DriftReportResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    drift_profile_id: str
    endpoint_id: str
    deployment_id: str
    deployment_revision_id: str
    status: str
    drift_score: float
    drifted_feature_count: int
    evaluated_feature_count: int
    window_seconds: int
    drift_threshold: float
    summary: dict[str, object]
    report_uri: str
    error_message: str | None


class DriftReportListResponse(BaseModel):
    items: list[DriftReportResponse]
    next_cursor: str | None = None


class DriftFeatureResultResponse(BaseModel):
    id: str
    drift_report_id: str
    feature_name: str
    feature_type: str
    drift_score: float
    threshold: float
    drift_detected: bool
    statistics: dict[str, object]


class DriftFeatureResultListResponse(BaseModel):
    items: list[DriftFeatureResultResponse]
    next_cursor: str | None = None
