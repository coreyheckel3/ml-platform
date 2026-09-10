from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

LIFECYCLE_SCHEMA_VERSION = "forgeml.project_lifecycle.v1"


@dataclass(frozen=True)
class ProjectLifecycleMetric:
    label: str
    value: str
    detail: str
    tone: str = "neutral"


@dataclass(frozen=True)
class ProjectLifecycleStage:
    key: str
    title: str
    status: str
    description: str
    primary_signal: str
    count: int
    last_updated_at: datetime | None
    route_path: str
    recommended_action: str


@dataclass(frozen=True)
class ProjectLifecycleDependency:
    source_stage: str
    target_stage: str
    status: str
    detail: str


@dataclass(frozen=True)
class ProjectLifecycleSnapshot:
    project_id: UUID
    project_name: str
    project_slug: str
    project_status: str
    datasets: int
    dataset_versions: int
    validation_runs: int
    feature_sets: int
    feature_pipelines: int
    materializations: int
    experiments: int
    experiment_runs: int
    training_runs: int
    succeeded_training_runs: int
    failed_training_runs: int
    registered_models: int
    model_versions: int
    approved_model_versions: int
    deployments: int
    active_deployments: int
    inference_endpoints: int
    active_inference_endpoints: int
    prediction_count: int
    request_count: int
    inference_error_count: int
    max_p95_latency_ms: float
    drift_profiles: int
    drift_reports: int
    breached_drift_reports: int
    alert_rules: int
    active_alert_events: int
    retraining_policies: int
    enabled_retraining_policies: int
    retraining_runs: int
    successful_retraining_runs: int
    queued_retraining_runs: int
    last_updated_at: datetime | None


@dataclass(frozen=True)
class ProjectLifecycleSummary:
    schema_version: str
    project_id: UUID
    project_name: str
    project_slug: str
    project_status: str
    readiness_score: int
    ready_stage_count: int
    total_stage_count: int
    stages: tuple[ProjectLifecycleStage, ...]
    dependencies: tuple[ProjectLifecycleDependency, ...]
    metrics: tuple[ProjectLifecycleMetric, ...]
    recommended_actions: tuple[str, ...]
    generated_at: datetime
