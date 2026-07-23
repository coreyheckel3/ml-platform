import { apiGet, apiPost } from "../../../shared/api/client";

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

export type SchemaField = {
  name: string;
  dtype: string;
  nullable: boolean;
};

export type UploadInstructions = {
  upload_url: string;
  object_uri: string;
  expires_at: string;
  required_headers: Record<string, string>;
};

export type DatasetSchema = {
  dataset_version_id: string;
  fields: SchemaField[];
  inferred: boolean;
  schema_hash: string;
};

export type DatasetValidationRun = {
  id: string;
  dataset_version_id: string;
  status: string;
  report: Record<string, unknown>;
  error_message: string | null;
};

export type DatasetListResponse = {
  items: Dataset[];
  next_cursor: string | null;
};

export type DatasetVersionListResponse = {
  items: DatasetVersion[];
  next_cursor: string | null;
};

export type CreateDatasetVersionResponse = {
  version: DatasetVersion;
  upload: UploadInstructions;
};

export type DatasetValidationRunListResponse = {
  items: DatasetValidationRun[];
  next_cursor: string | null;
};

export type CreateDatasetPayload = {
  name: string;
  description: string;
  source_type: "upload" | "s3" | "database" | "stream";
};

export type CreateDatasetVersionPayload = {
  filename: string;
  content_type: string;
};

export type FinalizeDatasetVersionPayload = {
  object_uri: string | null;
  content_hash: string;
  size_bytes: number;
  row_count: number | null;
  schema_fields: SchemaField[] | null;
  sample_csv: string | null;
};

export function createDataset(
  projectId: string,
  payload: CreateDatasetPayload,
  token: string
): Promise<Dataset> {
  return apiPost<CreateDatasetPayload, Dataset>(
    `/api/v1/projects/${projectId}/datasets`,
    payload,
    { token }
  );
}

export function listDatasets(projectId: string, token: string): Promise<DatasetListResponse> {
  return apiGet<DatasetListResponse>(`/api/v1/projects/${projectId}/datasets`, { token });
}

export function listDatasetVersions(
  datasetId: string,
  token: string
): Promise<DatasetVersionListResponse> {
  return apiGet<DatasetVersionListResponse>(`/api/v1/datasets/${datasetId}/versions`, { token });
}

export function createDatasetVersion(
  datasetId: string,
  payload: CreateDatasetVersionPayload,
  token: string
): Promise<CreateDatasetVersionResponse> {
  return apiPost<CreateDatasetVersionPayload, CreateDatasetVersionResponse>(
    `/api/v1/datasets/${datasetId}/versions`,
    payload,
    { token }
  );
}

export function finalizeDatasetVersion(
  datasetVersionId: string,
  payload: FinalizeDatasetVersionPayload,
  token: string
): Promise<DatasetVersion> {
  return apiPost<FinalizeDatasetVersionPayload, DatasetVersion>(
    `/api/v1/dataset-versions/${datasetVersionId}/finalize`,
    payload,
    { token }
  );
}

export function getDatasetSchema(
  datasetVersionId: string,
  token: string
): Promise<DatasetSchema> {
  return apiGet<DatasetSchema>(`/api/v1/dataset-versions/${datasetVersionId}/schema`, {
    token
  });
}

export function validateDatasetVersion(
  datasetVersionId: string,
  token: string
): Promise<DatasetValidationRun> {
  return apiPost<Record<string, never>, DatasetValidationRun>(
    `/api/v1/dataset-versions/${datasetVersionId}/validate`,
    {},
    { token }
  );
}

export function listDatasetValidationRuns(
  datasetVersionId: string,
  token: string
): Promise<DatasetValidationRunListResponse> {
  return apiGet<DatasetValidationRunListResponse>(
    `/api/v1/dataset-versions/${datasetVersionId}/validation-runs`,
    { token }
  );
}
