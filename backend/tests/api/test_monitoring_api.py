from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.monitoring.api.routes import get_monitoring_service
from forgeml.modules.monitoring.domain.entities import (
    InferenceEndpointMonitoringSummary,
    ProjectMonitoringSummary,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeMonitoringService:
    project_id: UUID
    endpoint_id: UUID
    deployment_id: UUID
    revision_id: UUID

    def get_project_summary(self, project_id, principal):
        assert project_id == self.project_id
        return ProjectMonitoringSummary(
            project_id=self.project_id,
            inference_endpoint_count=1,
            prediction_count=1200,
            error_count=3,
            request_count=12,
            active_alert_count=1,
            error_rate=0.0025,
            max_p95_latency_ms=46.8,
        )

    def list_inference_endpoint_summaries(self, project_id, principal):
        assert project_id == self.project_id
        return [
            InferenceEndpointMonitoringSummary(
                endpoint_id=self.endpoint_id,
                endpoint_name="Fraud Risk Online",
                route_path="/inference/fraud-risk-online",
                status="active",
                deployment_id=self.deployment_id,
                deployment_revision_id=self.revision_id,
                latest_window_seconds=300,
                prediction_count=1200,
                error_count=3,
                request_count=12,
                error_rate=0.0025,
                p50_latency_ms=18.2,
                p95_latency_ms=46.8,
            )
        ]


def test_monitoring_routes_expose_project_summary_and_endpoint_summaries() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = FakeMonitoringService(
        project_id=uuid4(),
        endpoint_id=uuid4(),
        deployment_id=uuid4(),
        revision_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_monitoring_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    summary = client.get(f"/api/v1/projects/{service.project_id}/monitoring/summary")
    endpoints = client.get(
        f"/api/v1/projects/{service.project_id}/monitoring/inference-endpoints"
    )

    assert summary.status_code == 200
    assert summary.json()["prediction_count"] == 1200
    assert summary.json()["active_alert_count"] == 1
    assert endpoints.status_code == 200
    assert endpoints.json()["items"][0]["route_path"] == "/inference/fraud-risk-online"
