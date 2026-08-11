import { apiGet } from "../../../shared/api/client";

export type ProjectMonitoringSummary = {
  project_id: string;
  inference_endpoint_count: number;
  prediction_count: number;
  error_count: number;
  request_count: number;
  active_alert_count: number;
  error_rate: number;
  max_p95_latency_ms: number;
};

export type MonitoringLatencyPercentile = {
  endpoint_id: string;
  endpoint_name: string;
  p50_latency_ms: number;
  p95_latency_ms: number;
  prediction_count: number;
  latest_window_seconds: number;
};

export type MonitoringInferenceErrorBreakdown = {
  endpoint_id: string;
  endpoint_name: string;
  error_count: number;
  request_count: number;
  error_rate: number;
  status: string;
};

export type MonitoringInferenceOverview = {
  endpoint_count: number;
  prediction_count: number;
  error_count: number;
  request_count: number;
  error_rate: number;
  weighted_p50_latency_ms: number;
  weighted_p95_latency_ms: number;
  latency_percentiles: MonitoringLatencyPercentile[];
  error_breakdown: MonitoringInferenceErrorBreakdown[];
};

export type MonitoringDriftSignal = {
  drift_report_id: string;
  endpoint_id: string;
  deployment_id: string;
  status: string;
  drift_score: number;
  drift_threshold: number;
  drifted_feature_count: number;
  evaluated_feature_count: number;
  created_at: string | null;
};

export type MonitoringDriftOverview = {
  report_count: number;
  failed_report_count: number;
  breached_report_count: number;
  latest_drift_score: number;
  drifted_feature_count: number;
  signals: MonitoringDriftSignal[];
};

export type MonitoringTrainingFailure = {
  training_run_id: string;
  algorithm: string;
  model_type: string;
  status: string;
  objective_metric_name: string;
  error_message: string | null;
  attempt_count: number;
  completed_at: string | null;
};

export type MonitoringTrainingOverview = {
  total_run_count: number;
  running_count: number;
  failed_count: number;
  dead_lettered_count: number;
  failure_rate: number;
  average_training_time_seconds: number;
  latest_failures: MonitoringTrainingFailure[];
};

export type MonitoringRetrainingActivity = {
  retraining_run_id: string;
  policy_id: string;
  deployment_id: string;
  trigger_type: string;
  status: string;
  training_run_id: string | null;
  drift_report_id: string | null;
  alert_event_id: string | null;
  created_at: string | null;
};

export type MonitoringRetrainingOverview = {
  policy_count: number;
  enabled_policy_count: number;
  run_count: number;
  pending_approval_count: number;
  queued_count: number;
  running_count: number;
  succeeded_count: number;
  failed_count: number;
  skipped_count: number;
  latest_activity: MonitoringRetrainingActivity[];
};

export type MonitoringOperationsOverview = {
  project_id: string;
  active_alert_count: number;
  inference: MonitoringInferenceOverview;
  drift: MonitoringDriftOverview;
  training: MonitoringTrainingOverview;
  retraining: MonitoringRetrainingOverview;
};

export type InferenceEndpointMonitoringSummary = {
  endpoint_id: string;
  endpoint_name: string;
  route_path: string;
  status: string;
  deployment_id: string;
  deployment_revision_id: string;
  latest_window_seconds: number;
  prediction_count: number;
  error_count: number;
  request_count: number;
  error_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
};

export type InferenceEndpointMonitoringSummaryListResponse = {
  items: InferenceEndpointMonitoringSummary[];
  next_cursor: string | null;
};

export function getProjectMonitoringSummary(
  projectId: string,
  token: string
): Promise<ProjectMonitoringSummary> {
  return apiGet<ProjectMonitoringSummary>(`/api/v1/projects/${projectId}/monitoring/summary`, {
    token
  });
}

export function getProjectMonitoringOperations(
  projectId: string,
  token: string
): Promise<MonitoringOperationsOverview> {
  return apiGet<MonitoringOperationsOverview>(
    `/api/v1/projects/${projectId}/monitoring/operations`,
    { token }
  );
}

export function listInferenceEndpointMonitoringSummaries(
  projectId: string,
  token: string
): Promise<InferenceEndpointMonitoringSummaryListResponse> {
  return apiGet<InferenceEndpointMonitoringSummaryListResponse>(
    `/api/v1/projects/${projectId}/monitoring/inference-endpoints`,
    { token }
  );
}
