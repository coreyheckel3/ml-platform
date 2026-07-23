from uuid import UUID, uuid4

import pytest

from forgeml.modules.model_registry.application.services import (
    CreateRegisteredModelCommand,
    ModelRegistryService,
    RegisterModelVersionCommand,
    RequestModelApprovalCommand,
    ReviewModelVersionCommand,
)
from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    ModelVersionStatus,
    RegisteredModel,
    TrainingRunReference,
)
from forgeml.platform.domain.errors import ConflictError, DomainValidationError
from forgeml.platform.security.rbac import Principal


class FakeModelRegistryRepository:
    def __init__(self) -> None:
        self.models: dict[UUID, RegisteredModel] = {}
        self.training_refs: dict[UUID, TrainingRunReference] = {}
        self.versions: dict[UUID, ModelVersion] = {}
        self.approvals: list[ModelApproval] = []
        self.lineage: list[ModelLineage] = []

    def add_registered_model(self, model: RegisteredModel) -> RegisteredModel:
        self.models[model.id] = model
        return model

    def get_registered_model(self, model_id: UUID) -> RegisteredModel | None:
        return self.models.get(model_id)

    def list_registered_models(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[RegisteredModel]:
        return [
            model
            for model in self.models.values()
            if model.organization_id == organization_id and model.project_id == project_id
        ]

    def registered_model_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return any(
            model.organization_id == organization_id
            and model.project_id == project_id
            and model.slug == slug
            for model in self.models.values()
        )

    def get_training_run_reference(self, training_run_id: UUID) -> TrainingRunReference | None:
        return self.training_refs.get(training_run_id)

    def training_run_already_registered(
        self,
        registered_model_id: UUID,
        training_run_id: UUID,
    ) -> bool:
        return any(
            version.registered_model_id == registered_model_id
            and version.training_run_id == training_run_id
            for version in self.versions.values()
        )

    def latest_model_version_number(self, registered_model_id: UUID) -> int:
        return max(
            (
                version.version
                for version in self.versions.values()
                if version.registered_model_id == registered_model_id
            ),
            default=0,
        )

    def add_model_version(self, version: ModelVersion) -> ModelVersion:
        self.versions[version.id] = version
        return version

    def get_model_version(self, version_id: UUID) -> ModelVersion | None:
        return self.versions.get(version_id)

    def list_model_versions(self, registered_model_id: UUID) -> list[ModelVersion]:
        return [
            version
            for version in self.versions.values()
            if version.registered_model_id == registered_model_id
        ]

    def update_model_version(self, version: ModelVersion) -> ModelVersion:
        self.versions[version.id] = version
        return version

    def add_approval(self, approval: ModelApproval) -> ModelApproval:
        self.approvals.append(approval)
        return approval

    def list_approvals(self, model_version_id: UUID) -> list[ModelApproval]:
        return [
            approval for approval in self.approvals if approval.model_version_id == model_version_id
        ]

    def add_lineage(self, lineage: ModelLineage) -> ModelLineage:
        self.lineage.append(lineage)
        return lineage

    def list_lineage(self, model_version_id: UUID) -> list[ModelLineage]:
        return [lineage for lineage in self.lineage if lineage.model_version_id == model_version_id]


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_model_registry_service_registers_version_and_approval_flow() -> None:
    repository = FakeModelRegistryRepository()
    service = ModelRegistryService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    training_run_id = uuid4()
    repository.training_refs[training_run_id] = TrainingRunReference(
        id=training_run_id,
        organization_id=organization_id,
        project_id=project_id,
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=uuid4(),
        status="succeeded",
        artifact_uri="s3://forgeml/training-runs/run-1",
        model_type="xgboost",
        metrics={"auc": 0.94},
    )
    actor = principal(
        organization_id,
        user_id,
        {
            "models:create",
            "models:read",
            "model_versions:create",
            "model_versions:request_approval",
            "model_versions:review",
        },
    )

    model = service.create_registered_model(
        CreateRegisteredModelCommand(
            organization_id=organization_id,
            project_id=project_id,
            owner_user_id=user_id,
            name="Fraud Risk XGB",
            description="Fraud scoring model.",
            task_type="classification",
        ),
        actor,
    )
    version = service.register_model_version(
        RegisterModelVersionCommand(
            registered_model_id=model.id,
            training_run_id=training_run_id,
            model_format="xgboost-booster",
            signature={"inputs": [{"name": "amount"}], "outputs": [{"name": "risk_score"}]},
            created_by=user_id,
        ),
        actor,
    )
    requested = service.request_approval(
        RequestModelApprovalCommand(
            model_version_id=version.id,
            requested_by=user_id,
            comment="Ready for offline review.",
        ),
        actor,
    )
    approved = service.review_model_version(
        ReviewModelVersionCommand(
            model_version_id=version.id,
            reviewer_id=user_id,
            status=ModelApprovalStatus.APPROVED,
            comment="Meets launch gate.",
        ),
        actor,
    )

    assert model.slug == "fraud-risk-xgb"
    assert version.version == 1
    assert version.status == ModelVersionStatus.CANDIDATE
    assert requested.status == ModelApprovalStatus.REQUESTED
    assert approved.status == ModelApprovalStatus.APPROVED
    assert repository.versions[version.id].status == ModelVersionStatus.APPROVED
    assert {lineage.source_type for lineage in repository.lineage} == {
        "dataset_version",
        "experiment_run",
        "feature_set",
        "training_run",
    }


def test_model_registry_service_rejects_duplicate_registered_model_slug() -> None:
    repository = FakeModelRegistryRepository()
    service = ModelRegistryService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"models:create"})
    command = CreateRegisteredModelCommand(
        organization_id=organization_id,
        project_id=project_id,
        owner_user_id=user_id,
        name="Movie Ranker",
        description="",
        task_type="recommendation",
    )

    service.create_registered_model(command, actor)

    with pytest.raises(ConflictError):
        service.create_registered_model(command, actor)


def test_model_registry_service_rejects_failed_training_run_registration() -> None:
    repository = FakeModelRegistryRepository()
    service = ModelRegistryService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    training_run_id = uuid4()
    repository.training_refs[training_run_id] = TrainingRunReference(
        id=training_run_id,
        organization_id=organization_id,
        project_id=project_id,
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=None,
        feature_set_id=uuid4(),
        status="failed",
        artifact_uri="s3://forgeml/training-runs/run-1",
        model_type="xgboost",
        metrics={},
    )
    actor = principal(organization_id, user_id, {"models:create", "model_versions:create"})
    model = service.create_registered_model(
        CreateRegisteredModelCommand(
            organization_id=organization_id,
            project_id=project_id,
            owner_user_id=user_id,
            name="Fraud Risk XGB",
            description="",
            task_type="classification",
        ),
        actor,
    )

    with pytest.raises(DomainValidationError):
        service.register_model_version(
            RegisterModelVersionCommand(
                registered_model_id=model.id,
                training_run_id=training_run_id,
                model_format="xgboost-booster",
                signature={"inputs": [], "outputs": []},
                created_by=user_id,
            ),
            actor,
        )
