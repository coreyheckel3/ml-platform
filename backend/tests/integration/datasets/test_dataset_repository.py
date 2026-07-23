from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
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
from forgeml.modules.datasets.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDatasetRepository,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.platform.database.base import Base


def test_dataset_repository_round_trips_dataset_version_schema_and_validation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    version_id = uuid4()

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            UserModel(
                id=user_id,
                organization_id=organization_id,
                email="owner@example.com",
                display_name="Owner",
                password_hash="hash",
                permissions_csv="*",
            )
        )
        session.add(
            ProjectModel(
                id=project_id,
                organization_id=organization_id,
                name="Fraud",
                slug="fraud",
                owner_user_id=user_id,
            )
        )
        repository = SqlAlchemyDatasetRepository(session)
        dataset = repository.add_dataset(
            Dataset(
                id=dataset_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Transactions",
                slug="transactions",
                description="",
                source_type=DatasetSourceType.UPLOAD,
                status=DatasetStatus.ACTIVE,
            )
        )
        version = repository.add_version(
            DatasetVersion(
                id=version_id,
                dataset_id=dataset.id,
                version=1,
                object_uri="s3://forgeml/transactions.csv",
                content_hash="",
                row_count=0,
                size_bytes=0,
                status=DatasetVersionStatus.PENDING_UPLOAD,
                created_by=user_id,
            )
        )
        repository.update_version(
            DatasetVersion(
                id=version.id,
                dataset_id=dataset.id,
                version=1,
                object_uri=version.object_uri,
                content_hash="sha256:abc123",
                row_count=2,
                size_bytes=128,
                status=DatasetVersionStatus.VALIDATED,
                created_by=user_id,
            )
        )
        repository.save_schema(
            DatasetSchema(
                dataset_version_id=version.id,
                fields=(SchemaField(name="amount", dtype="float", nullable=False),),
                inferred=True,
                schema_hash="hash123",
            )
        )
        repository.add_validation_run(
            DatasetValidationRun(
                id=uuid4(),
                dataset_version_id=version.id,
                status=DatasetValidationStatus.COMPLETED,
                report={"field_count": 1},
                error_message=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyDatasetRepository(session)

        datasets = repository.list_datasets(organization_id, project_id)
        versions = repository.list_versions(dataset_id)
        schema = repository.get_schema(version_id)
        runs = repository.list_validation_runs(version_id)

    assert datasets[0].slug == "transactions"
    assert versions[0].status == DatasetVersionStatus.VALIDATED
    assert schema is not None
    assert schema.fields[0].dtype == "float"
    assert runs[0].status == DatasetValidationStatus.COMPLETED
