from dataclasses import dataclass
from uuid import UUID, uuid4

from forgeml.modules.datasets.domain.entities import (
    Dataset,
    DatasetSchema,
    DatasetSourceType,
    DatasetStatus,
    DatasetValidationRun,
    DatasetValidationStatus,
    DatasetVersion,
    DatasetVersionStatus,
    SchemaField,
)
from forgeml.modules.datasets.domain.policies import (
    build_dataset_slug,
    infer_schema_from_csv,
    schema_hash,
    validate_dataset_name,
    validate_dataset_version_metadata,
)
from forgeml.modules.datasets.repositories.interfaces import (
    DatasetRepository,
    ObjectStorageGateway,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class UploadInstructionsDto:
    upload_url: str
    object_uri: str
    expires_at: str
    required_headers: dict[str, str]


@dataclass(frozen=True)
class DatasetVersionUpload:
    version: DatasetVersion
    upload: UploadInstructionsDto


@dataclass(frozen=True)
class CreateDatasetCommand:
    organization_id: UUID
    project_id: UUID
    name: str
    description: str
    source_type: DatasetSourceType


@dataclass(frozen=True)
class CreateDatasetVersionCommand:
    dataset_id: UUID
    created_by: UUID
    filename: str
    content_type: str


@dataclass(frozen=True)
class FinalizeDatasetVersionCommand:
    version_id: UUID
    object_uri: str | None
    content_hash: str
    size_bytes: int
    row_count: int | None
    schema_fields: tuple[SchemaField, ...] | None = None
    sample_csv: str | None = None


class DatasetService:
    def __init__(
        self,
        *,
        datasets: DatasetRepository,
        object_storage: ObjectStorageGateway,
    ) -> None:
        self._datasets = datasets
        self._object_storage = object_storage

    def create_dataset(self, command: CreateDatasetCommand, principal: Principal) -> Dataset:
        self._require(principal, "datasets:create")
        self._require_same_organization(command.organization_id, principal)
        validate_dataset_name(command.name)
        slug = build_dataset_slug(command.name)
        if self._datasets.dataset_slug_exists(command.organization_id, command.project_id, slug):
            raise ConflictError("A dataset with this name already exists in the project.")

        dataset = Dataset(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            source_type=command.source_type,
            status=DatasetStatus.ACTIVE,
        )
        return self._datasets.add_dataset(dataset)

    def list_datasets(self, project_id: UUID, principal: Principal) -> list[Dataset]:
        self._require(principal, "datasets:read")
        return self._datasets.list_datasets(UUID(principal.organization_id), project_id)

    def get_dataset(self, dataset_id: UUID, principal: Principal) -> Dataset:
        self._require(principal, "datasets:read")
        return self._get_scoped_dataset(dataset_id, principal)

    def create_version(
        self,
        command: CreateDatasetVersionCommand,
        principal: Principal,
    ) -> DatasetVersionUpload:
        self._require(principal, "dataset_versions:create")
        dataset = self._get_scoped_dataset(command.dataset_id, principal)
        next_version = self._datasets.latest_version_number(dataset.id) + 1
        version_id = uuid4()
        upload = self._object_storage.create_upload_instructions(
            organization_id=dataset.organization_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            version_id=version_id,
            filename=command.filename,
            content_type=command.content_type,
        )
        version = DatasetVersion(
            id=version_id,
            dataset_id=dataset.id,
            version=next_version,
            object_uri=upload.object_uri,
            content_hash="",
            row_count=0,
            size_bytes=0,
            status=DatasetVersionStatus.PENDING_UPLOAD,
            created_by=command.created_by,
        )
        saved = self._datasets.add_version(version)
        return DatasetVersionUpload(
            version=saved,
            upload=UploadInstructionsDto(
                upload_url=upload.upload_url,
                object_uri=upload.object_uri,
                expires_at=upload.expires_at,
                required_headers=upload.required_headers,
            ),
        )

    def list_versions(self, dataset_id: UUID, principal: Principal) -> list[DatasetVersion]:
        self._require(principal, "datasets:read")
        dataset = self._get_scoped_dataset(dataset_id, principal)
        return self._datasets.list_versions(dataset.id)

    def get_version(self, version_id: UUID, principal: Principal) -> DatasetVersion:
        self._require(principal, "datasets:read")
        version, _dataset = self._get_scoped_version(version_id, principal)
        return version

    def finalize_version(
        self,
        command: FinalizeDatasetVersionCommand,
        principal: Principal,
    ) -> DatasetVersion:
        self._require(principal, "dataset_versions:finalize")
        version, _dataset = self._get_scoped_version(command.version_id, principal)
        if version.status != DatasetVersionStatus.PENDING_UPLOAD:
            raise ConflictError("Only pending dataset versions can be finalized.")

        fields, inferred_row_count = self._resolve_schema_fields(command)
        row_count = command.row_count if command.row_count is not None else inferred_row_count
        if row_count is None:
            raise DomainValidationError("Row count is required when no CSV sample is provided.")
        validate_dataset_version_metadata(
            content_hash=command.content_hash,
            size_bytes=command.size_bytes,
            row_count=row_count,
        )

        finalized = DatasetVersion(
            id=version.id,
            dataset_id=version.dataset_id,
            version=version.version,
            object_uri=command.object_uri or version.object_uri,
            content_hash=command.content_hash,
            row_count=row_count,
            size_bytes=command.size_bytes,
            status=DatasetVersionStatus.VALIDATED,
            created_by=version.created_by,
        )
        self._datasets.update_version(finalized)
        self._datasets.save_schema(
            DatasetSchema(
                dataset_version_id=version.id,
                fields=fields,
                inferred=command.schema_fields is None,
                schema_hash=schema_hash(fields),
            )
        )
        self._datasets.add_validation_run(
            DatasetValidationRun(
                id=uuid4(),
                dataset_version_id=version.id,
                status=DatasetValidationStatus.COMPLETED,
                report={
                    "row_count": row_count,
                    "field_count": len(fields),
                    "checks": ["schema_present", "metadata_valid", "version_immutable"],
                },
                error_message=None,
            )
        )
        return finalized

    def get_schema(self, version_id: UUID, principal: Principal) -> DatasetSchema:
        self._require(principal, "datasets:read")
        self._get_scoped_version(version_id, principal)
        schema = self._datasets.get_schema(version_id)
        if schema is None:
            raise ResourceNotFoundError("Dataset version schema was not found.")
        return schema

    def list_validation_runs(
        self,
        version_id: UUID,
        principal: Principal,
    ) -> list[DatasetValidationRun]:
        self._require(principal, "datasets:read")
        self._get_scoped_version(version_id, principal)
        return self._datasets.list_validation_runs(version_id)

    def validate_version(self, version_id: UUID, principal: Principal) -> DatasetValidationRun:
        self._require(principal, "dataset_versions:validate")
        version, _dataset = self._get_scoped_version(version_id, principal)
        schema = self._datasets.get_schema(version.id)
        if schema is None:
            run = DatasetValidationRun(
                id=uuid4(),
                dataset_version_id=version.id,
                status=DatasetValidationStatus.FAILED,
                report={"checks": ["schema_present"], "field_count": 0},
                error_message="Dataset version has no schema.",
            )
            return self._datasets.add_validation_run(run)

        run = DatasetValidationRun(
            id=uuid4(),
            dataset_version_id=version.id,
            status=DatasetValidationStatus.COMPLETED,
            report={
                "checks": ["schema_present", "metadata_valid"],
                "field_count": len(schema.fields),
                "row_count": version.row_count,
            },
            error_message=None,
        )
        return self._datasets.add_validation_run(run)

    def _resolve_schema_fields(
        self,
        command: FinalizeDatasetVersionCommand,
    ) -> tuple[tuple[SchemaField, ...], int | None]:
        if command.schema_fields is not None:
            if len(command.schema_fields) == 0:
                raise DomainValidationError("Dataset schema must contain at least one field.")
            return command.schema_fields, None
        if command.sample_csv is None:
            raise DomainValidationError("Dataset schema fields or a CSV sample are required.")
        fields, row_count = infer_schema_from_csv(command.sample_csv)
        if len(fields) == 0:
            raise DomainValidationError("Dataset schema must contain at least one field.")
        return fields, row_count

    def _get_scoped_dataset(self, dataset_id: UUID, principal: Principal) -> Dataset:
        dataset = self._datasets.get_dataset(dataset_id)
        if dataset is None or str(dataset.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Dataset was not found.")
        return dataset

    def _get_scoped_version(
        self,
        version_id: UUID,
        principal: Principal,
    ) -> tuple[DatasetVersion, Dataset]:
        version = self._datasets.get_version(version_id)
        if version is None:
            raise ResourceNotFoundError("Dataset version was not found.")
        dataset = self._get_scoped_dataset(version.dataset_id, principal)
        return version, dataset

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage datasets.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage datasets in another organization.")

