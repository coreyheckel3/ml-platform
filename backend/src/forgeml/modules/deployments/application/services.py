import hashlib
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.administration.application.audit import record_user_audit_event
from forgeml.modules.administration.repositories.interfaces import AuditEventRecorder
from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentCanarySimulation,
    DeploymentCanarySimulationAllocation,
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
    validate_canary_request_count,
    validate_deployable_model_version,
    validate_deployment_name,
    validate_health_check,
    validate_rollback_target,
    validate_runtime_config,
    validate_serving_image,
    validate_traffic_percentage,
    validate_traffic_target_status,
)
from forgeml.modules.deployments.repositories.interfaces import (
    DeploymentOrchestrator,
    DeploymentRepository,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    DomainValidationError,
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


@dataclass(frozen=True)
class ProbeDeploymentRevisionCommand:
    revision_id: UUID


@dataclass(frozen=True)
class SimulateCanaryTrafficCommand:
    deployment_id: UUID
    canary_revision_id: UUID
    request_count: int
    canary_percentage: int | None = None
    routing_seed: str = "forgeml-canary-simulation"


class DeploymentService:
    def __init__(
        self,
        *,
        repository: DeploymentRepository,
        orchestrator: DeploymentOrchestrator,
        audit_log: AuditEventRecorder | None = None,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator
        self._audit_log = audit_log

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
        record_user_audit_event(
            self._audit_log,
            organization_id=deployment.organization_id,
            actor_id=command.created_by,
            action="deployments.rollout",
            resource_type="deployment_revision",
            resource_id=saved.id,
            metadata={
                "deployment_id": str(deployment.id),
                "project_id": str(deployment.project_id),
                "environment": deployment.environment.value,
                "revision": saved.revision,
                "model_version_id": str(saved.model_version_id),
                "traffic_percentage": saved.traffic_percentage,
                "orchestrator_deployment_id": saved.orchestrator_deployment_id,
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
        if command.traffic_percentage > 0:
            validate_traffic_target_status(revision.status)
        planned_revisions = self._build_traffic_plan(
            deployment=deployment,
            target=revision,
            traffic_percentage=command.traffic_percentage,
        )
        saved_revisions = self._apply_traffic_plan(deployment, planned_revisions)
        saved = _find_revision(saved_revisions, revision.id)
        self._record_event(
            deployment.id,
            saved.id,
            "traffic_updated",
            "Deployment traffic allocation was updated.",
            {
                "traffic_percentage": saved.traffic_percentage,
                "traffic_plan": _traffic_plan_payload(saved_revisions),
            },
        )
        record_user_audit_event(
            self._audit_log,
            organization_id=deployment.organization_id,
            actor_id=principal.user_id,
            action="deployments.update_traffic",
            resource_type="deployment_revision",
            resource_id=saved.id,
            metadata={
                "deployment_id": str(deployment.id),
                "project_id": str(deployment.project_id),
                "environment": deployment.environment.value,
                "revision": saved.revision,
                "previous_traffic_percentage": revision.traffic_percentage,
                "traffic_percentage": saved.traffic_percentage,
                "traffic_plan": _traffic_plan_payload(saved_revisions),
            },
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
        active_revisions = [
            revision
            for revision in self._repository.list_revisions(deployment.id)
            if revision.traffic_percentage > 0 and revision.id != target.id
        ]
        previous = max(active_revisions, key=lambda revision: revision.revision, default=None)
        updated_target = replace(
            target,
            traffic_percentage=100,
            status=DeploymentRevisionStatus.HEALTHY,
        )
        self._orchestrator.rollback(deployment, updated_target, previous)
        for active_revision in active_revisions:
            drained = replace(
                active_revision,
                traffic_percentage=0,
                status=DeploymentRevisionStatus.ROLLED_BACK,
            )
            self._orchestrator.update_traffic(deployment, drained)
            self._repository.update_revision(drained)
        saved = self._repository.update_revision(updated_target)
        self._record_event(
            deployment.id,
            saved.id,
            "rollback",
            "Deployment was rolled back to a healthy revision.",
            {
                "target_revision": saved.revision,
                "previous_revision_id": str(previous.id) if previous else None,
                "drained_revision_ids": [str(revision.id) for revision in active_revisions],
            },
        )
        record_user_audit_event(
            self._audit_log,
            organization_id=deployment.organization_id,
            actor_id=principal.user_id,
            action="deployments.rollback",
            resource_type="deployment",
            resource_id=deployment.id,
            metadata={
                "project_id": str(deployment.project_id),
                "environment": deployment.environment.value,
                "target_revision_id": str(saved.id),
                "target_revision": saved.revision,
                "previous_revision_id": str(previous.id) if previous else None,
                "drained_revision_ids": [str(revision.id) for revision in active_revisions],
            },
        )
        return saved

    def probe_revision_health(
        self,
        command: ProbeDeploymentRevisionCommand,
        principal: Principal,
    ) -> DeploymentHealthCheck:
        self._require(principal, "deployment_health:write")
        revision = self._get_scoped_revision(command.revision_id, principal)
        deployment = self._get_scoped_deployment(revision.deployment_id, principal)
        probe = self._orchestrator.probe_revision(deployment, revision)
        health_check = self.record_health(
            RecordDeploymentHealthCommand(
                revision_id=revision.id,
                status=_health_status_from_probe(probe.status),
                latency_ms=probe.latency_ms,
                error_rate=probe.error_rate,
                details={
                    **probe.details,
                    "probe_observed_at": probe.observed_at.isoformat(),
                },
            ),
            principal,
        )
        self._record_event(
            deployment.id,
            revision.id,
            "health_probed",
            f"Deployment revision probe reported {health_check.status.value}.",
            {
                "latency_ms": health_check.latency_ms,
                "error_rate": health_check.error_rate,
            },
        )
        return health_check

    def simulate_canary_traffic(
        self,
        command: SimulateCanaryTrafficCommand,
        principal: Principal,
    ) -> DeploymentCanarySimulation:
        self._require(principal, "deployments:read")
        deployment = self._get_scoped_deployment(command.deployment_id, principal)
        canary = self._repository.get_revision(command.canary_revision_id)
        if canary is None or canary.deployment_id != deployment.id:
            raise ResourceNotFoundError("Canary revision was not found.")
        validate_canary_request_count(command.request_count)
        canary_percentage = (
            canary.traffic_percentage
            if command.canary_percentage is None
            else command.canary_percentage
        )
        validate_traffic_percentage(canary_percentage)
        if canary_percentage <= 0 or canary_percentage >= 100:
            raise DomainValidationError(
                "Canary simulation requires a traffic percentage between 1 and 99."
            )
        validate_traffic_target_status(canary.status)
        planned_revisions = self._build_traffic_plan(
            deployment=deployment,
            target=canary,
            traffic_percentage=canary_percentage,
        )
        simulated_counts = _simulate_weighted_traffic(
            planned_revisions,
            request_count=command.request_count,
            routing_seed=command.routing_seed,
        )
        allocations = tuple(
            DeploymentCanarySimulationAllocation(
                deployment_revision_id=revision.id,
                revision=revision.revision,
                traffic_percentage=revision.traffic_percentage,
                simulated_request_count=simulated_counts[revision.id],
            )
            for revision in planned_revisions
        )
        return DeploymentCanarySimulation(
            deployment_id=deployment.id,
            canary_revision_id=canary.id,
            request_count=command.request_count,
            routing_seed=command.routing_seed,
            allocations=allocations,
            metadata={
                "traffic_plan": _traffic_plan_payload(planned_revisions),
                "total_traffic_percentage": sum(
                    revision.traffic_percentage for revision in planned_revisions
                ),
            },
        )

    def list_events(self, deployment_id: UUID, principal: Principal) -> list[DeploymentEvent]:
        self._require(principal, "deployments:read")
        deployment = self._get_scoped_deployment(deployment_id, principal)
        return self._repository.list_events(deployment.id)

    def _build_traffic_plan(
        self,
        *,
        deployment: Deployment,
        target: DeploymentRevision,
        traffic_percentage: int,
    ) -> tuple[DeploymentRevision, ...]:
        revisions = {
            revision.id: revision for revision in self._repository.list_revisions(deployment.id)
        }
        revisions[target.id] = target
        if traffic_percentage == 0:
            return (replace(target, traffic_percentage=0),)
        if traffic_percentage == 100:
            return tuple(
                replace(
                    revision,
                    traffic_percentage=100 if revision.id == target.id else 0,
                )
                for revision in sorted(revisions.values(), key=lambda revision: revision.revision)
                if revision.id == target.id or revision.traffic_percentage > 0
            )

        baseline = self._select_canary_baseline(
            target=target,
            revisions=tuple(revisions.values()),
        )
        planned: list[DeploymentRevision] = [
            replace(target, traffic_percentage=traffic_percentage),
            replace(baseline, traffic_percentage=100 - traffic_percentage),
        ]
        planned.extend(
            replace(revision, traffic_percentage=0)
            for revision in revisions.values()
            if revision.id not in {target.id, baseline.id}
            and revision.traffic_percentage > 0
        )
        return tuple(sorted(planned, key=lambda revision: revision.revision))

    def _select_canary_baseline(
        self,
        *,
        target: DeploymentRevision,
        revisions: tuple[DeploymentRevision, ...],
    ) -> DeploymentRevision:
        candidates = [
            revision
            for revision in revisions
            if revision.id != target.id
            and revision.traffic_percentage > 0
            and revision.status in {
                DeploymentRevisionStatus.HEALTHY,
                DeploymentRevisionStatus.DEGRADED,
            }
        ]
        if not candidates:
            raise ConflictError(
                "Canary traffic requires an existing healthy baseline revision with active traffic."
            )
        return max(
            candidates,
            key=lambda revision: (revision.traffic_percentage, revision.revision),
        )

    def _apply_traffic_plan(
        self,
        deployment: Deployment,
        revisions: tuple[DeploymentRevision, ...],
    ) -> tuple[DeploymentRevision, ...]:
        saved: list[DeploymentRevision] = []
        for revision in revisions:
            self._orchestrator.update_traffic(deployment, revision)
            saved.append(self._repository.update_revision(revision))
        return tuple(saved)

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


def _health_status_from_probe(status: str) -> DeploymentHealthStatus:
    try:
        return DeploymentHealthStatus(status)
    except ValueError:
        return DeploymentHealthStatus.UNHEALTHY


def _traffic_plan_payload(revisions: tuple[DeploymentRevision, ...]) -> list[dict[str, object]]:
    return [
        {
            "deployment_revision_id": str(revision.id),
            "revision": revision.revision,
            "traffic_percentage": revision.traffic_percentage,
            "status": revision.status.value,
        }
        for revision in revisions
    ]


def _find_revision(
    revisions: tuple[DeploymentRevision, ...],
    revision_id: UUID,
) -> DeploymentRevision:
    for revision in revisions:
        if revision.id == revision_id:
            return revision
    raise RuntimeError("Traffic plan did not include the target revision.")


def _simulate_weighted_traffic(
    revisions: tuple[DeploymentRevision, ...],
    *,
    request_count: int,
    routing_seed: str,
) -> dict[UUID, int]:
    active_revisions = [revision for revision in revisions if revision.traffic_percentage > 0]
    total_weight = sum(revision.traffic_percentage for revision in active_revisions)
    if total_weight <= 0:
        raise DomainValidationError("Canary simulation requires positive traffic allocations.")
    counts = {revision.id: 0 for revision in revisions}
    for index in range(request_count):
        digest = hashlib.sha256(f"{routing_seed}:{index}".encode()).hexdigest()
        bucket = int(digest[:8], 16) % total_weight
        cursor = 0
        for revision in active_revisions:
            cursor += revision.traffic_percentage
            if bucket < cursor:
                counts[revision.id] += 1
                break
    return counts
