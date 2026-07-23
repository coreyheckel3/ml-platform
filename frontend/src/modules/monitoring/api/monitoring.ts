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

export function listInferenceEndpointMonitoringSummaries(
  projectId: string,
  token: string
): Promise<InferenceEndpointMonitoringSummaryListResponse> {
  return apiGet<InferenceEndpointMonitoringSummaryListResponse>(
    `/api/v1/projects/${projectId}/monitoring/inference-endpoints`,
    { token }
  );
}
