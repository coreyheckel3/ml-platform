from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.inference.api.routes import get_inference_service
from forgeml.modules.inference.domain.entities import (
    InferenceEndpoint,
    InferenceEndpointStatus,
    InferenceMetricSnapshot,
    InferencePrediction,
    InferenceRequestLog,
    InferenceRequestStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeInferenceService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    deployment_id: UUID
    revision_id: UUID
    endpoint_id: UUID
    log_id: UUID
    snapshot_id: UUID

    def create_endpoint(self, command, principal):
        assert command.name == "Fraud Risk Online"
        assert command.deployment_id == self.deployment_id
        return self._endpoint()

    def list_endpoints(self, project_id, principal):
        assert project_id == self.project_id
        return [self._endpoint()]

    def get_endpoint(self, endpoint_id, principal):
        assert endpoint_id == self.endpoint_id
        return self._endpoint()

    def predict(self, command, principal):
        assert command.request_id == "req-001"
        assert command.payload["amount"] == 128.45
        return InferencePrediction(
            log_id=self.log_id,
            endpoint_id=self.endpoint_id,
            deployment_revision_id=self.revision_id,
            request_id="req-001",
            status=InferenceRequestStatus.SUCCEEDED,
            latency_ms=17.4,
            output_payload={"score": 0.81},
        )

    def list_request_logs(self, endpoint_id, principal):
        assert endpoint_id == self.endpoint_id
        return [
            InferenceRequestLog(
                id=self.log_id,
                endpoint_id=self.endpoint_id,
                deployment_revision_id=self.revision_id,
                request_id="req-001",
                status=InferenceRequestStatus.SUCCEEDED,
                latency_ms=17.4,
                input_payload={"amount": 128.45},
                output_payload={"score": 0.81},
                error_message=None,
            )
        ]

    def record_metric_snapshot(self, command, principal):
        assert command.prediction_count == 1200
        return self._snapshot()

    def list_metric_snapshots(self, endpoint_id, principal):
        assert endpoint_id == self.endpoint_id
        return [self._snapshot()]

    def _endpoint(self) -> InferenceEndpoint:
        return InferenceEndpoint(
            id=self.endpoint_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            deployment_id=self.deployment_id,
            deployment_revision_id=self.revision_id,
            name="Fraud Risk Online",
            slug="fraud-risk-online",
            route_path="/inference/fraud-risk-online",
            description="Real-time fraud scoring.",
            status=InferenceEndpointStatus.ACTIVE,
            created_by=self.user_id,
        )

    def _snapshot(self) -> InferenceMetricSnapshot:
        return InferenceMetricSnapshot(
            id=self.snapshot_id,
            endpoint_id=self.endpoint_id,
            window_seconds=300,
            prediction_count=1200,
            error_count=3,
            p50_latency_ms=18.2,
            p95_latency_ms=46.8,
        )


def test_inference_routes_expose_endpoint_prediction_and_metric_lifecycle() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    service = FakeInferenceService(
        organization_id=organization_id,
        project_id=project_id,
        user_id=user_id,
        deployment_id=uuid4(),
        revision_id=uuid4(),
        endpoint_id=uuid4(),
        log_id=uuid4(),
        snapshot_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_inference_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{project_id}/inference-endpoints",
        json={
            "deployment_id": str(service.deployment_id),
            "deployment_revision_id": str(service.revision_id),
            "name": "Fraud Risk Online",
            "description": "Real-time fraud scoring.",
        },
    )
    listed = client.get(f"/api/v1/projects/{project_id}/inference-endpoints")
    fetched = client.get(f"/api/v1/inference-endpoints/{service.endpoint_id}")
    prediction = client.post(
        f"/api/v1/inference-endpoints/{service.endpoint_id}/predict",
        json={"request_id": "req-001", "payload": {"amount": 128.45}},
    )
    requests = client.get(f"/api/v1/inference-endpoints/{service.endpoint_id}/requests")
    recorded_snapshot = client.post(
        f"/api/v1/inference-endpoints/{service.endpoint_id}/metric-snapshots",
        json={
            "window_seconds": 300,
            "prediction_count": 1200,
            "error_count": 3,
            "p50_latency_ms": 18.2,
            "p95_latency_ms": 46.8,
        },
    )
    snapshots = client.get(
        f"/api/v1/inference-endpoints/{service.endpoint_id}/metric-snapshots"
    )

    assert created.status_code == 201
    assert created.json()["route_path"] == "/inference/fraud-risk-online"
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == str(service.endpoint_id)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "active"
    assert prediction.status_code == 200
    assert prediction.json()["output_payload"]["score"] == 0.81
    assert requests.status_code == 200
    assert requests.json()["items"][0]["request_id"] == "req-001"
    assert recorded_snapshot.status_code == 201
    assert recorded_snapshot.json()["p95_latency_ms"] == 46.8
    assert snapshots.status_code == 200
    assert snapshots.json()["items"][0]["prediction_count"] == 1200
