import { apiGet } from "../../../shared/api/client";

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

export type FeatureSetListResponse = {
  items: FeatureSet[];
  next_cursor: string | null;
};

export function listFeatureSets(
  projectId: string,
  token: string
): Promise<FeatureSetListResponse> {
  return apiGet<FeatureSetListResponse>(`/api/v1/projects/${projectId}/feature-sets`, {
    token
  });
}

