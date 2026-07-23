import { apiGet, apiPost } from "../../../shared/api/client";

export type FeatureSet = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  entity_key: string;
  status: string;
};

export type FeatureDefinition = {
  id: string;
  feature_set_id: string;
  name: string;
  dtype: string;
  description: string;
  nullable: boolean;
  constraints: Record<string, unknown>;
};

export type FeaturePipeline = {
  id: string;
  feature_set_id: string;
  name: string;
  source_dataset_id: string | null;
  code_ref: string;
  schedule_cron: string | null;
  status: string;
};

export type FeatureMaterialization = {
  id: string;
  feature_set_id: string;
  pipeline_id: string;
  version: number;
  offline_uri: string;
  online_ref: string | null;
  orchestrator_run_id: string;
  status: string;
};

export type FeatureLineage = {
  id: string;
  feature_set_id: string;
  upstream_type: string;
  upstream_id: string;
};

export type FeatureSetListResponse = {
  items: FeatureSet[];
  next_cursor: string | null;
};

export type FeatureDefinitionListResponse = {
  items: FeatureDefinition[];
  next_cursor: string | null;
};

export type FeaturePipelineListResponse = {
  items: FeaturePipeline[];
  next_cursor: string | null;
};

export type FeatureMaterializationListResponse = {
  items: FeatureMaterialization[];
  next_cursor: string | null;
};

export type FeatureLineageListResponse = {
  items: FeatureLineage[];
  next_cursor: string | null;
};

export type CreateFeatureSetPayload = {
  name: string;
  description: string;
  entity_key: string;
};

export type FeatureDefinitionPayload = {
  name: string;
  dtype: string;
  description: string;
  nullable: boolean;
  constraints: Record<string, unknown>;
};

export type RegisterFeatureDefinitionsPayload = {
  definitions: FeatureDefinitionPayload[];
};

export type RegisterFeaturePipelinePayload = {
  name: string;
  source_dataset_id: string | null;
  code_ref: string;
  schedule_cron: string | null;
};

export function createFeatureSet(
  projectId: string,
  payload: CreateFeatureSetPayload,
  token: string
): Promise<FeatureSet> {
  return apiPost<CreateFeatureSetPayload, FeatureSet>(
    `/api/v1/projects/${projectId}/feature-sets`,
    payload,
    { token }
  );
}

export function listFeatureSets(
  projectId: string,
  token: string
): Promise<FeatureSetListResponse> {
  return apiGet<FeatureSetListResponse>(`/api/v1/projects/${projectId}/feature-sets`, {
    token
  });
}

export function registerFeatureDefinitions(
  featureSetId: string,
  payload: RegisterFeatureDefinitionsPayload,
  token: string
): Promise<FeatureDefinitionListResponse> {
  return apiPost<RegisterFeatureDefinitionsPayload, FeatureDefinitionListResponse>(
    `/api/v1/feature-sets/${featureSetId}/features`,
    payload,
    { token }
  );
}

export function listFeatureDefinitions(
  featureSetId: string,
  token: string
): Promise<FeatureDefinitionListResponse> {
  return apiGet<FeatureDefinitionListResponse>(
    `/api/v1/feature-sets/${featureSetId}/features`,
    { token }
  );
}

export function registerFeaturePipeline(
  featureSetId: string,
  payload: RegisterFeaturePipelinePayload,
  token: string
): Promise<FeaturePipeline> {
  return apiPost<RegisterFeaturePipelinePayload, FeaturePipeline>(
    `/api/v1/feature-sets/${featureSetId}/pipelines`,
    payload,
    { token }
  );
}

export function listFeaturePipelines(
  featureSetId: string,
  token: string
): Promise<FeaturePipelineListResponse> {
  return apiGet<FeaturePipelineListResponse>(
    `/api/v1/feature-sets/${featureSetId}/pipelines`,
    { token }
  );
}

export function materializeFeaturePipeline(
  pipelineId: string,
  token: string
): Promise<FeatureMaterialization> {
  return apiPost<Record<string, never>, FeatureMaterialization>(
    `/api/v1/feature-pipelines/${pipelineId}/materialize`,
    {},
    { token }
  );
}

export function listFeatureMaterializations(
  featureSetId: string,
  token: string
): Promise<FeatureMaterializationListResponse> {
  return apiGet<FeatureMaterializationListResponse>(
    `/api/v1/feature-sets/${featureSetId}/materializations`,
    { token }
  );
}

export function listFeatureLineage(
  featureSetId: string,
  token: string
): Promise<FeatureLineageListResponse> {
  return apiGet<FeatureLineageListResponse>(
    `/api/v1/feature-sets/${featureSetId}/lineage`,
    { token }
  );
}
