import { apiGet, apiPost } from "../../../shared/api/client";

export type DriftProfile = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  model_version_id: string | null;
  dataset_version_id: string | null;
  baseline_profile: Record<string, unknown>;
  status: string;
  created_by: string;
};

export type DriftReport = {
  id: string;
  organization_id: string;
  project_id: string;
  drift_profile_id: string;
  endpoint_id: string;
  deployment_id: string;
  deployment_revision_id: string;
  status: string;
  drift_score: number;
  drifted_feature_count: number;
  evaluated_feature_count: number;
  window_seconds: number;
  drift_threshold: number;
  summary: Record<string, unknown>;
  report_uri: string;
  error_message: string | null;
};

export type DriftFeatureResult = {
  id: string;
  drift_report_id: string;
  feature_name: string;
  feature_type: string;
  drift_score: number;
  threshold: number;
  drift_detected: boolean;
  statistics: Record<string, unknown>;
};

export type DriftProfileListResponse = {
  items: DriftProfile[];
  next_cursor: string | null;
};

export type DriftReportListResponse = {
  items: DriftReport[];
  next_cursor: string | null;
};

export type DriftFeatureResultListResponse = {
  items: DriftFeatureResult[];
  next_cursor: string | null;
};

export type CreateDriftProfilePayload = {
  name: string;
  description: string;
  model_version_id: string | null;
  dataset_version_id: string | null;
  baseline_profile: Record<string, unknown>;
};

export type RunDriftReportPayload = {
  endpoint_id: string;
  window_seconds: number;
  drift_threshold: number;
  sample_limit: number;
  report_uri: string;
};

export function createDriftProfile(
  projectId: string,
  payload: CreateDriftProfilePayload,
  token: string
): Promise<DriftProfile> {
  return apiPost<CreateDriftProfilePayload, DriftProfile>(
    `/api/v1/projects/${projectId}/drift-profiles`,
    payload,
    { token }
  );
}

export function listDriftProfiles(
  projectId: string,
  token: string
): Promise<DriftProfileListResponse> {
  return apiGet<DriftProfileListResponse>(`/api/v1/projects/${projectId}/drift-profiles`, {
    token
  });
}

export function listProjectDriftReports(
  projectId: string,
  token: string
): Promise<DriftReportListResponse> {
  return apiGet<DriftReportListResponse>(`/api/v1/projects/${projectId}/drift-reports`, {
    token
  });
}

export function listDriftFeatureResults(
  reportId: string,
  token: string
): Promise<DriftFeatureResultListResponse> {
  return apiGet<DriftFeatureResultListResponse>(`/api/v1/drift-reports/${reportId}/features`, {
    token
  });
}

export function runDriftReport(
  profileId: string,
  payload: RunDriftReportPayload,
  token: string
): Promise<DriftReport> {
  return apiPost<RunDriftReportPayload, DriftReport>(
    `/api/v1/drift-profiles/${profileId}/reports`,
    payload,
    { token }
  );
}
