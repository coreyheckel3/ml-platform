import { apiGet, apiPost } from "../../../shared/api/client";

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

export type ExperimentArtifact = {
  id: string;
  experiment_run_id: string;
  name: string;
  artifact_type: string;
  uri: string;
  metadata: Record<string, unknown>;
};

export type ExperimentListResponse = {
  items: Experiment[];
  next_cursor: string | null;
};

export type ExperimentRunListResponse = {
  items: ExperimentRun[];
  next_cursor: string | null;
};

export type ExperimentArtifactListResponse = {
  items: ExperimentArtifact[];
  next_cursor: string | null;
};

export type CreateExperimentPayload = {
  name: string;
  description: string;
};

export type StartExperimentRunPayload = {
  run_name: string;
  model_type: string;
  artifact_uri: string;
  dataset_version_id: string | null;
  feature_set_id: string | null;
  parameters: Record<string, unknown>;
};

export type LogExperimentMetricsPayload = {
  metrics: Record<string, number>;
  evaluation_report: Record<string, unknown> | null;
};

export type LogExperimentArtifactPayload = {
  name: string;
  artifact_type: string;
  uri: string;
  metadata: Record<string, unknown>;
};

export type CompleteExperimentRunPayload = {
  status: "succeeded" | "failed" | "canceled";
  metrics: Record<string, number>;
  evaluation_report: Record<string, unknown> | null;
  error_message: string | null;
};

export function createExperiment(
  projectId: string,
  payload: CreateExperimentPayload,
  token: string
): Promise<Experiment> {
  return apiPost<CreateExperimentPayload, Experiment>(
    `/api/v1/projects/${projectId}/experiments`,
    payload,
    { token }
  );
}

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

export function startExperimentRun(
  experimentId: string,
  payload: StartExperimentRunPayload,
  token: string
): Promise<ExperimentRun> {
  return apiPost<StartExperimentRunPayload, ExperimentRun>(
    `/api/v1/experiments/${experimentId}/runs`,
    payload,
    { token }
  );
}

export function logExperimentMetrics(
  runId: string,
  payload: LogExperimentMetricsPayload,
  token: string
): Promise<ExperimentRun> {
  return apiPost<LogExperimentMetricsPayload, ExperimentRun>(
    `/api/v1/experiment-runs/${runId}/metrics`,
    payload,
    { token }
  );
}

export function logExperimentArtifact(
  runId: string,
  payload: LogExperimentArtifactPayload,
  token: string
): Promise<ExperimentArtifact> {
  return apiPost<LogExperimentArtifactPayload, ExperimentArtifact>(
    `/api/v1/experiment-runs/${runId}/artifacts`,
    payload,
    { token }
  );
}

export function listExperimentArtifacts(
  runId: string,
  token: string
): Promise<ExperimentArtifactListResponse> {
  return apiGet<ExperimentArtifactListResponse>(
    `/api/v1/experiment-runs/${runId}/artifacts`,
    { token }
  );
}

export function completeExperimentRun(
  runId: string,
  payload: CompleteExperimentRunPayload,
  token: string
): Promise<ExperimentRun> {
  return apiPost<CompleteExperimentRunPayload, ExperimentRun>(
    `/api/v1/experiment-runs/${runId}/complete`,
    payload,
    { token }
  );
}
