from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    ModelVersionStatus,
    RegisteredModel,
    RegisteredModelStatus,
    TrainingRunPromotionCandidate,
    TrainingRunReference,
)
from forgeml.modules.model_registry.domain.policies import (
    build_registered_model_slug,
    model_artifact_uri_from_training_execution,
    normalize_model_format,
    normalize_task_type,
    validate_approval_decision,
    validate_approval_request,
    validate_model_signature,
    validate_registered_model_name,
    validate_reviewable_status,
    validate_training_run_promotion_candidate,
    validate_training_run_reference,
)
from forgeml.modules.model_registry.repositories.interfaces import ModelRegistryRepository
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.observability.metrics import model_promotions_total
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateRegisteredModelCommand:
    organization_id: UUID
    project_id: UUID
    owner_user_id: UUID
    name: str
    description: str
    task_type: str


@dataclass(frozen=True)
class RegisterModelVersionCommand:
    registered_model_id: UUID
    training_run_id: UUID
    model_format: str
    signature: dict[str, object]
    created_by: UUID


@dataclass(frozen=True)
class PromoteTrainingRunCommand:
    registered_model_id: UUID
    training_run_id: UUID
    model_format: str
    signature: dict[str, object]
    promoted_by: UUID


@dataclass(frozen=True)
class RequestModelApprovalCommand:
    model_version_id: UUID
    requested_by: UUID
    comment: str


@dataclass(frozen=True)
class ReviewModelVersionCommand:
    model_version_id: UUID
    reviewer_id: UUID
    status: ModelApprovalStatus
    comment: str


