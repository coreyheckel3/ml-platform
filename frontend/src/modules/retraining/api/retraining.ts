import { apiGet, apiPost } from "../../../shared/api/client";

export type RetrainingPolicy = {
  id: string;
  organization_id: string;
  project_id: string;
  deployment_id: string;
  name: string;
  slug: string;
  description: string;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  training_template: Record<string, unknown>;
  cooldown_seconds: number;
  max_runs_per_day: number;
  approval_required: boolean;
  enabled: boolean;
  status: string;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
};

export type RetrainingRun = {
  id: string;
  organization_id: string;
  project_id: string;
  policy_id: string;
  deployment_id: string;
  trigger_type: string;
  drift_report_id: string | null;
  alert_event_id: string | null;
  training_run_id: string | null;
  status: string;
  reason: string;
  training_config: Record<string, unknown>;
  decision_metadata: Record<string, unknown>;
  requested_by: string;
  approved_by: string | null;
  rejected_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type RetrainingPolicyListResponse = {
  items: RetrainingPolicy[];
  next_cursor: string | null;
};

export type RetrainingRunListResponse = {
  items: RetrainingRun[];
  next_cursor: string | null;
};

export type EvaluateRetrainingPolicyPayload = {
  drift_report_id: string | null;
  alert_event_id: string | null;
  reason: string;
};

export type RetrainingEvaluation = {
  policy_id: string;
  decision: string;
  triggered: boolean;
  reason: string;
  run: RetrainingRun | null;
};

export function listRetrainingPolicies(
  projectId: string,
  token: string
): Promise<RetrainingPolicyListResponse> {
  return apiGet<RetrainingPolicyListResponse>(`/api/v1/projects/${projectId}/retraining-policies`, {
    token
  });
}

export function listRetrainingRuns(
  projectId: string,
  token: string
): Promise<RetrainingRunListResponse> {
  return apiGet<RetrainingRunListResponse>(`/api/v1/projects/${projectId}/retraining-runs`, {
    token
  });
}

export function evaluateRetrainingPolicy(
  policyId: string,
  payload: EvaluateRetrainingPolicyPayload,
  token: string
): Promise<RetrainingEvaluation> {
  return apiPost<EvaluateRetrainingPolicyPayload, RetrainingEvaluation>(
    `/api/v1/retraining-policies/${policyId}/evaluate`,
    payload,
    { token }
  );
}
