from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from forgeml.modules.administration.domain.entities import AuditLogEntry, AuditLogEvent
from forgeml.modules.deployments.application.services import (
    CreateDeploymentCommand,
    CreateDeploymentRevisionCommand,
    DeploymentService,
    ProbeDeploymentRevisionCommand,
    RecordDeploymentHealthCommand,
    RollbackDeploymentCommand,
    SimulateCanaryTrafficCommand,
    UpdateDeploymentTrafficCommand,
)
from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEnvironment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
    DeploymentRevisionStatus,
    DeploymentStatus,
    ModelVersionDeploymentReference,
)
from forgeml.platform.domain.errors import ConflictError, DomainValidationError
from forgeml.platform.security.rbac import Principal
from forgeml.platform.serving import ServingHealthProbeResult


class FakeDeploymentRepository:
    def __init__(self) -> None:
        self.deployments: dict[UUID, Deployment] = {}
        self.model_versions: dict[UUID, ModelVersionDeploymentReference] = {}
        self.revisions: dict[UUID, DeploymentRevision] = {}
        self.health_checks: list[DeploymentHealthCheck] = []
        self.events: list[DeploymentEvent] = []

    def add_deployment(self, deployment: Deployment) -> Deployment:
        self.deployments[deployment.id] = deployment
        return deployment

    def get_deployment(self, deployment_id: UUID) -> Deployment | None:
        return self.deployments.get(deployment_id)

    def list_deployments(self, organization_id: UUID, project_id: UUID) -> list[Deployment]:
        return [
            deployment
            for deployment in self.deployments.values()
            if deployment.organization_id == organization_id and deployment.project_id == project_id
        ]

    def deployment_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return any(
            deployment.organization_id == organization_id
            and deployment.project_id == project_id
            and deployment.slug == slug
            for deployment in self.deployments.values()
        )

    def get_model_version_reference(
        self,
        model_version_id: UUID,
    ) -> ModelVersionDeploymentReference | None:
        return self.model_versions.get(model_version_id)

    def latest_revision_number(self, deployment_id: UUID) -> int:
        return max(
            (
                revision.revision
                for revision in self.revisions.values()
                if revision.deployment_id == deployment_id
            ),
            default=0,
        )

    def add_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        self.revisions[revision.id] = revision
        return revision

    def get_revision(self, revision_id: UUID) -> DeploymentRevision | None:
        return self.revisions.get(revision_id)

    def list_revisions(self, deployment_id: UUID) -> list[DeploymentRevision]:
        return [
            revision
            for revision in self.revisions.values()
            if revision.deployment_id == deployment_id
        ]

    def get_active_revision(self, deployment_id: UUID) -> DeploymentRevision | None:
        candidates = [
            revision
            for revision in self.revisions.values()
            if revision.deployment_id == deployment_id and revision.traffic_percentage > 0
        ]
        return max(candidates, key=lambda revision: revision.revision, default=None)

    def update_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        self.revisions[revision.id] = revision
        return revision

    def add_health_check(self, health_check: DeploymentHealthCheck) -> DeploymentHealthCheck:
        self.health_checks.append(health_check)
        return health_check

    def list_health_checks(self, revision_id: UUID) -> list[DeploymentHealthCheck]:
        return [
            health_check
            for health_check in self.health_checks
            if health_check.deployment_revision_id == revision_id
        ]

    def add_event(self, event: DeploymentEvent) -> DeploymentEvent:
        self.events.append(event)
        return event

    def list_events(self, deployment_id: UUID) -> list[DeploymentEvent]:
        return [event for event in self.events if event.deployment_id == deployment_id]


