import { apiGet, apiPost } from "../../../shared/api/client";

export type ReleaseEvidenceReport = {
  id: string;
  organization_id: string;
  requested_by_user_id: string;
  provider: string;
  status: string;
  repository: string | null;
  branch: string | null;
  workflow: string | null;
  artifact_name: string | null;
  run_id: string | null;
  run_url: string | null;
  manifest_git_sha: string | null;
  manifest_git_branch: string | null;
  ci_run_url: string | null;
  artifact_count: number;
  quality_gate_count: number;
  missing_artifacts: string[];
  missing_quality_gates: string[];
  comparison: Record<string, unknown>;
  manifest_summary: Record<string, unknown>;
  report: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
};

export type ReleaseEvidenceReportListResponse = {
  items: ReleaseEvidenceReport[];
  next_cursor: string | null;
};

export type ReleaseEvidenceRefreshStatus = {
  schema_version: string;
  organization_id: string;
  provider: string;
  repository: string | null;
  branch: string | null;
  workflow: string | null;
  artifact_name: string | null;
  status: string;
  stale: boolean;
  stale_after_seconds: number;
  refresh_interval_seconds: number;
  latest_report: ReleaseEvidenceReport | null;
  last_successful_report: ReleaseEvidenceReport | null;
  latest_report_age_seconds: number | null;
  last_success_age_seconds: number | null;
  next_refresh_at: string | null;
  checked_at: string;
  stale_reasons: string[];
  recommended_action: string;
  operator_command: string;
};

export type ReleaseEvidenceReportFilters = {
  status?: string;
  limit?: number;
};

export function listReleaseEvidenceReports(
  token: string,
  filters: ReleaseEvidenceReportFilters = {},
): Promise<ReleaseEvidenceReportListResponse> {
  const params = new URLSearchParams();
  if (filters.status) {
    params.set("status", filters.status);
  }
  params.set("limit", String(filters.limit ?? 20));

  return apiGet<ReleaseEvidenceReportListResponse>(
    `/api/v1/admin/release-evidence/reports?${params.toString()}`,
    { token },
  );
}

export function getReleaseEvidenceReport(
  token: string,
  reportId: string,
): Promise<ReleaseEvidenceReport> {
  return apiGet<ReleaseEvidenceReport>(
    `/api/v1/admin/release-evidence/reports/${reportId}`,
    { token },
  );
}

export function retrieveReleaseEvidenceReport(
  token: string,
): Promise<ReleaseEvidenceReport> {
  return apiPost<Record<string, never>, ReleaseEvidenceReport>(
    "/api/v1/admin/release-evidence/reports/retrieve",
    {},
    { token },
  );
}

export function getReleaseEvidenceRefreshStatus(
  token: string,
): Promise<ReleaseEvidenceRefreshStatus> {
  return apiGet<ReleaseEvidenceRefreshStatus>(
    "/api/v1/admin/release-evidence/refresh/status",
    { token },
  );
}
