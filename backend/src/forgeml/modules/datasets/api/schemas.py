from typing import Literal

from pydantic import BaseModel, Field


class SchemaFieldPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dtype: str = Field(min_length=1, max_length=64)
    nullable: bool


class CreateDatasetRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    source_type: Literal["upload", "s3", "database", "stream"] = "upload"


class DatasetResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    source_type: str
    status: str


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    next_cursor: str | None = None


class CreateDatasetVersionRequest(BaseModel):
    filename: str = Field(default="dataset.csv", min_length=1, max_length=255)
    content_type: str = Field(default="text/csv", min_length=1, max_length=255)


class UploadInstructionsResponse(BaseModel):
    upload_url: str
    object_uri: str
    expires_at: str
    required_headers: dict[str, str]


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_id: str
    version: int
    object_uri: str
    content_hash: str
    row_count: int
    size_bytes: int
    status: str
    created_by: str


class CreateDatasetVersionResponse(BaseModel):
    version: DatasetVersionResponse
    upload: UploadInstructionsResponse


class DatasetVersionListResponse(BaseModel):
    items: list[DatasetVersionResponse]
    next_cursor: str | None = None


class FinalizeDatasetVersionRequest(BaseModel):
    object_uri: str | None = Field(default=None, max_length=2048)
    content_hash: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)
    row_count: int | None = Field(default=None, ge=0)
    schema_fields: list[SchemaFieldPayload] | None = None
    sample_csv: str | None = Field(default=None, max_length=500_000)


class DatasetSchemaResponse(BaseModel):
    dataset_version_id: str
    fields: list[SchemaFieldPayload]
    inferred: bool
    schema_hash: str


class DatasetValidationRunResponse(BaseModel):
    id: str
    dataset_version_id: str
    status: str
    report: dict[str, object]
    error_message: str | None


class DatasetValidationRunListResponse(BaseModel):
    items: list[DatasetValidationRunResponse]
    next_cursor: str | None = None
