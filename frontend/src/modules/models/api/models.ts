import { apiGet } from "../../../shared/api/client";

export type RegisteredModel = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  task_type: string;
  owner_user_id: string;
  status: string;
};

export type ModelVersion = {
  id: string;
  registered_model_id: string;
  version: number;
  training_run_id: string;
  experiment_run_id: string;
  artifact_uri: string;
  model_format: string;
  signature: Record<string, unknown>;
  metrics: Record<string, number>;
  status: string;
  created_by: string;
};

export type RegisteredModelListResponse = {
  items: RegisteredModel[];
  next_cursor: string | null;
};

export type ModelVersionListResponse = {
  items: ModelVersion[];
  next_cursor: string | null;
};

export function listRegisteredModels(
  projectId: string,
  token: string
): Promise<RegisteredModelListResponse> {
  return apiGet<RegisteredModelListResponse>(`/api/v1/projects/${projectId}/models`, {
    token
  });
}

export function listModelVersions(
  modelId: string,
  token: string
): Promise<ModelVersionListResponse> {
  return apiGet<ModelVersionListResponse>(`/api/v1/models/${modelId}/versions`, {
    token
  });
}
