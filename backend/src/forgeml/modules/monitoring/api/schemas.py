from pydantic import BaseModel


class InferenceEndpointMonitoringSummaryResponse(BaseModel):
    endpoint_id: str
    endpoint_name: str
    route_path: str
    status: str
    deployment_id: str
    deployment_revision_id: str
    latest_window_seconds: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float


class InferenceEndpointMonitoringSummaryListResponse(BaseModel):
    items: list[InferenceEndpointMonitoringSummaryResponse]
    next_cursor: str | None = None


class ProjectMonitoringSummaryResponse(BaseModel):
    project_id: str
    inference_endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    active_alert_count: int
    error_rate: float
    max_p95_latency_ms: float


class MonitoringLatencyPercentileResponse(BaseModel):
    endpoint_id: str
    endpoint_name: str
    p50_latency_ms: float
    p95_latency_ms: float
    prediction_count: int
    latest_window_seconds: int


class MonitoringInferenceErrorBreakdownResponse(BaseModel):
    endpoint_id: str
    endpoint_name: str
    error_count: int
    request_count: int
    error_rate: float
    status: str


class MonitoringInferenceOverviewResponse(BaseModel):
    endpoint_count: int
    prediction_count: int
    error_count: int
    request_count: int
    error_rate: float
    weighted_p50_latency_ms: float
    weighted_p95_latency_ms: float
    latency_percentiles: list[MonitoringLatencyPercentileResponse]
    error_breakdown: list[MonitoringInferenceErrorBreakdownResponse]


class MonitoringDriftSignalResponse(BaseModel):
    drift_report_id: str
    endpoint_id: str
    deployment_id: str
    status: str
    drift_score: float
    drift_threshold: float
    drifted_feature_count: int
    evaluated_feature_count: int
    created_at: str | None


class MonitoringDriftOverviewResponse(BaseModel):
    report_count: int
    failed_report_count: int
    breached_report_count: int
    latest_drift_score: float
    drifted_feature_count: int
    signals: list[MonitoringDriftSignalResponse]


class MonitoringTrainingFailureResponse(BaseModel):
    training_run_id: str
    algorithm: str
    model_type: str
    status: str
    objective_metric_name: str
    error_message: str | None
    attempt_count: int
    completed_at: str | None


class MonitoringTrainingOverviewResponse(BaseModel):
    total_run_count: int
    running_count: int
    failed_count: int
    dead_lettered_count: int
    failure_rate: float
    average_training_time_seconds: float
    latest_failures: list[MonitoringTrainingFailureResponse]


class MonitoringRetrainingActivityResponse(BaseModel):
    retraining_run_id: str
    policy_id: str
    deployment_id: str
    trigger_type: str
    status: str
    training_run_id: str | None
    drift_report_id: str | None
    alert_event_id: str | None
    created_at: str | None


class MonitoringRetrainingOverviewResponse(BaseModel):
    policy_count: int
    enabled_policy_count: int
    run_count: int
    pending_approval_count: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    latest_activity: list[MonitoringRetrainingActivityResponse]


class MonitoringOperationsOverviewResponse(BaseModel):
    project_id: str
    active_alert_count: int
    inference: MonitoringInferenceOverviewResponse
    drift: MonitoringDriftOverviewResponse
    training: MonitoringTrainingOverviewResponse
    retraining: MonitoringRetrainingOverviewResponse
