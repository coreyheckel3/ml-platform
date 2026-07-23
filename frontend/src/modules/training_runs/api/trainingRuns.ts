import { apiGet } from "../../../shared/api/client";

export type TrainingRun = {
  id: string;
  organization_id: string;
  project_id: string;
  experiment_id: string;
  experiment_run_id: string;
  dataset_version_id: string | null;
  feature_set_id: string | null;
  algorithm: string;
  model_type: string;
  objective_metric_name: string;
  hyperparameters: Record<string, unknown>;
  status: string;
  requested_by: string;
  artifact_uri: string;
  orchestrator_run_id: string;
  metrics: Record<string, number>;
  error_message: string | null;
};

export type TrainingRunListResponse = {
  items: TrainingRun[];
  next_cursor: string | null;
};

export function listTrainingRuns(
  projectId: string,
  token: string
): Promise<TrainingRunListResponse> {
  return apiGet<TrainingRunListResponse>(`/api/v1/projects/${projectId}/training-runs`, {
    token
  });
}
