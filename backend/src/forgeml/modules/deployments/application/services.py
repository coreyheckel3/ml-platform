from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
    DeploymentRevisionStatus,
    DeploymentStatus,
)
from forgeml.modules.deployments.domain.policies import (
    build_deployment_slug,
    parse_deployment_environment,
    validate_deployable_model_version,
    validate_deployment_name,
    validate_health_check,
    validate_rollback_target,
    validate_runtime_config,
    validate_serving_image,
    validate_traffic_percentage,
)
from forgeml.modules.deployments.repositories.interfaces import (
    DeploymentOrchestrator,
    DeploymentRepository,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateDeploymentCommand:
    organization_id: UUID
    project_id: UUID
    name: str
    description: str
    environment: str
    created_by: UUID


@dataclass(frozen=True)
class CreateDeploymentRevisionCommand:
    deployment_id: UUID
    model_version_id: UUID
    serving_image: str
    runtime_config: dict[str, object]
    traffic_percentage: int
    created_by: UUID


@dataclass(frozen=True)
class UpdateDeploymentTrafficCommand:
    revision_id: UUID
    traffic_percentage: int


@dataclass(frozen=True)
class RecordDeploymentHealthCommand:
    revision_id: UUID
    status: DeploymentHealthStatus
    latency_ms: float
    error_rate: float
    details: dict[str, object]


@dataclass(frozen=True)
class RollbackDeploymentCommand:
    deployment_id: UUID
    target_revision_id: UUID


class DeploymentService:
    def __init__(
        self,
        *,
        repository: DeploymentRepository,
        orchestrator: DeploymentOrchestrator,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator

    def create_deployment(
        self,
        command: CreateDeploymentCommand,
        principal: Principal,
    ) -> Deployment:
        self._require(principal, "deployments:create")
        self._require_same_organization(command.organization_id, principal)
        validate_deployment_name(command.name)
        environment = parse_deployment_environment(command.environment)
        slug = build_deployment_slug(command.name)
        if self._repository.deployment_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("A deployment with this name already exists in the project.")

        deployment = Deployment(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            environment=environment,
            status=DeploymentStatus.ACTIVE,
            created_by=command.created_by,
        )
        saved = self._repository.add_deployment(deployment)
        self._record_event(saved.id, None, "created", "Deployment target was created.", {})
        return saved

    def list_deployments(self, project_id: UUID, principal: Principal) -> list[Deployment]:
        self._require(principal, "deployments:read")
        return self._repository.list_deployments(UUID(principal.organization_id), project_id)

    def get_deployment(self, deployment_id: UUID, principal: Principal) -> Deployment:
        self._require(principal, "deployments:read")
        return self._get_scoped_deployment(deployment_id, principal)

    def create_revision(
        self,
        command: CreateDeploymentRevisionCommand,
        principal: Principal,
    ) -> DeploymentRevision:
        self._require(principal, "deployment_revisions:create")
        deployment = self._get_scoped_deployment(command.deployment_id, principal)
        model_version = self._repository.get_model_version_reference(command.model_version_id)
        if model_version is None or model_version.organization_id != deployment.organization_id:
            raise ResourceNotFoundError("Model version was not found.")
        if model_version.project_id != deployment.project_id:
            raise ResourceNotFoundError("Model version was not found.")
        validate_deployable_model_version(model_version)
        validate_serving_image(command.serving_image)
        validate_runtime_config(command.runtime_config)
        validate_traffic_percentage(command.traffic_percentage)
        revision_id = uuid4()
        planned = DeploymentRevision(
            id=revision_id,
            deployment_id=deployment.id,
            model_version_id=model_version.id,
            revision=self._repository.latest_revision_number(deployment.id) + 1,
            serving_image=command.serving_image.strip(),
            runtime_config=command.runtime_config,
            traffic_percentage=command.traffic_percentage,
            status=DeploymentRevisionStatus.REQUESTED,
            orchestrator_deployment_id="",
            created_by=command.created_by,
        )
        orchestrator_id = self._orchestrator.deploy_revision(deployment, planned)
        saved = self._repository.add_revision(
            replace(
                planned,
                status=DeploymentRevisionStatus.DEPLOYING,
                orchestrator_deployment_id=orchestrator_id,
            )
        )
        self._record_event(
            deployment.id,
            saved.id,
            "revision_created",
            "Deployment revision was submitted to the serving orchestrator.",
            {
                "model_version_id": str(model_version.id),
                "traffic_percentage": saved.traffic_percentage,
            },
        )
        return saved

    def list_revisions(
        self,
        deployment_id: UUID,
        principal: Principal,
    ) -> list[DeploymentRevision]:
        self._require(principal, "deployments:read")
        deployment = self._get_scoped_deployment(deployment_id, principal)
        return self._repository.list_revisions(deployment.id)

    def update_traffic(
        self,
        command: UpdateDeploymentTrafficCommand,
        principal: Principal,
    ) -> DeploymentRevision:
        self._require(principal, "deployment_revisions:traffic")
        revision = self._get_scoped_revision(command.revision_id, principal)
        deployment = self._get_scoped_deployment(revision.deployment_id, principal)
        validate_traffic_percentage(command.traffic_percentage)
        updated = replace(revision, traffic_percentage=command.traffic_percentage)
        self._orchestrator.update_traffic(deployment, updated)
        saved = self._repository.update_revision(updated)
        self._record_event(
            deployment.id,
            saved.id,
            "traffic_updated",
            "Deployment traffic allocation was updated.",
            {"traffic_percentage": saved.traffic_percentage},
        )
        return saved

    def record_health(
        self,
        command: RecordDeploymentHealthCommand,
        principal: Principal,
    ) -> DeploymentHealthCheck:
        self._require(principal, "deployment_health:write")
        revision = self._get_scoped_revision(command.revision_id, principal)
        validate_health_check(
            status=command.status,
            latency_ms=command.latency_ms,
            error_rate=command.error_rate,
        )
        health_check = DeploymentHealthCheck(
            id=uuid4(),
            deployment_revision_id=revision.id,
            status=command.status,
            latency_ms=float(command.latency_ms),
            error_rate=float(command.error_rate),
            details=command.details,
        )
        saved = self._repository.add_health_check(health_check)
        revision_status = _revision_status_from_health(command.status)
        self._repository.update_revision(replace(revision, status=revision_status))
        self._record_event(
            revision.deployment_id,
            revision.id,
            "health_checked",
            f"Deployment revision health is {command.status.value}.",
            {
                "latency_ms": saved.latency_ms,
                "error_rate": saved.error_rate,
            },
        )
        return saved

    def list_health_checks(
        self,
        revision_id: UUID,
        principal: Principal,
    ) -> list[DeploymentHealthCheck]:
        self._require(principal, "deployments:read")
        revision = self._get_scoped_revision(revision_id, principal)
        return self._repository.list_health_checks(revision.id)

    def rollback_deployment(
        self,
        command: RollbackDeploymentCommand,
        principal: Principal,
    ) -> DeploymentRevision:
        self._require(principal, "deployments:rollback")
        deployment = self._get_scoped_deployment(command.deployment_id, principal)
        target = self._repository.get_revision(command.target_revision_id)
        if target is None or target.deployment_id != deployment.id:
            raise ResourceNotFoundError("Rollback target revision was not found.")
        validate_rollback_target(target.status)
        previous = self._repository.get_active_revision(deployment.id)
        if previous is not None and previous.id != target.id:
            self._repository.update_revision(
                replace(
                    previous,
                    traffic_percentage=0,
                    status=DeploymentRevisionStatus.ROLLED_BACK,
                )
            )
        updated_target = replace(
            target,
            traffic_percentage=100,
            status=DeploymentRevisionStatus.HEALTHY,
        )
        self._orchestrator.rollback(deployment, updated_target, previous)
        saved = self._repository.update_revision(updated_target)
        self._record_event(
            deployment.id,
            saved.id,
            "rollback",
            "Deployment was rolled back to a healthy revision.",
            {
                "target_revision": saved.revision,
                "previous_revision_id": str(previous.id) if previous else None,
            },
        )
        return saved

    def list_events(self, deployment_id: UUID, principal: Principal) -> list[DeploymentEvent]:
        self._require(principal, "deployments:read")
        deployment = self._get_scoped_deployment(deployment_id, principal)
        return self._repository.list_events(deployment.id)

    def _get_scoped_deployment(self, deployment_id: UUID, principal: Principal) -> Deployment:
        deployment = self._repository.get_deployment(deployment_id)
        if deployment is None or str(deployment.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Deployment was not found.")
        return deployment

    def _get_scoped_revision(self, revision_id: UUID, principal: Principal) -> DeploymentRevision:
        revision = self._repository.get_revision(revision_id)
        if revision is None:
            raise ResourceNotFoundError("Deployment revision was not found.")
        self._get_scoped_deployment(revision.deployment_id, principal)
        return revision

    def _record_event(
        self,
        deployment_id: UUID,
        revision_id: UUID | None,
        event_type: str,
        message: str,
        metadata: dict[str, object],
    ) -> DeploymentEvent:
        return self._repository.add_event(
            DeploymentEvent(
                id=uuid4(),
                deployment_id=deployment_id,
                deployment_revision_id=revision_id,
                event_type=event_type,
                message=message,
                metadata=metadata,
            )
        )

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage deployments.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage deployments in another organization.")


def _revision_status_from_health(
    status: DeploymentHealthStatus,
) -> DeploymentRevisionStatus:
    if status == DeploymentHealthStatus.HEALTHY:
        return DeploymentRevisionStatus.HEALTHY
    if status == DeploymentHealthStatus.DEGRADED:
        return DeploymentRevisionStatus.DEGRADED
    return DeploymentRevisionStatus.FAILED
