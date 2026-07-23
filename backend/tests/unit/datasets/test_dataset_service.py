from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from forgeml.modules.datasets.application.services import (
    CreateDatasetCommand,
    CreateDatasetVersionCommand,
    DatasetService,
    FinalizeDatasetVersionCommand,
)
from forgeml.modules.datasets.domain.entities import (
    Dataset,
    DatasetSchema,
    DatasetSourceType,
    DatasetStatus,
    DatasetValidationRun,
    DatasetVersion,
    DatasetVersionStatus,
)
from forgeml.platform.domain.errors import ConflictError, PermissionDeniedError
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class FakeUploadInstructions:
    upload_url: str
    object_uri: str
    expires_at: str
    required_headers: dict[str, str]


class FakeObjectStorage:
    def create_upload_instructions(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version_id: UUID,
        filename: str,
        content_type: str,
    ) -> FakeUploadInstructions:
        return FakeUploadInstructions(
            upload_url=f"https://storage.local/{version_id}/{filename}",
            object_uri=f"s3://forgeml/{dataset_id}/{version_id}/{filename}",
            expires_at="2026-07-18T00:15:00+00:00",
            required_headers={"content-type": content_type},
        )


class FakeDatasetRepository:
    def __init__(self) -> None:
        self.datasets: dict[UUID, Dataset] = {}
        self.versions: dict[UUID, DatasetVersion] = {}
        self.schemas: dict[UUID, DatasetSchema] = {}
        self.validation_runs: list[DatasetValidationRun] = []

    def add_dataset(self, dataset: Dataset) -> Dataset:
        self.datasets[dataset.id] = dataset
        return dataset

    def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        return self.datasets.get(dataset_id)

    def list_datasets(self, organization_id: UUID, project_id: UUID) -> list[Dataset]:
        return [
            dataset
            for dataset in self.datasets.values()
            if dataset.organization_id == organization_id and dataset.project_id == project_id
        ]

    def dataset_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return any(
            dataset.organization_id == organization_id
            and dataset.project_id == project_id
            and dataset.slug == slug
            for dataset in self.datasets.values()
        )

    def latest_version_number(self, dataset_id: UUID) -> int:
        return max(
            (
                version.version
                for version in self.versions.values()
                if version.dataset_id == dataset_id
            ),
            default=0,
        )

    def add_version(self, version: DatasetVersion) -> DatasetVersion:
        self.versions[version.id] = version
        return version

    def get_version(self, version_id: UUID) -> DatasetVersion | None:
        return self.versions.get(version_id)

    def list_versions(self, dataset_id: UUID) -> list[DatasetVersion]:
        return [version for version in self.versions.values() if version.dataset_id == dataset_id]

    def update_version(self, version: DatasetVersion) -> DatasetVersion:
        self.versions[version.id] = version
        return version

    def save_schema(self, schema: DatasetSchema) -> DatasetSchema:
        self.schemas[schema.dataset_version_id] = schema
        return schema

    def get_schema(self, dataset_version_id: UUID) -> DatasetSchema | None:
        return self.schemas.get(dataset_version_id)

    def add_validation_run(self, run: DatasetValidationRun) -> DatasetValidationRun:
        self.validation_runs.append(run)
        return run

    def list_validation_runs(self, dataset_version_id: UUID) -> list[DatasetValidationRun]:
        return [
            run for run in self.validation_runs if run.dataset_version_id == dataset_version_id
        ]


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_dataset_service_creates_dataset_and_upload_version() -> None:
    repository = FakeDatasetRepository()
    service = DatasetService(datasets=repository, object_storage=FakeObjectStorage())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(
        organization_id,
        user_id,
        {"datasets:create", "datasets:read", "dataset_versions:create"},
    )

    dataset = service.create_dataset(
        CreateDatasetCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Transactions",
            description="Payment events.",
            source_type=DatasetSourceType.UPLOAD,
        ),
        actor,
    )
    version_upload = service.create_version(
        CreateDatasetVersionCommand(
            dataset_id=dataset.id,
            created_by=user_id,
            filename="transactions.csv",
            content_type="text/csv",
        ),
        actor,
    )

    assert dataset.slug == "fraud-transactions"
    assert version_upload.version.version == 1
    assert version_upload.version.status == DatasetVersionStatus.PENDING_UPLOAD
    assert version_upload.upload.object_uri.startswith("s3://forgeml/")


def test_dataset_service_finalizes_version_with_inferred_schema() -> None:
    repository = FakeDatasetRepository()
    service = DatasetService(datasets=repository, object_storage=FakeObjectStorage())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(
        organization_id,
        user_id,
        {
            "datasets:create",
            "datasets:read",
            "dataset_versions:create",
            "dataset_versions:finalize",
        },
    )
    dataset = repository.add_dataset(
        Dataset(
            id=uuid4(),
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Transactions",
            slug="fraud-transactions",
            description="",
            source_type=DatasetSourceType.UPLOAD,
            status=DatasetStatus.ACTIVE,
        )
    )
    version = service.create_version(
        CreateDatasetVersionCommand(
            dataset_id=dataset.id,
            created_by=user_id,
            filename="transactions.csv",
            content_type="text/csv",
        ),
        actor,
    ).version

    finalized = service.finalize_version(
        FinalizeDatasetVersionCommand(
            version_id=version.id,
            object_uri=None,
            content_hash="sha256:abc123",
            size_bytes=128,
            row_count=None,
            sample_csv="id,amount\n1,12.5\n2,14.0\n",
        ),
        actor,
    )

    assert finalized.status == DatasetVersionStatus.VALIDATED
    assert finalized.row_count == 2
    assert repository.schemas[version.id].fields[1].dtype == "float"
    assert repository.validation_runs[-1].report["field_count"] == 2


def test_dataset_service_rejects_duplicate_dataset_slug() -> None:
    repository = FakeDatasetRepository()
    service = DatasetService(datasets=repository, object_storage=FakeObjectStorage())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"datasets:create"})
    command = CreateDatasetCommand(
        organization_id=organization_id,
        project_id=project_id,
        name="Movie Catalog",
        description="",
        source_type=DatasetSourceType.UPLOAD,
    )

    service.create_dataset(command, actor)

    with pytest.raises(ConflictError):
        service.create_dataset(command, actor)


def test_dataset_service_rejects_missing_permission() -> None:
    service = DatasetService(datasets=FakeDatasetRepository(), object_storage=FakeObjectStorage())
    organization_id = uuid4()
    user_id = uuid4()

    with pytest.raises(PermissionDeniedError):
        service.create_dataset(
            CreateDatasetCommand(
                organization_id=organization_id,
                project_id=uuid4(),
                name="Movie Catalog",
                description="",
                source_type=DatasetSourceType.UPLOAD,
            ),
            principal(organization_id, user_id, {"datasets:read"}),
        )

