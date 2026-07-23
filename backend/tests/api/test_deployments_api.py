from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.deployments.api.routes import get_deployment_service
from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEnvironment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
    DeploymentRevisionStatus,
    DeploymentStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeDeploymentService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    deployment_id: UUID
    revision_id: UUID
    model_version_id: UUID
    event_id: UUID
    health_check_id: UUID

    def create_deployment(self, command, principal):
        assert command.name == "Fraud Risk Production"
        return self._deployment()

    def list_deployments(self, project_id, principal):
        assert project_id == self.project_id
        return [self._deployment()]

    def get_deployment(self, deployment_id, principal):
        assert deployment_id == self.deployment_id
        return self._deployment()

    def create_revision(self, command, principal):
        assert command.model_version_id == self.model_version_id
        return self._revision(DeploymentRevisionStatus.DEPLOYING, traffic_percentage=10)

    def list_revisions(self, deployment_id, principal):
        assert deployment_id == self.deployment_id
        return [self._revision(DeploymentRevisionStatus.HEALTHY, traffic_percentage=100)]

    def update_traffic(self, command, principal):
        assert command.traffic_percentage == 25
        return self._revision(DeploymentRevisionStatus.HEALTHY, traffic_percentage=25)

    def record_health(self, command, principal):
        assert command.status == DeploymentHealthStatus.HEALTHY
        return self._health_check()

    def list_health_checks(self, revision_id, principal):
        assert revision_id == self.revision_id
        return [self._health_check()]

    def rollback_deployment(self, command, principal):
        assert command.target_revision_id == self.revision_id
        return self._revision(DeploymentRevisionStatus.HEALTHY, traffic_percentage=100)

    def list_events(self, deployment_id, principal):
        assert deployment_id == self.deployment_id
        return [
            DeploymentEvent(
                id=self.event_id,
                deployment_id=self.deployment_id,
                deployment_revision_id=self.revision_id,
                event_type="revision_created",
                message="Deployment revision was submitted.",
                metadata={"traffic_percentage": 10},
            )
        ]

    def _deployment(self) -> Deployment:
        return Deployment(
            id=self.deployment_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Risk Production",
            slug="fraud-risk-production",
            description="Production risk scoring endpoint.",
            environment=DeploymentEnvironment.PRODUCTION,
            status=DeploymentStatus.ACTIVE,
            created_by=self.user_id,
        )

    def _revision(
        self,
        status: DeploymentRevisionStatus,
        traffic_percentage: int,
    ) -> DeploymentRevision:
        return DeploymentRevision(
            id=self.revision_id,
            deployment_id=self.deployment_id,
            model_version_id=self.model_version_id,
            revision=1,
            serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
            runtime_config={"replicas": 3},
            traffic_percentage=traffic_percentage,
            status=status,
            orchestrator_deployment_id="local-serving-1",
            created_by=self.user_id,
        )

    def _health_check(self) -> DeploymentHealthCheck:
        return DeploymentHealthCheck(
            id=self.health_check_id,
            deployment_revision_id=self.revision_id,
            status=DeploymentHealthStatus.HEALTHY,
            latency_ms=18.2,
            error_rate=0.001,
            details={"window": "5m"},
        )


def test_deployment_routes_expose_rollout_health_and_rollback_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeDeploymentService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        deployment_id=uuid4(),
        revision_id=uuid4(),
        model_version_id=uuid4(),
        event_id=uuid4(),
        health_check_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_deployment_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/deployments",
        json={
            "name": "Fraud Risk Production",
            "description": "Production risk scoring endpoint.",
            "environment": "production",
        },
    )
    listed = client.get(f"/api/v1/projects/{project_id}/deployments")
    revision = client.post(
        f"/api/v1/deployments/{service.deployment_id}/revisions",
        json={
            "model_version_id": str(service.model_version_id),
            "serving_image": "ghcr.io/forgeml/serving/xgboost:1.0.0",
            "runtime_config": {"replicas": 3},
            "traffic_percentage": 10,
        },
    )
    health = client.post(
        f"/api/v1/deployment-revisions/{service.revision_id}/health-checks",
        json={
            "status": "healthy",
            "latency_ms": 18.2,
            "error_rate": 0.001,
            "details": {"window": "5m"},
        },
    )
    traffic = client.post(
        f"/api/v1/deployment-revisions/{service.revision_id}/traffic",
        json={"traffic_percentage": 25},
    )
    rollback = client.post(
        f"/api/v1/deployments/{service.deployment_id}/rollback",
        json={"target_revision_id": str(service.revision_id)},
    )
    events = client.get(f"/api/v1/deployments/{service.deployment_id}/events")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-risk-production"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.deployment_id)
    assert revision.status_code == 202
    assert revision.json()["traffic_percentage"] == 10
    assert health.status_code == 201
    assert health.json()["status"] == "healthy"
    assert traffic.status_code == 200
    assert traffic.json()["traffic_percentage"] == 25
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "healthy"
    assert events.status_code == 200
    assert events.json()["items"][0]["event_type"] == "revision_created"