class FakeDeploymentOrchestrator:
    def __init__(self) -> None:
        self.traffic_updates: list[tuple[UUID, UUID, int]] = []
        self.rollbacks: list[tuple[UUID, UUID, UUID | None]] = []
        self.probes: list[UUID] = []

    def deploy_revision(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        return f"serving:{deployment.id}:{revision.id}"

    def update_traffic(self, deployment: Deployment, revision: DeploymentRevision) -> str:
        self.traffic_updates.append((deployment.id, revision.id, revision.traffic_percentage))
        return f"traffic:{deployment.id}:{revision.id}:{revision.traffic_percentage}"

    def rollback(
        self,
        deployment: Deployment,
        target_revision: DeploymentRevision,
        previous_revision: DeploymentRevision | None,
    ) -> str:
        self.rollbacks.append(
            (
                deployment.id,
                target_revision.id,
                previous_revision.id if previous_revision else None,
            )
        )
        previous = str(previous_revision.id) if previous_revision else "none"
        return f"rollback:{deployment.id}:{previous}:{target_revision.id}"

    def probe_revision(
        self,
        deployment: Deployment,
        revision: DeploymentRevision,
    ) -> ServingHealthProbeResult:
        self.probes.append(revision.id)
        return ServingHealthProbeResult(
            deployment_id=deployment.id,
            deployment_revision_id=revision.id,
            status="healthy",
            latency_ms=14.2,
            error_rate=0.001,
            details={"runtime_deployment_id": revision.orchestrator_deployment_id},
            observed_at=datetime.now(UTC),
        )


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.events: list[AuditLogEvent] = []

    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        self.events.append(event)
        return AuditLogEntry(
            id=uuid4(),
            organization_id=event.organization_id,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata=event.metadata,
            created_at=datetime.now(UTC),
        )


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_deployment_service_creates_revision_health_and_rollback() -> None:
    repository = FakeDeploymentRepository()
    audit_log = FakeAuditLogRepository()
    service = DeploymentService(
        repository=repository,
        orchestrator=FakeDeploymentOrchestrator(),
        audit_log=audit_log,
    )
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    model_version_id = uuid4()
    repository.model_versions[model_version_id] = ModelVersionDeploymentReference(
        id=model_version_id,
        registered_model_id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        version=1,
        status="approved",
        artifact_uri="s3://forgeml/models/fraud-risk-xgb/v1",
        model_format="xgboost-booster",
    )
    actor = principal(
        organization_id,
        user_id,
        {
            "deployments:create",
            "deployments:read",
            "deployment_revisions:create",
            "deployment_revisions:traffic",
            "deployment_health:write",
            "deployments:rollback",
        },
    )

    deployment = service.create_deployment(
        CreateDeploymentCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Risk Production",
            description="Production risk scoring endpoint.",
            environment="production",
            created_by=user_id,
        ),
        actor,
    )
    revision = service.create_revision(
        CreateDeploymentRevisionCommand(
            deployment_id=deployment.id,
            model_version_id=model_version_id,
            serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
            runtime_config={"replicas": 3},
            traffic_percentage=10,
            created_by=user_id,
        ),
        actor,
    )
    healthy = service.record_health(
        RecordDeploymentHealthCommand(
            revision_id=revision.id,
            status=DeploymentHealthStatus.HEALTHY,
            latency_ms=18.2,
            error_rate=0.001,
            details={"window": "5m"},
        ),
        actor,
    )
    full_traffic = service.update_traffic(
        UpdateDeploymentTrafficCommand(revision_id=revision.id, traffic_percentage=100),
        actor,
    )
    rollback_target = service.rollback_deployment(
        RollbackDeploymentCommand(
            deployment_id=deployment.id,
            target_revision_id=revision.id,
        ),
        actor,
    )

    assert deployment.slug == "fraud-risk-production"
    assert revision.status == DeploymentRevisionStatus.DEPLOYING
    assert revision.orchestrator_deployment_id.startswith("serving:")
    assert healthy.status == DeploymentHealthStatus.HEALTHY
    assert full_traffic.traffic_percentage == 100
    assert rollback_target.status == DeploymentRevisionStatus.HEALTHY
    assert {event.event_type for event in repository.events} >= {
        "created",
        "revision_created",
        "health_checked",
        "traffic_updated",
        "rollback",
    }
    assert [event.action for event in audit_log.events] == [
        "deployments.rollout",
        "deployments.update_traffic",
        "deployments.rollback",
    ]
    assert audit_log.events[0].resource_id == str(revision.id)
    assert audit_log.events[0].metadata["traffic_percentage"] == 10
    assert audit_log.events[-1].resource_id == str(deployment.id)
    assert audit_log.events[-1].metadata["target_revision_id"] == str(revision.id)


