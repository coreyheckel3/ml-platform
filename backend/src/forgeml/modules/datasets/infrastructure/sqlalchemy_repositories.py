from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetSchemaModel,
    DatasetValidationRunModel,
    DatasetVersionModel,
)


class SqlAlchemyDatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_dataset(self, dataset: Dataset) -> Dataset:
        model = DatasetModel(
            id=dataset.id,
            organization_id=dataset.organization_id,
            project_id=dataset.project_id,
            name=dataset.name,
            slug=dataset.slug,
            description=dataset.description,
            source_type=dataset.source_type.value,
            status=dataset.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return _dataset_to_domain(model)

    def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        model = self._session.get(DatasetModel, dataset_id)
        return _dataset_to_domain(model) if model else None

    def list_datasets(self, organization_id: UUID, project_id: UUID) -> list[Dataset]:
        models = self._session.scalars(
            select(DatasetModel)
            .where(
                DatasetModel.organization_id == organization_id,
                DatasetModel.project_id == project_id,
            )
            .order_by(DatasetModel.name)
        ).all()
        return [_dataset_to_domain(model) for model in models]

    def dataset_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return (
            self._session.scalar(
                select(DatasetModel.id).where(
                    DatasetModel.organization_id == organization_id,
                    DatasetModel.project_id == project_id,
                    DatasetModel.slug == slug,
                )
            )
            is not None
        )

    def latest_version_number(self, dataset_id: UUID) -> int:
        versions = self._session.scalars(
            select(DatasetVersionModel.version).where(DatasetVersionModel.dataset_id == dataset_id)
        ).all()
        return max(versions, default=0)

    def add_version(self, version: DatasetVersion) -> DatasetVersion:
        model = DatasetVersionModel(
            id=version.id,
            dataset_id=version.dataset_id,
            version=version.version,
            object_uri=version.object_uri,
            content_hash=version.content_hash,
            row_count=version.row_count,
            size_bytes=version.size_bytes,
            status=version.status.value,
            created_by=version.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _version_to_domain(model)

    def get_version(self, version_id: UUID) -> DatasetVersion | None:
        model = self._session.get(DatasetVersionModel, version_id)
        return _version_to_domain(model) if model else None

    def list_versions(self, dataset_id: UUID) -> list[DatasetVersion]:
        models = self._session.scalars(
            select(DatasetVersionModel)
            .where(DatasetVersionModel.dataset_id == dataset_id)
            .order_by(DatasetVersionModel.version.desc())
        ).all()
        return [_version_to_domain(model) for model in models]

    def update_version(self, version: DatasetVersion) -> DatasetVersion:
        model = self._session.get(DatasetVersionModel, version.id)
        if model is None:
            raise ValueError("Dataset version does not exist.")
        model.object_uri = version.object_uri
        model.content_hash = version.content_hash
        model.row_count = version.row_count
        model.size_bytes = version.size_bytes
        model.status = version.status.value
        self._session.flush()
        return _version_to_domain(model)

    def save_schema(self, schema: DatasetSchema) -> DatasetSchema:
        model = DatasetSchemaModel(
            dataset_version_id=schema.dataset_version_id,
            fields_json=[
                {"name": field.name, "dtype": field.dtype, "nullable": field.nullable}
                for field in schema.fields
            ],
            inferred=schema.inferred,
            schema_hash=schema.schema_hash,
        )
        self._session.merge(model)
        self._session.flush()
        return schema

    def get_schema(self, dataset_version_id: UUID) -> DatasetSchema | None:
        model = self._session.get(DatasetSchemaModel, dataset_version_id)
        return _schema_to_domain(model) if model else None

    def add_validation_run(self, run: DatasetValidationRun) -> DatasetValidationRun:
        model = DatasetValidationRunModel(
            id=run.id,
            dataset_version_id=run.dataset_version_id,
            status=run.status.value,
            report_json=run.report,
            error_message=run.error_message,
        )
        self._session.add(model)
        self._session.flush()
        return _validation_run_to_domain(model)

    def list_validation_runs(self, dataset_version_id: UUID) -> list[DatasetValidationRun]:
        models = self._session.scalars(
            select(DatasetValidationRunModel)
            .where(DatasetValidationRunModel.dataset_version_id == dataset_version_id)
            .order_by(DatasetValidationRunModel.created_at.desc())
        ).all()
        return [_validation_run_to_domain(model) for model in models]


def _dataset_to_domain(model: DatasetModel) -> Dataset:
    return Dataset(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        source_type=DatasetSourceType(model.source_type),
        status=DatasetStatus(model.status),
    )


def _version_to_domain(model: DatasetVersionModel) -> DatasetVersion:
    return DatasetVersion(
        id=model.id,
        dataset_id=model.dataset_id,
        version=model.version,
        object_uri=model.object_uri,
        content_hash=model.content_hash,
        row_count=model.row_count,
        size_bytes=model.size_bytes,
        status=DatasetVersionStatus(model.status),
        created_by=model.created_by,
    )


def _schema_to_domain(model: DatasetSchemaModel) -> DatasetSchema:
    return DatasetSchema(
        dataset_version_id=model.dataset_version_id,
        fields=tuple(
            SchemaField(
                name=str(field["name"]),
                dtype=str(field["dtype"]),
                nullable=bool(field["nullable"]),
            )
            for field in model.fields_json
        ),
        inferred=model.inferred,
        schema_hash=model.schema_hash,
    )


def _validation_run_to_domain(model: DatasetValidationRunModel) -> DatasetValidationRun:
    return DatasetValidationRun(
        id=model.id,
        dataset_version_id=model.dataset_version_id,
        status=DatasetValidationStatus(model.status),
        report=model.report_json,
        error_message=model.error_message,
    )

