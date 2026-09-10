import { apiGet } from "../../../shared/api/client";

export type EvaluationLeaderboardEntry = {
  rank: number;
  experiment_run_id: string;
  run_name: string;
  experiment_name: string;
  status: string;
  model_type: string;
  primary_metric_name: string | null;
  primary_metric_value: number | null;
  delta_from_baseline: number | null;
  quality_score: number;
  model_version_label: string | null;
  approval_status: string;
  evidence_summary: string;
};

export type EvaluationMetricSlice = {
  metric_name: string;
  candidate_count: number;
  best_value: number;
  baseline_value: number;
  delta_from_baseline: number;
  best_experiment_run_id: string;
  best_run_name: string;
  higher_is_better: boolean;
};

export type EvaluationModelMetric = {
  label: string;
  value: number;
  tone: "neutral" | "success" | "warning" | "danger";
};

export type EvaluationModelCard = {
  model_version_id: string;
  model_name: string;
  version: number;
  status: string;
  approval_status: string;
  model_format: string;
  metric_summary: EvaluationModelMetric[];
  signature_summary: string[];
  artifact_uri: string;
  artifact_manifest_uri: string;
  artifact_manifest_hash: string;
  lineage_summary: string[];
  risk_flags: string[];
};

export type EvaluationApprovalChecklistItem = {
  key: string;
  label: string;
  status: "passed" | "warning" | "missing";
  detail: string;
  evidence: string;
};

export type EvaluationComparisonSummary = {
  schema_version: "forgeml.evaluation_comparison.v1";
  project_id: string;
  project_name: string;
  project_slug: string;
  project_status: string;
  primary_metric_name: string | null;
  higher_is_better: boolean;
  candidate_count: number;
  recommended_experiment_run_id: string | null;
  leaderboard: EvaluationLeaderboardEntry[];
  metric_slices: EvaluationMetricSlice[];
  model_cards: EvaluationModelCard[];
  approval_checklist: EvaluationApprovalChecklistItem[];
  narrative: string[];
  generated_at: string;
};

export function getEvaluationComparisonSummary(
  projectId: string,
  token: string,
): Promise<EvaluationComparisonSummary> {
  return apiGet<EvaluationComparisonSummary>(
    `/api/v1/projects/${projectId}/evaluation/comparison`,
    { token },
  );
}