def test_deployment_service_plans_canary_traffic_and_simulates_routing() -> None:
    repository = FakeDeploymentRepository()
    orchestrator = FakeDeploymentOrchestrator()
    service = DeploymentService(repository=repository, orchestrator=orchestrator)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    model_version_id = uuid4()
    deployment = _deployment(organization_id, project_id, user_id)
    repository.deployments[deployment.id] = deployment
    baseline = _revision(
        deployment.id,
        model_version_id,
        revision=1,
        status=DeploymentRevisionStatus.HEALTHY,
        traffic_percentage=100,
    )
    canary = _revision(
        deployment.id,
        model_version_id,
        revision=2,
        status=DeploymentRevisionStatus.HEALTHY,
        traffic_percentage=0,
    )
    repository.revisions[baseline.id] = baseline
    repository.revisions[canary.id] = canary
    actor = principal(
        organization_id,
        user_id,
        {"deployment_revisions:traffic", "deployments:read"},
    )

    updated_canary = service.update_traffic(
        UpdateDeploymentTrafficCommand(revision_id=canary.id, traffic_percentage=10),
        actor,
    )
    simulation = service.simulate_canary_traffic(
        SimulateCanaryTrafficCommand(
            deployment_id=deployment.id,
            canary_revision_id=canary.id,
            request_count=1000,
            routing_seed="fixed-seed",
        ),
        actor,
    )

    assert updated_canary.traffic_percentage == 10
    assert repository.revisions[baseline.id].traffic_percentage == 90
    assert repository.revisions[canary.id].traffic_percentage == 10
    assert sorted(traffic for _, _, traffic in orchestrator.traffic_updates) == [10, 90]
    assert sum(allocation.simulated_request_count for allocation in simulation.allocations) == 1000
    assert {allocation.traffic_percentage for allocation in simulation.allocations} == {10, 90}


def test_deployment_service_probe_records_runtime_health_check() -> None:
    repository = FakeDeploymentRepository()
    orchestrator = FakeDeploymentOrchestrator()
    service = DeploymentService(repository=repository, orchestrator=orchestrator)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    model_version_id = uuid4()
    deployment = _deployment(organization_id, project_id, user_id)
    revision = _revision(
        deployment.id,
        model_version_id,
        revision=1,
        status=DeploymentRevisionStatus.DEPLOYING,
        traffic_percentage=10,
    )
    repository.deployments[deployment.id] = deployment
    repository.revisions[revision.id] = revision
    actor = principal(organization_id, user_id, {"deployment_health:write"})

    health_check = service.probe_revision_health(
        ProbeDeploymentRevisionCommand(revision_id=revision.id),
        actor,
    )

    assert health_check.status == DeploymentHealthStatus.HEALTHY
    assert health_check.latency_ms == 14.2
    assert health_check.details["runtime_deployment_id"] == revision.orchestrator_deployment_id
    assert repository.revisions[revision.id].status == DeploymentRevisionStatus.HEALTHY
    assert orchestrator.probes == [revision.id]
    assert {event.event_type for event in repository.events} >= {
        "health_checked",
        "health_probed",
    }


