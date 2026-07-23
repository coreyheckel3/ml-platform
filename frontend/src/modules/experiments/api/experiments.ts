import { apiGet } from "../../../shared/api/client";

export type Experiment = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  owner_user_id: string;
  status: string;
};

export type ExperimentRun = {
  id: string;
  experiment_id: string;
  project_id: string;
  run_name: string;
  status: string;
  model_type: string;
  started_by: string;
  dataset_version_id: string | null;
  feature_set_id: string | null;
  parameters: Record<string, unknown>;
  metrics: Record<string, number>;
  artifact_uri: string;
  evaluation_report: Record<string, unknown>;
  error_message: string | null;
};

export type ExperimentListResponse = {
  items: Experiment[];
  next_cursor: string | null;
};

export type ExperimentRunListResponse = {
  items: ExperimentRun[];
  next_cursor: string | null;
};

export function listExperiments(
  projectId: string,
  token: string
): Promise<ExperimentListResponse> {
  return apiGet<ExperimentListResponse>(`/api/v1/projects/${projectId}/experiments`, {
    token
  });
}

export function listExperimentRuns(
  experimentId: string,
  token: string
): Promise<ExperimentRunListResponse> {
  return apiGet<ExperimentRunListResponse>(`/api/v1/experiments/${experimentId}/runs`, {
    token
  });
}
