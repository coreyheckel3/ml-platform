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
  attempt_count: number;
  max_attempts: number;
  worker_id: string | null;
  lease_expires_at: string | null;
  last_heartbeat_at: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  next_retry_at: string | null;
};

export type TrainingRunEvent = {
  id: string;
  training_run_id: string;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
};

export type TrainingRunLog = {
  id: string;
  training_run_id: string;
  sequence: number;
  level: string;
  logger: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type TrainingOrchestrationStatus = {
  training_run_id: string;
  orchestrator_run_id: string;
  orchestrator: string;
  external_status: string;
  mapped_training_status: string | null;
  is_terminal: boolean;
  external_url: string | null;
  metadata: Record<string, unknown>;
  observed_at: string | null;
};

export type TrainingRunnerProfile = {
  slug: string;
  display_name: string;
  runner_kind: string;
  package_name: string;
  description: string;
  supported_algorithms: string[];
  default_algorithm: string;
  default_model_type: string;
  objective_metric_name: string;
  default_hyperparameters: Record<string, unknown>;
  availability: {
    available: boolean;
    repo_root: string;
    executable_path: string;
    data_dir: string;
    missing: string[];
  };
  command_preview: string[];
};

export type TrainingRunListResponse = {
  items: TrainingRun[];
  next_cursor: string | null;
};

export type TrainingRunnerProfileListResponse = {
  items: TrainingRunnerProfile[];
  next_cursor: string | null;
};

export type TrainingRunEventListResponse = {
  items: TrainingRunEvent[];
  next_cursor: string | null;
};

export type TrainingRunLogListResponse = {
  items: TrainingRunLog[];
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
  token: string,
): Promise<TrainingRun> {
  return apiPost<StartTrainingRunPayload, TrainingRun>(
    `/api/v1/projects/${projectId}/training-runs`,
    payload,
    { token },
  );
}

export function listTrainingRuns(
  projectId: string,
  token: string,
): Promise<TrainingRunListResponse> {
  return apiGet<TrainingRunListResponse>(
    `/api/v1/projects/${projectId}/training-runs`,
    {
      token,
    },
  );
}

export function getTrainingRun(
  trainingRunId: string,
  token: string,
): Promise<TrainingRun> {
  return apiGet<TrainingRun>(`/api/v1/training-runs/${trainingRunId}`, {
    token,
  });
}

export function recordTrainingResult(
  trainingRunId: string,
  payload: RecordTrainingResultPayload,
  token: string,
): Promise<TrainingRun> {
  return apiPost<RecordTrainingResultPayload, TrainingRun>(
    `/api/v1/training-runs/${trainingRunId}/result`,
    payload,
    { token },
  );
}

export function cancelTrainingRun(
  trainingRunId: string,
  token: string,
): Promise<TrainingRun> {
  return apiPost<Record<string, never>, TrainingRun>(
    `/api/v1/training-runs/${trainingRunId}/cancel`,
    {},
    { token },
  );
}

export function listTrainingRunEvents(
  trainingRunId: string,
  token: string,
): Promise<TrainingRunEventListResponse> {
  return apiGet<TrainingRunEventListResponse>(
    `/api/v1/training-runs/${trainingRunId}/events`,
    { token },
  );
}

export function listTrainingRunLogs(
  trainingRunId: string,
  token: string,
): Promise<TrainingRunLogListResponse> {
  return apiGet<TrainingRunLogListResponse>(
    `/api/v1/training-runs/${trainingRunId}/logs`,
    { token },
  );
}

export function getTrainingRunOrchestrationStatus(
  trainingRunId: string,
  token: string,
): Promise<TrainingOrchestrationStatus> {
  return apiGet<TrainingOrchestrationStatus>(
    `/api/v1/training-runs/${trainingRunId}/orchestration-status`,
    { token },
  );
}

export function listTrainingRunnerProfiles(
  token: string,
): Promise<TrainingRunnerProfileListResponse> {
  return apiGet<TrainingRunnerProfileListResponse>(
    "/api/v1/training-runner-profiles",
    { token },
  );
}
