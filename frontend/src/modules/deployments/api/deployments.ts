import { apiGet, apiPost } from "../../../shared/api/client";

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

export type DeploymentHealthCheck = {
  id: string;
  deployment_revision_id: string;
  status: string;
  latency_ms: number;
  error_rate: number;
  details: Record<string, unknown>;
};

export type DeploymentEvent = {
  id: string;
  deployment_id: string;
  deployment_revision_id: string | null;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
};

export type DeploymentListResponse = {
  items: Deployment[];
  next_cursor: string | null;
};

export type DeploymentRevisionListResponse = {
  items: DeploymentRevision[];
  next_cursor: string | null;
};

export type DeploymentHealthCheckListResponse = {
  items: DeploymentHealthCheck[];
  next_cursor: string | null;
};

export type DeploymentEventListResponse = {
  items: DeploymentEvent[];
  next_cursor: string | null;
};

export type CreateDeploymentPayload = {
  name: string;
  description: string;
  environment: string;
};

export type CreateDeploymentRevisionPayload = {
  model_version_id: string;
  serving_image: string;
  runtime_config: Record<string, unknown>;
  traffic_percentage: number;
};

export type UpdateDeploymentTrafficPayload = {
  traffic_percentage: number;
};

export type RecordDeploymentHealthPayload = {
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms: number;
  error_rate: number;
  details: Record<string, unknown>;
};

export type RollbackDeploymentPayload = {
  target_revision_id: string;
};

export function createDeployment(
  projectId: string,
  payload: CreateDeploymentPayload,
  token: string,
): Promise<Deployment> {
  return apiPost<CreateDeploymentPayload, Deployment>(
    `/api/v1/projects/${projectId}/deployments`,
    payload,
    { token },
  );
}

export function listDeployments(
  projectId: string,
  token: string,
): Promise<DeploymentListResponse> {
  return apiGet<DeploymentListResponse>(
    `/api/v1/projects/${projectId}/deployments`,
    {
      token,
    },
  );
}

export function listDeploymentRevisions(
  deploymentId: string,
  token: string,
): Promise<DeploymentRevisionListResponse> {
  return apiGet<DeploymentRevisionListResponse>(
    `/api/v1/deployments/${deploymentId}/revisions`,
    { token },
  );
}

export function createDeploymentRevision(
  deploymentId: string,
  payload: CreateDeploymentRevisionPayload,
  token: string,
): Promise<DeploymentRevision> {
  return apiPost<CreateDeploymentRevisionPayload, DeploymentRevision>(
    `/api/v1/deployments/${deploymentId}/revisions`,
    payload,
    { token },
  );
}

export function updateDeploymentTraffic(
  revisionId: string,
  payload: UpdateDeploymentTrafficPayload,
  token: string,
): Promise<DeploymentRevision> {
  return apiPost<UpdateDeploymentTrafficPayload, DeploymentRevision>(
    `/api/v1/deployment-revisions/${revisionId}/traffic`,
    payload,
    { token },
  );
}

export function recordDeploymentHealth(
  revisionId: string,
  payload: RecordDeploymentHealthPayload,
  token: string,
): Promise<DeploymentHealthCheck> {
  return apiPost<RecordDeploymentHealthPayload, DeploymentHealthCheck>(
    `/api/v1/deployment-revisions/${revisionId}/health-checks`,
    payload,
    { token },
  );
}

export function listDeploymentHealthChecks(
  revisionId: string,
  token: string,
): Promise<DeploymentHealthCheckListResponse> {
  return apiGet<DeploymentHealthCheckListResponse>(
    `/api/v1/deployment-revisions/${revisionId}/health-checks`,
    { token },
  );
}

export function rollbackDeployment(
  deploymentId: string,
  payload: RollbackDeploymentPayload,
  token: string,
): Promise<DeploymentRevision> {
  return apiPost<RollbackDeploymentPayload, DeploymentRevision>(
    `/api/v1/deployments/${deploymentId}/rollback`,
    payload,
    { token },
  );
}

export function listDeploymentEvents(
  deploymentId: string,
  token: string,
): Promise<DeploymentEventListResponse> {
  return apiGet<DeploymentEventListResponse>(
    `/api/v1/deployments/${deploymentId}/events`,
    {
      token,
    },
  );
}
