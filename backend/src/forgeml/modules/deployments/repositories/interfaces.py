from typing import Protocol
from uuid import UUID

from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentRevision,
    ModelVersionDeploymentReference,
)


class DeploymentRepository(Protocol):
    def add_deployment(self, deployment: Deployment) -> Deployment:
        raise NotImplementedError

    def get_deployment(self, deployment_id: UUID) -> Deployment | None:
        raise NotImplementedError

    def list_deployments(self, organization_id: UUID, project_id: UUID) -> list[Deployment]:
        raise NotImplementedError

    def deployment_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        raise NotImplementedError

    def get_model_version_reference(
        self,
        model_version_id: UUID,
    ) -> ModelVersionDeploymentReference | None:
        raise NotImplementedError

    def latest_revision_number(self, deployment_id: UUID) -> int:
        raise NotImplementedError

    def add_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        raise NotImplementedError

    def get_revision(self, revision_id: UUID) -> DeploymentRevision | None:
        raise NotImplementedError

    def list_revisions(self, deployment_id: UUID) -> list[DeploymentRevision]:
        raise NotImplementedError

    def get_active_revision(self, deployment_id: UUID) -> DeploymentRevision | None:
        raise NotImplementedError

    def update_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        raise NotImplementedError

    def add_health_check(self, health_check: DeploymentHealthCheck) -> DeploymentHealthCheck:
        raise NotImplementedError

    def list_health_checks(self, revision_id: UUID) -> list[DeploymentHealthCheck]:
        raise NotImplementedError

    def add_event(self, event: DeploymentEvent) -> DeploymentEvent:
        raise NotImplementedError

    def list_events(self, deployment_id: UUID) -> list[DeploymentEvent]:
        raise NotImplementedError


class DeploymentOrchestrator(Protocol):
    def deploy_revision(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        raise NotImplementedError

    def update_traffic(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        raise NotImplementedError

    def rollback(
        self,
        deployment: Deployment,
        target_revision: DeploymentRevision,
        previous_revision: DeploymentRevision | None,
    ) -> str:
        raise NotImplementedError
