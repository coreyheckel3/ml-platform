import { apiGet } from "../../../shared/api/client";

export type Dataset = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  source_type: string;
  status: string;
};

export type DatasetListResponse = {
  items: Dataset[];
  next_cursor: string | null;
};

export function listDatasets(projectId: string, token: string): Promise<DatasetListResponse> {
  return apiGet<DatasetListResponse>(`/api/v1/projects/${projectId}/datasets`, { token });
}
