from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.datasets.api.routes import get_dataset_service
from forgeml.modules.datasets.application.services import (
    DatasetVersionUpload,
    UploadInstructionsDto,
)
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
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeDatasetService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    dataset_id: UUID
    version_id: UUID

    def create_dataset(self, command, principal):
        assert command.name == "Fraud Transactions"
        return self._dataset()

    def list_datasets(self, project_id, principal):
        assert project_id == self.project_id
        return [self._dataset()]

    def get_dataset(self, dataset_id, principal):
        assert dataset_id == self.dataset_id
        return self._dataset()

    def create_version(self, command, principal):
        assert command.filename == "transactions.csv"
        return DatasetVersionUpload(
            version=self._version(DatasetVersionStatus.PENDING_UPLOAD),
            upload=UploadInstructionsDto(
                upload_url="https://storage.local/upload",
                object_uri="s3://forgeml/transactions.csv",
                expires_at="2026-07-18T00:15:00+00:00",
                required_headers={"content-type": "text/csv"},
            ),
        )

    def list_versions(self, dataset_id, principal):
        assert dataset_id == self.dataset_id
        return [self._version(DatasetVersionStatus.VALIDATED)]

    def get_version(self, version_id, principal):
        assert version_id == self.version_id
        return self._version(DatasetVersionStatus.VALIDATED)

    def finalize_version(self, command, principal):
        assert command.content_hash == "sha256:abc123"
        return self._version(DatasetVersionStatus.VALIDATED)

    def get_schema(self, version_id, principal):
        assert version_id == self.version_id
        return DatasetSchema(
            dataset_version_id=self.version_id,
            fields=(SchemaField(name="amount", dtype="float", nullable=False),),
            inferred=True,
            schema_hash="abc123",
        )

    def validate_version(self, version_id, principal):
        assert version_id == self.version_id
        return self._validation_run()

    def list_validation_runs(self, version_id, principal):
        assert version_id == self.version_id
        return [self._validation_run()]

    def _dataset(self) -> Dataset:
        return Dataset(
            id=self.dataset_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Transactions",
            slug="fraud-transactions",
            description="Payment events.",
            source_type=DatasetSourceType.UPLOAD,
            status=DatasetStatus.ACTIVE,
        )

    def _version(self, status: DatasetVersionStatus) -> DatasetVersion:
        return DatasetVersion(
            id=self.version_id,
            dataset_id=self.dataset_id,
            version=1,
            object_uri="s3://forgeml/transactions.csv",
            content_hash="sha256:abc123" if status == DatasetVersionStatus.VALIDATED else "",
            row_count=2 if status == DatasetVersionStatus.VALIDATED else 0,
            size_bytes=128 if status == DatasetVersionStatus.VALIDATED else 0,
            status=status,
            created_by=self.user_id,
        )

    def _validation_run(self) -> DatasetValidationRun:
        return DatasetValidationRun(
            id=uuid4(),
            dataset_version_id=self.version_id,
            status=DatasetValidationStatus.COMPLETED,
            report={"field_count": 1, "row_count": 2},
            error_message=None,
        )


def test_dataset_routes_expose_registry_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    version_id = uuid4()
    fake_service = FakeDatasetService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        dataset_id=dataset_id,
        version_id=version_id,
    )
    app = create_app()
    app.dependency_overrides[get_dataset_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "Fraud Transactions", "description": "Payment events."},
    )
    listed = client.get(f"/api/v1/projects/{project_id}/datasets")
    upload = client.post(
        f"/api/v1/datasets/{dataset_id}/versions",
        json={"filename": "transactions.csv", "content_type": "text/csv"},
    )
    finalized = client.post(
        f"/api/v1/dataset-versions/{version_id}/finalize",
        json={
            "content_hash": "sha256:abc123",
            "size_bytes": 128,
            "sample_csv": "amount\n12.5\n",
        },
    )
    schema = client.get(f"/api/v1/dataset-versions/{version_id}/schema")
    validation = client.post(f"/api/v1/dataset-versions/{version_id}/validate")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-transactions"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(dataset_id)
    assert upload.status_code == 201
    assert upload.json()["upload"]["object_uri"] == "s3://forgeml/transactions.csv"
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "validated"
    assert schema.status_code == 200
    assert schema.json()["fields"][0]["name"] == "amount"
    assert validation.status_code == 202
    assert validation.json()["status"] == "completed"

