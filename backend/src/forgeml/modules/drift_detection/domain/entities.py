from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class DriftProfileStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DriftReportStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class DriftFeatureType(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


@dataclass(frozen=True)
class DriftProfile:
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    slug: str
    description: str
    model_version_id: UUID | None
    dataset_version_id: UUID | None
    baseline_profile: dict[str, object]
    status: DriftProfileStatus
    created_by: UUID


@dataclass(frozen=True)
class DriftReport:
    id: UUID
    organization_id: UUID
    project_id: UUID
    drift_profile_id: UUID
    endpoint_id: UUID
    deployment_id: UUID
    deployment_revision_id: UUID
    status: DriftReportStatus
    drift_score: float
    drifted_feature_count: int
    evaluated_feature_count: int
    window_seconds: int
    drift_threshold: float
    summary: dict[str, object]
    report_uri: str
    error_message: str | None


@dataclass(frozen=True)
class DriftFeatureResult:
    id: UUID
    drift_report_id: UUID
    feature_name: str
    feature_type: DriftFeatureType
    drift_score: float
    threshold: float
    drift_detected: bool
    statistics: dict[str, object]


@dataclass(frozen=True)
class InferenceEndpointDriftReference:
    endpoint_id: UUID
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    deployment_revision_id: UUID
    endpoint_name: str
    route_path: str


@dataclass(frozen=True)
class DriftAnalysisResult:
    drift_score: float
    drifted_feature_count: int
    evaluated_feature_count: int
    summary: dict[str, object]
    feature_results: list[DriftFeatureResult]
