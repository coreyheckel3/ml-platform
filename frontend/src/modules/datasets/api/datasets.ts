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

export type DatasetVersion = {
  id: string;
  dataset_id: string;
  version: number;
  object_uri: string;
  content_hash: string;
  row_count: number;
  size_bytes: number;
  status: string;
  created_by: string;
};

export type DatasetListResponse = {
  items: Dataset[];
  next_cursor: string | null;
};

export type DatasetVersionListResponse = {
  items: DatasetVersion[];
  next_cursor: string | null;
};

export function listDatasets(projectId: string, token: string): Promise<DatasetListResponse> {
  return apiGet<DatasetListResponse>(`/api/v1/projects/${projectId}/datasets`, { token });
}

export function listDatasetVersions(
  datasetId: string,
  token: string
): Promise<DatasetVersionListResponse> {
  return apiGet<DatasetVersionListResponse>(`/api/v1/datasets/${datasetId}/versions`, { token });
}