class ModelRegistryService:
    def __init__(self, *, repository: ModelRegistryRepository) -> None:
        self._repository = repository

    def create_registered_model(
        self,
        command: CreateRegisteredModelCommand,
        principal: Principal,
    ) -> RegisteredModel:
        self._require(principal, "models:create")
        self._require_same_organization(command.organization_id, principal)
        validate_registered_model_name(command.name)
        task_type = normalize_task_type(command.task_type)
        slug = build_registered_model_slug(command.name)
        if self._repository.registered_model_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("A registered model with this name already exists in the project.")

        model = RegisteredModel(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            task_type=task_type,
            owner_user_id=command.owner_user_id,
            status=RegisteredModelStatus.ACTIVE,
        )
        return self._repository.add_registered_model(model)

    def list_registered_models(
        self,
        project_id: UUID,
        principal: Principal,
    ) -> list[RegisteredModel]:
        self._require(principal, "models:read")
        return self._repository.list_registered_models(UUID(principal.organization_id), project_id)

    def get_registered_model(self, model_id: UUID, principal: Principal) -> RegisteredModel:
        self._require(principal, "models:read")
        return self._get_scoped_model(model_id, principal)

    def register_model_version(
        self,
        command: RegisterModelVersionCommand,
        principal: Principal,
    ) -> ModelVersion:
        self._require(principal, "model_versions:create")
        model = self._get_scoped_model(command.registered_model_id, principal)
        training_run = self._repository.get_training_run_reference(command.training_run_id)
        if training_run is None or training_run.organization_id != model.organization_id:
            raise ResourceNotFoundError("Training run was not found.")
        if training_run.project_id != model.project_id:
            raise ResourceNotFoundError("Training run was not found.")
        validate_training_run_reference(training_run)
        validate_model_signature(command.signature)
        model_format = normalize_model_format(command.model_format)
        if self._repository.training_run_already_registered(model.id, training_run.id):
            raise ConflictError("This training run is already registered for the model.")

        return self._create_model_version(
            model=model,
            training_run=training_run,
            model_format=model_format,
            signature=command.signature,
            artifact_uri=training_run.artifact_uri,
            created_by=command.created_by,
        )

    def promote_training_run_to_model_version(
        self,
        command: PromoteTrainingRunCommand,
        principal: Principal,
    ) -> ModelVersion:
        self._require(principal, "model_versions:create")
        model = self._get_scoped_model(command.registered_model_id, principal)
        candidate = self._repository.get_training_run_promotion_candidate(command.training_run_id)
        if candidate is None or candidate.organization_id != model.organization_id:
            raise ResourceNotFoundError("Training run was not found.")
        if candidate.project_id != model.project_id:
            raise ResourceNotFoundError("Training run was not found.")

        validate_training_run_promotion_candidate(candidate)
        validate_model_signature(command.signature)
        model_format = normalize_model_format(command.model_format)
        existing = self._repository.get_model_version_by_training_run(model.id, candidate.id)
        if existing is not None:
            model_promotions_total.labels(status="idempotent").inc()
            return existing

        version = self._create_model_version(
            model=model,
            training_run=candidate,
            model_format=model_format,
            signature=command.signature,
            artifact_uri=model_artifact_uri_from_training_execution(candidate),
            created_by=command.promoted_by,
        )
        model_promotions_total.labels(status="succeeded").inc()
        return version

    def _create_model_version(
        self,
        *,
        model: RegisteredModel,
        training_run: TrainingRunReference | TrainingRunPromotionCandidate,
        model_format: str,
        signature: dict[str, object],
        artifact_uri: str,
        created_by: UUID,
    ) -> ModelVersion:
        version_number = self._repository.latest_model_version_number(model.id) + 1
        version = ModelVersion(
            id=uuid4(),
            registered_model_id=model.id,
            version=version_number,
            training_run_id=training_run.id,
            experiment_run_id=training_run.experiment_run_id,
            artifact_uri=artifact_uri,
            model_format=model_format,
            signature=signature,
            metrics=training_run.metrics,
            status=ModelVersionStatus.CANDIDATE,
            created_by=created_by,
        )
        saved = self._repository.add_model_version(version)
        self._record_training_lineage(saved, training_run)
        return saved

    def list_model_versions(
        self,
        registered_model_id: UUID,
        principal: Principal,
    ) -> list[ModelVersion]:
        self._require(principal, "models:read")
        model = self._get_scoped_model(registered_model_id, principal)
        return self._repository.list_model_versions(model.id)

    def get_model_version(self, version_id: UUID, principal: Principal) -> ModelVersion:
        self._require(principal, "models:read")
        return self._get_scoped_version(version_id, principal)

    def request_approval(
        self,
        command: RequestModelApprovalCommand,
        principal: Principal,
    ) -> ModelApproval:
        self._require(principal, "model_versions:request_approval")
        version = self._get_scoped_version(command.model_version_id, principal)
        validate_approval_request(version.status)
        updated = replace(version, status=ModelVersionStatus.PENDING_APPROVAL)
        self._repository.update_model_version(updated)
        approval = ModelApproval(
            id=uuid4(),
            model_version_id=version.id,
            status=ModelApprovalStatus.REQUESTED,
            requested_by=command.requested_by,
            reviewer_id=None,
            comment=command.comment.strip(),
            policy_snapshot={
                "requires_completed_training_run": True,
                "requires_signature": True,
                "requires_reviewer": True,
            },
        )
        return self._repository.add_approval(approval)

    def review_model_version(
        self,
        command: ReviewModelVersionCommand,
        principal: Principal,
    ) -> ModelApproval:
        self._require(principal, "model_versions:review")
        version = self._get_scoped_version(command.model_version_id, principal)
        validate_approval_decision(command.status)
        validate_reviewable_status(version.status)
        updated = replace(
            version,
            status=(
                ModelVersionStatus.APPROVED
                if command.status == ModelApprovalStatus.APPROVED
                else ModelVersionStatus.REJECTED
            ),
        )
        self._repository.update_model_version(updated)
        approval = ModelApproval(
            id=uuid4(),
            model_version_id=version.id,
            status=command.status,
            requested_by=version.created_by,
            reviewer_id=command.reviewer_id,
            comment=command.comment.strip(),
            policy_snapshot={
                "reviewed_after_request": True,
                "decision": command.status.value,
            },
        )
        return self._repository.add_approval(approval)

    def list_approvals(
        self,
        model_version_id: UUID,
        principal: Principal,
    ) -> list[ModelApproval]:
        self._require(principal, "models:read")
        version = self._get_scoped_version(model_version_id, principal)
        return self._repository.list_approvals(version.id)

    def list_lineage(
        self,
        model_version_id: UUID,
        principal: Principal,
    ) -> list[ModelLineage]:
        self._require(principal, "models:read")
        version = self._get_scoped_version(model_version_id, principal)
        return self._repository.list_lineage(version.id)

    def _get_scoped_model(self, model_id: UUID, principal: Principal) -> RegisteredModel:
        model = self._repository.get_registered_model(model_id)
        if model is None or str(model.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Registered model was not found.")
        return model

    def _get_scoped_version(self, version_id: UUID, principal: Principal) -> ModelVersion:
        version = self._repository.get_model_version(version_id)
        if version is None:
            raise ResourceNotFoundError("Model version was not found.")
        self._get_scoped_model(version.registered_model_id, principal)
        return version

    def _record_training_lineage(
        self,
        version: ModelVersion,
        training_run,
    ) -> None:
        sources = [
            ("training_run", str(training_run.id)),
            ("experiment_run", str(training_run.experiment_run_id)),
        ]
        if training_run.dataset_version_id is not None:
            sources.append(("dataset_version", str(training_run.dataset_version_id)))
        if training_run.feature_set_id is not None:
            sources.append(("feature_set", str(training_run.feature_set_id)))
        for source_type, source_id in sources:
            self._repository.add_lineage(
                ModelLineage(
                    id=uuid4(),
                    model_version_id=version.id,
                    source_type=source_type,
                    source_id=source_id,
                )
            )

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage model registry.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage models in another organization.")
