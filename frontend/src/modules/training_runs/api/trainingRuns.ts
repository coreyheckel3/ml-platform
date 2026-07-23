import { apiGet, apiPost } from "../../../shared/api/client";

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

export type TrainingRunEvent = {
  id: string;
  training_run_id: string;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
};

export type TrainingRunListResponse = {
  items: TrainingRun[];
  next_cursor: string | null;
};

export type TrainingRunEventListResponse = {
  items: TrainingRunEvent[];
  next_cursor: string | null;
};

export type StartTrainingRunPayload = {
  experiment_id: string;
  run_name: string;
  dataset_version_id: string | null;
  feature_set_id: string | null;
  algorithm: string;
  model_type: string;
  objective_metric_name: string;
  hyperparameters: Record<string, unknown>;
};

export type RecordTrainingResultPayload = {
  status: "succeeded" | "failed" | "canceled";
  metrics: Record<string, number>;
  evaluation_report: Record<string, unknown>;
  error_message: string | null;
};

export function startTrainingRun(
  projectId: string,
  payload: StartTrainingRunPayload,
  token: string
): Promise<TrainingRun> {
  return apiPost<StartTrainingRunPayload, TrainingRun>(
    `/api/v1/projects/${projectId}/training-runs`,
    payload,
    { token }
  );
}

export function listTrainingRuns(
  projectId: string,
  token: string
): Promise<TrainingRunListResponse> {
  return apiGet<TrainingRunListResponse>(`/api/v1/projects/${projectId}/training-runs`, {
    token
  });
}

export function getTrainingRun(trainingRunId: string, token: string): Promise<TrainingRun> {
  return apiGet<TrainingRun>(`/api/v1/training-runs/${trainingRunId}`, { token });
}

export function recordTrainingResult(
  trainingRunId: string,
  payload: RecordTrainingResultPayload,
  token: string
): Promise<TrainingRun> {
  return apiPost<RecordTrainingResultPayload, TrainingRun>(
    `/api/v1/training-runs/${trainingRunId}/result`,
    payload,
    { token }
  );
}

export function cancelTrainingRun(
  trainingRunId: string,
  token: string
): Promise<TrainingRun> {
  return apiPost<Record<string, never>, TrainingRun>(
    `/api/v1/training-runs/${trainingRunId}/cancel`,
    {},
    { token }
  );
}

export function listTrainingRunEvents(
  trainingRunId: string,
  token: string
): Promise<TrainingRunEventListResponse> {
  return apiGet<TrainingRunEventListResponse>(
    `/api/v1/training-runs/${trainingRunId}/events`,
    { token }
  );
}
