from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class InferenceEndpointMonitoringSummary:
    endpoint_id: UUID
    endpoint_name: str
    route_path: str
    status: str
    deployment_id: UUID
    deployment_revision_id: UUID
    latest_window_seconds: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class ProjectMonitoringSummary:
    project_id: UUID
    inference_endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    active_alert_count: int
    error_rate: float
    max_p95_latency_ms: float


@dataclass(frozen=True)
class MonitoringLatencyPercentile:
    endpoint_id: UUID
    endpoint_name: str
    p50_latency_ms: float
    p95_latency_ms: float
    prediction_count: int
    latest_window_seconds: int


@dataclass(frozen=True)
class MonitoringInferenceErrorBreakdown:
    endpoint_id: UUID
    endpoint_name: str
    error_count: int
    request_count: int
    error_rate: float
    status: str


@dataclass(frozen=True)
class MonitoringInferenceOverview:
    endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    weighted_p50_latency_ms: float
    weighted_p95_latency_ms: float
    latency_percentiles: tuple[MonitoringLatencyPercentile, ...]
    error_breakdown: tuple[MonitoringInferenceErrorBreakdown, ...]


@dataclass(frozen=True)
class MonitoringDriftSignal:
    drift_report_id: UUID
    endpoint_id: UUID
    deployment_id: UUID
    status: str
    drift_score: float
    drift_threshold: float
    drifted_feature_count: int
    evaluated_feature_count: int
    created_at: datetime | None


@dataclass(frozen=True)
class MonitoringDriftOverview:
    report_count: int
    failed_report_count: int
    breached_report_count: int
    latest_drift_score: float
    drifted_feature_count: int
    signals: tuple[MonitoringDriftSignal, ...]


@dataclass(frozen=True)
class MonitoringTrainingFailure:
    training_run_id: UUID
    algorithm: str
    model_type: str
    status: str
    objective_metric_name: str
    error_message: str | None
    attempt_count: int
    completed_at: datetime | None


@dataclass(frozen=True)
class MonitoringTrainingOverview:
    total_run_count: int
    running_count: int
    failed_count: int
    dead_lettered_count: int
    failure_rate: float
    average_training_time_seconds: float
    latest_failures: tuple[MonitoringTrainingFailure, ...]


@dataclass(frozen=True)
class MonitoringRetrainingActivity:
    retraining_run_id: UUID
    policy_id: UUID
    deployment_id: UUID
    trigger_type: str
    status: str
    training_run_id: UUID | None
    drift_report_id: UUID | None
    alert_event_id: UUID | None
    created_at: datetime | None


@dataclass(frozen=True)
class MonitoringRetrainingOverview:
    policy_count: int
    enabled_policy_count: int
    run_count: int
    pending_approval_count: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    latest_activity: tuple[MonitoringRetrainingActivity, ...]


@dataclass(frozen=True)
class MonitoringOperationsOverview:
    project_id: UUID
    active_alert_count: int
    inference: MonitoringInferenceOverview
    drift: MonitoringDriftOverview
    training: MonitoringTrainingOverview
    retraining: MonitoringRetrainingOverview
