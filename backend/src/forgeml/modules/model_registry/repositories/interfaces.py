from typing import Protocol
from uuid import UUID

from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelLineage,
    ModelVersion,
    RegisteredModel,
    TrainingRunReference,
)


class ModelRegistryRepository(Protocol):
    def add_registered_model(self, model: RegisteredModel) -> RegisteredModel:
        raise NotImplementedError

    def get_registered_model(self, model_id: UUID) -> RegisteredModel | None:
        raise NotImplementedError

    def list_registered_models(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[RegisteredModel]:
        raise NotImplementedError

    def registered_model_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        raise NotImplementedError

    def get_training_run_reference(self, training_run_id: UUID) -> TrainingRunReference | None:
        raise NotImplementedError

    def training_run_already_registered(
        self,
        registered_model_id: UUID,
        training_run_id: UUID,
    ) -> bool:
        raise NotImplementedError

    def latest_model_version_number(self, registered_model_id: UUID) -> int:
        raise NotImplementedError

    def add_model_version(self, version: ModelVersion) -> ModelVersion:
        raise NotImplementedError

    def get_model_version(self, version_id: UUID) -> ModelVersion | None:
        raise NotImplementedError

    def list_model_versions(self, registered_model_id: UUID) -> list[ModelVersion]:
        raise NotImplementedError

    def update_model_version(self, version: ModelVersion) -> ModelVersion:
        raise NotImplementedError

    def add_approval(self, approval: ModelApproval) -> ModelApproval:
        raise NotImplementedError

    def list_approvals(self, model_version_id: UUID) -> list[ModelApproval]:
        raise NotImplementedError

    def add_lineage(self, lineage: ModelLineage) -> ModelLineage:
        raise NotImplementedError

    def list_lineage(self, model_version_id: UUID) -> list[ModelLineage]:
        raise NotImplementedError
