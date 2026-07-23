import { apiGet } from "../../../shared/api/client";

export type Deployment = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  environment: string;
  status: string;
  created_by: string;
};

export type DeploymentRevision = {
  id: string;
  deployment_id: string;
  model_version_id: string;
  revision: number;
  serving_image: string;
  runtime_config: Record<string, unknown>;
  traffic_percentage: number;
  status: string;
  orchestrator_deployment_id: string;
  created_by: string;
};

export type DeploymentListResponse = {
  items: Deployment[];
  next_cursor: string | null;
};

export type DeploymentRevisionListResponse = {
  items: DeploymentRevision[];
  next_cursor: string | null;
};

export function listDeployments(
  projectId: string,
  token: string
): Promise<DeploymentListResponse> {
  return apiGet<DeploymentListResponse>(`/api/v1/projects/${projectId}/deployments`, {
    token
  });
}

export function listDeploymentRevisions(
  deploymentId: string,
  token: string
): Promise<DeploymentRevisionListResponse> {
  return apiGet<DeploymentRevisionListResponse>(
    `/api/v1/deployments/${deploymentId}/revisions`,
    { token }
  );
}
