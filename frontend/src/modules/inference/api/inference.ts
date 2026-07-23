import { apiGet, apiPost } from "../../../shared/api/client";

export type InferenceEndpoint = {
  id: string;
  organization_id: string;
  project_id: string;
  deployment_id: string;
  deployment_revision_id: string;
  name: string;
  slug: string;
  route_path: string;
  description: string;
  status: string;
  created_by: string;
};

export type InferenceRequestLog = {
  id: string;
  endpoint_id: string;
  deployment_revision_id: string;
  request_id: string;
  status: string;
  latency_ms: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string | null;
};

export type InferenceMetricSnapshot = {
  id: string;
  endpoint_id: string;
  window_seconds: number;
  prediction_count: number;
  error_count: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
};

export type PredictResponse = {
  log_id: string;
  endpoint_id: string;
  deployment_revision_id: string;
  request_id: string;
  status: string;
  latency_ms: number;
  output_payload: Record<string, unknown>;
};

export type InferenceEndpointListResponse = {
  items: InferenceEndpoint[];
  next_cursor: string | null;
};

export type InferenceRequestLogListResponse = {
  items: InferenceRequestLog[];
  next_cursor: string | null;
};

export type InferenceMetricSnapshotListResponse = {
  items: InferenceMetricSnapshot[];
  next_cursor: string | null;
};

export function listInferenceEndpoints(
  projectId: string,
  token: string
): Promise<InferenceEndpointListResponse> {
  return apiGet<InferenceEndpointListResponse>(
    `/api/v1/projects/${projectId}/inference-endpoints`,
    { token }
  );
}

export function listInferenceRequests(
  endpointId: string,
  token: string
): Promise<InferenceRequestLogListResponse> {
  return apiGet<InferenceRequestLogListResponse>(
    `/api/v1/inference-endpoints/${endpointId}/requests`,
    { token }
  );
}

export function listInferenceMetricSnapshots(
  endpointId: string,
  token: string
): Promise<InferenceMetricSnapshotListResponse> {
  return apiGet<InferenceMetricSnapshotListResponse>(
    `/api/v1/inference-endpoints/${endpointId}/metric-snapshots`,
    { token }
  );
}

export function predictEndpoint(
  endpointId: string,
  token: string,
  payload: Record<string, unknown>
): Promise<PredictResponse> {
  return apiPost<{ payload: Record<string, unknown> }, PredictResponse>(
    `/api/v1/inference-endpoints/${endpointId}/predict`,
    { payload },
    { token }
  );
}