def test_deployment_service_rollback_drains_all_active_non_target_revisions() -> None:
    repository = FakeDeploymentRepository()
    orchestrator = FakeDeploymentOrchestrator()
    service = DeploymentService(repository=repository, orchestrator=orchestrator)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    model_version_id = uuid4()
    deployment = _deployment(organization_id, project_id, user_id)
    target = _revision(
        deployment.id,
        model_version_id,
        revision=1,
        status=DeploymentRevisionStatus.HEALTHY,
        traffic_percentage=0,
    )
    active = _revision(
        deployment.id,
        model_version_id,
        revision=2,
        status=DeploymentRevisionStatus.HEALTHY,
        traffic_percentage=90,
    )
    canary = _revision(
        deployment.id,
        model_version_id,
        revision=3,
        status=DeploymentRevisionStatus.DEGRADED,
        traffic_percentage=10,
    )
    repository.deployments[deployment.id] = deployment
    for revision in (target, active, canary):
        repository.revisions[revision.id] = revision
    actor = principal(organization_id, user_id, {"deployments:rollback"})

    rolled_back = service.rollback_deployment(
        RollbackDeploymentCommand(
            deployment_id=deployment.id,
            target_revision_id=target.id,
        ),
        actor,
    )

    assert rolled_back.traffic_percentage == 100
    assert repository.revisions[active.id].traffic_percentage == 0
    assert repository.revisions[canary.id].traffic_percentage == 0
    assert repository.revisions[active.id].status == DeploymentRevisionStatus.ROLLED_BACK
    assert repository.revisions[canary.id].status == DeploymentRevisionStatus.ROLLED_BACK
    assert orchestrator.rollbacks == [(deployment.id, target.id, canary.id)]
    assert sorted(update[2] for update in orchestrator.traffic_updates) == [0, 0]


def test_deployment_service_rejects_duplicate_deployment_slug() -> None:
    repository = FakeDeploymentRepository()
    service = DeploymentService(
        repository=repository,
        orchestrator=FakeDeploymentOrchestrator(),
    )
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"deployments:create"})
    command = CreateDeploymentCommand(
        organization_id=organization_id,
        project_id=project_id,
        name="Movie Ranker Production",
        description="",
        environment="production",
        created_by=user_id,
    )

    service.create_deployment(command, actor)

    with pytest.raises(ConflictError):
        service.create_deployment(command, actor)


def test_deployment_service_rejects_unapproved_model_version() -> None:
    repository = FakeDeploymentRepository()
    service = DeploymentService(
        repository=repository,
        orchestrator=FakeDeploymentOrchestrator(),
    )
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    model_version_id = uuid4()
    repository.model_versions[model_version_id] = ModelVersionDeploymentReference(
        id=model_version_id,
        registered_model_id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        version=1,
        status="candidate",
        artifact_uri="s3://forgeml/models/fraud-risk-xgb/v1",
        model_format="xgboost-booster",
    )
    actor = principal(
        organization_id,
        user_id,
        {"deployments:create", "deployment_revisions:create"},
    )
    deployment = service.create_deployment(
        CreateDeploymentCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Risk Production",
            description="",
            environment="production",
            created_by=user_id,
        ),
        actor,
    )

    with pytest.raises(DomainValidationError):
        service.create_revision(
            CreateDeploymentRevisionCommand(
                deployment_id=deployment.id,
                model_version_id=model_version_id,
                serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
                runtime_config={},
                traffic_percentage=10,
                created_by=user_id,
            ),
            actor,
        )


def _deployment(organization_id: UUID, project_id: UUID, user_id: UUID) -> Deployment:
    return Deployment(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name="Fraud Risk Production",
        slug="fraud-risk-production",
        description="Production risk scoring endpoint.",
        environment=DeploymentEnvironment.PRODUCTION,
        status=DeploymentStatus.ACTIVE,
        created_by=user_id,
    )


def _revision(
    deployment_id: UUID,
    model_version_id: UUID,
    *,
    revision: int,
    status: DeploymentRevisionStatus,
    traffic_percentage: int,
) -> DeploymentRevision:
    return DeploymentRevision(
        id=uuid4(),
        deployment_id=deployment_id,
        model_version_id=model_version_id,
        revision=revision,
        serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
        runtime_config={"replicas": 3},
        traffic_percentage=traffic_percentage,
        status=status,
        orchestrator_deployment_id=f"serving-{revision}",
        created_by=uuid4(),
    )
