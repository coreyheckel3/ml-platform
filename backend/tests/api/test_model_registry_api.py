from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.model_registry.api.routes import get_model_registry_service
from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    ModelVersionStatus,
    RegisteredModel,
    RegisteredModelStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeModelRegistryService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    model_id: UUID
    version_id: UUID
    training_run_id: UUID
    experiment_run_id: UUID

    def create_registered_model(self, command, principal):
        assert command.name == "Fraud Risk XGB"
        return self._model()

    def list_registered_models(self, project_id, principal):
        assert project_id == self.project_id
        return [self._model()]

    def get_registered_model(self, model_id, principal):
        assert model_id == self.model_id
        return self._model()

    def register_model_version(self, command, principal):
        assert command.training_run_id == self.training_run_id
        return self._version(ModelVersionStatus.CANDIDATE)

    def list_model_versions(self, registered_model_id, principal):
        assert registered_model_id == self.model_id
        return [self._version(ModelVersionStatus.CANDIDATE)]

    def get_model_version(self, version_id, principal):
        assert version_id == self.version_id
        return self._version(ModelVersionStatus.CANDIDATE)

    def request_approval(self, command, principal):
        assert command.model_version_id == self.version_id
        return self._approval(ModelApprovalStatus.REQUESTED, reviewer_id=None)

    def review_model_version(self, command, principal):
        assert command.status == ModelApprovalStatus.APPROVED
        return self._approval(ModelApprovalStatus.APPROVED, reviewer_id=self.user_id)

    def list_approvals(self, model_version_id, principal):
        assert model_version_id == self.version_id
        return [self._approval(ModelApprovalStatus.REQUESTED, reviewer_id=None)]

    def list_lineage(self, model_version_id, principal):
        assert model_version_id == self.version_id
        return [
            ModelLineage(
                id=uuid4(),
                model_version_id=self.version_id,
                source_type="training_run",
                source_id=str(self.training_run_id),
            )
        ]

    def _model(self) -> RegisteredModel:
        return RegisteredModel(
            id=self.model_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Risk XGB",
            slug="fraud-risk-xgb",
            description="Fraud scoring model.",
            task_type="classification",
            owner_user_id=self.user_id,
            status=RegisteredModelStatus.ACTIVE,
        )

    def _version(self, status: ModelVersionStatus) -> ModelVersion:
        return ModelVersion(
            id=self.version_id,
            registered_model_id=self.model_id,
            version=1,
            training_run_id=self.training_run_id,
            experiment_run_id=self.experiment_run_id,
            artifact_uri="s3://forgeml/training-runs/run-1",
            model_format="xgboost-booster",
            signature={"inputs": [{"name": "amount"}], "outputs": [{"name": "risk_score"}]},
            metrics={"auc": 0.94},
            status=status,
            created_by=self.user_id,
        )

    def _approval(
        self,
        status: ModelApprovalStatus,
        reviewer_id: UUID | None,
    ) -> ModelApproval:
        return ModelApproval(
            id=uuid4(),
            model_version_id=self.version_id,
            status=status,
            requested_by=self.user_id,
            reviewer_id=reviewer_id,
            comment="Ready for review.",
            policy_snapshot={"requires_signature": True},
        )


def test_model_registry_routes_expose_versioning_approval_and_lineage() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeModelRegistryService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        model_id=uuid4(),
        version_id=uuid4(),
        training_run_id=uuid4(),
        experiment_run_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_model_registry_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/models",
        json={
            "name": "Fraud Risk XGB",
            "description": "Fraud scoring model.",
            "task_type": "classification",
        },
    )
    listed = client.get(f"/api/v1/projects/{project_id}/models")
    version = client.post(
        f"/api/v1/models/{service.model_id}/versions",
        json={
            "training_run_id": str(service.training_run_id),
            "model_format": "xgboost-booster",
            "signature": {
                "inputs": [{"name": "amount"}],
                "outputs": [{"name": "risk_score"}],
            },
        },
    )
    approval = client.post(
        f"/api/v1/model-versions/{service.version_id}/approval-request",
        json={"comment": "Ready for review."},
    )
    review = client.post(
        f"/api/v1/model-versions/{service.version_id}/review",
        json={"status": "approved", "comment": "Meets launch gate."},
    )
    lineage = client.get(f"/api/v1/model-versions/{service.version_id}/lineage")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-risk-xgb"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.model_id)
    assert version.status_code == 201
    assert version.json()["metrics"]["auc"] == 0.94
    assert approval.status_code == 202
    assert approval.json()["status"] == "requested"
    assert review.status_code == 200
    assert review.json()["status"] == "approved"
    assert lineage.status_code == 200
    assert lineage.json()["items"][0]["source_type"] == "training_run"
