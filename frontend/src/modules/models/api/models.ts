import { apiGet, apiPost } from "../../../shared/api/client";

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

export type ModelApproval = {
  id: string;
  model_version_id: string;
  status: string;
  requested_by: string;
  reviewer_id: string | null;
  comment: string;
  policy_snapshot: Record<string, unknown>;
};

export type RegisteredModelListResponse = {
  items: RegisteredModel[];
  next_cursor: string | null;
};

export type ModelVersionListResponse = {
  items: ModelVersion[];
  next_cursor: string | null;
};

export type PromoteTrainingRunPayload = {
  training_run_id: string;
  model_format: string;
  signature: Record<string, unknown>;
};

export type RequestModelApprovalPayload = {
  comment: string;
};

export type ReviewModelVersionPayload = {
  status: "approved" | "rejected";
  comment: string;
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

export function promoteTrainingRunToModelVersion(
  modelId: string,
  payload: PromoteTrainingRunPayload,
  token: string
): Promise<ModelVersion> {
  return apiPost<PromoteTrainingRunPayload, ModelVersion>(
    `/api/v1/models/${modelId}/versions/promote-training-run`,
    payload,
    { token }
  );
}

export function requestModelApproval(
  versionId: string,
  payload: RequestModelApprovalPayload,
  token: string
): Promise<ModelApproval> {
  return apiPost<RequestModelApprovalPayload, ModelApproval>(
    `/api/v1/model-versions/${versionId}/approval-request`,
    payload,
    { token }
  );
}

export function reviewModelVersion(
  versionId: string,
  payload: ReviewModelVersionPayload,
  token: string
): Promise<ModelApproval> {
  return apiPost<ReviewModelVersionPayload, ModelApproval>(
    `/api/v1/model-versions/${versionId}/review`,
    payload,
    { token }
  );
}
