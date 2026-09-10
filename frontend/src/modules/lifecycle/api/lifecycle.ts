import { apiGet } from "../../../shared/api/client";

export type LifecycleStageStatus =
  | "ready"
  | "needs_attention"
  | "pending"
  | "missing";

export type ProjectLifecycleMetric = {
  label: string;
  value: string;
  detail: string;
  tone: "neutral" | "success" | "warning" | "danger";
};

export type ProjectLifecycleStage = {
  key: string;
  title: string;
  status: LifecycleStageStatus;
  description: string;
  primary_signal: string;
  count: number;
  last_updated_at: string | null;
  route_path: string;
  recommended_action: string;
};

export type ProjectLifecycleDependency = {
  source_stage: string;
  target_stage: string;
  status: "connected" | "blocked";
  detail: string;
};

export type ProjectLifecycleSummary = {
  schema_version: "forgeml.project_lifecycle.v1";
  project_id: string;
  project_name: string;
  project_slug: string;
  project_status: string;
  readiness_score: number;
  ready_stage_count: number;
  total_stage_count: number;
  stages: ProjectLifecycleStage[];
  dependencies: ProjectLifecycleDependency[];
  metrics: ProjectLifecycleMetric[];
  recommended_actions: string[];
  generated_at: string;
};

export function getProjectLifecycleSummary(
  projectId: string,
  token: string,
): Promise<ProjectLifecycleSummary> {
  return apiGet<ProjectLifecycleSummary>(
    `/api/v1/projects/${projectId}/lifecycle/summary`,
    { token },
  );
}
