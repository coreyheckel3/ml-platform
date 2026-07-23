from typing import Protocol
from uuid import UUID

from forgeml.modules.datasets.domain.entities import (
    Dataset,
    DatasetSchema,
    DatasetValidationRun,
    DatasetVersion,
)


class DatasetRepository(Protocol):
    def add_dataset(self, dataset: Dataset) -> Dataset:
        raise NotImplementedError

    def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        raise NotImplementedError

    def list_datasets(self, organization_id: UUID, project_id: UUID) -> list[Dataset]:
        raise NotImplementedError

    def dataset_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        raise NotImplementedError

    def latest_version_number(self, dataset_id: UUID) -> int:
        raise NotImplementedError

    def add_version(self, version: DatasetVersion) -> DatasetVersion:
        raise NotImplementedError

    def get_version(self, version_id: UUID) -> DatasetVersion | None:
        raise NotImplementedError

    def list_versions(self, dataset_id: UUID) -> list[DatasetVersion]:
        raise NotImplementedError

    def update_version(self, version: DatasetVersion) -> DatasetVersion:
        raise NotImplementedError

    def save_schema(self, schema: DatasetSchema) -> DatasetSchema:
        raise NotImplementedError

    def get_schema(self, dataset_version_id: UUID) -> DatasetSchema | None:
        raise NotImplementedError

    def add_validation_run(self, run: DatasetValidationRun) -> DatasetValidationRun:
        raise NotImplementedError

    def list_validation_runs(self, dataset_version_id: UUID) -> list[DatasetValidationRun]:
        raise NotImplementedError


class ObjectStorageGateway(Protocol):
    def create_upload_instructions(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version_id: UUID,
        filename: str,
        content_type: str,
    ) -> "UploadInstructions":
        raise NotImplementedError


class UploadInstructions(Protocol):
    upload_url: str
    object_uri: str
    expires_at: str
    required_headers: dict[str, str]

