from uuid import UUID, uuid4

import pytest

from forgeml.modules.inference.application.services import (
    CreateInferenceEndpointCommand,
    InferenceService,
    PredictCommand,
    RecordInferenceMetricSnapshotCommand,
)
from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceEndpoint,
    InferenceMetricSnapshot,
    InferencePredictionResult,
    InferenceRequestLog,
)
from forgeml.platform.domain.errors import ConflictError, DomainValidationError
from forgeml.platform.security.rbac import Principal


class FakeInferenceRepository:
    def __init__(self) -> None:
        self.endpoints: dict[UUID, InferenceEndpoint] = {}
        self.references: dict[UUID, DeploymentRevisionServingReference] = {}
        self.request_logs: list[InferenceRequestLog] = []
        self.metric_snapshots: list[InferenceMetricSnapshot] = []

    def add_endpoint(self, endpoint: InferenceEndpoint) -> InferenceEndpoint:
        self.endpoints[endpoint.id] = endpoint
        return endpoint

    def get_endpoint(self, endpoint_id: UUID) -> InferenceEndpoint | None:
        return self.endpoints.get(endpoint_id)

    def list_endpoints(self, organization_id: UUID, project_id: UUID) -> list[InferenceEndpoint]:
        return [
            endpoint
            for endpoint in self.endpoints.values()
            if endpoint.organization_id == organization_id and endpoint.project_id == project_id
        ]

    def route_path_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        route_path: str,
    ) -> bool:
        return any(
            endpoint.organization_id == organization_id
            and endpoint.project_id == project_id
            and endpoint.route_path == route_path
            for endpoint in self.endpoints.values()
        )

    def get_serving_reference(
        self,
        deployment_revision_id: UUID,
    ) -> DeploymentRevisionServingReference | None:
        return self.references.get(deployment_revision_id)

    def add_request_log(self, request_log: InferenceRequestLog) -> InferenceRequestLog:
        self.request_logs.append(request_log)
        return request_log

    def list_request_logs(self, endpoint_id: UUID) -> list[InferenceRequestLog]:
        return [
            request_log
            for request_log in self.request_logs
            if request_log.endpoint_id == endpoint_id
        ]

    def add_metric_snapshot(
        self,
        snapshot: InferenceMetricSnapshot,
    ) -> InferenceMetricSnapshot:
        self.metric_snapshots.append(snapshot)
        return snapshot

    def list_metric_snapshots(self, endpoint_id: UUID) -> list[InferenceMetricSnapshot]:
        return [
            snapshot for snapshot in self.metric_snapshots if snapshot.endpoint_id == endpoint_id
        ]


class FakeInferenceRuntime:
    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        return InferencePredictionResult(
            output_payload={
                "model_version_id": str(reference.model_version_id),
                "features_seen": len(payload),
                "score": 0.81,
            },
            latency_ms=17.4,
        )


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_inference_service_creates_endpoint_predicts_and_records_metrics() -> None:
    repository = FakeInferenceRepository()
    service = InferenceService(repository=repository, runtime=FakeInferenceRuntime())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    repository.references[revision_id] = _serving_reference(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        revision_id=revision_id,
        revision_status="healthy",
        traffic_percentage=100,
    )
    actor = principal(
        organization_id,
        user_id,
        {
            "inference_endpoints:create",
            "inference_endpoints:read",
            "inference:predict",
            "inference_metrics:write",
        },
    )

    endpoint = service.create_endpoint(
        CreateInferenceEndpointCommand(
            organization_id=organization_id,
            project_id=project_id,
            deployment_id=deployment_id,
            deployment_revision_id=revision_id,
            name="Fraud Risk Online",
            description="Real-time fraud scoring.",
            route_path=None,
            created_by=user_id,
        ),
        actor,
    )
    prediction = service.predict(
        PredictCommand(
            endpoint_id=endpoint.id,
            payload={"amount": 128.45, "merchant_category": "travel"},
            request_id="req-001",
        ),
        actor,
    )
    snapshot = service.record_metric_snapshot(
        RecordInferenceMetricSnapshotCommand(
            endpoint_id=endpoint.id,
            window_seconds=300,
            prediction_count=1200,
            error_count=3,
            p50_latency_ms=18.2,
            p95_latency_ms=46.8,
        ),
        actor,
    )

    assert endpoint.route_path == "/inference/fraud-risk-online"
    assert prediction.request_id == "req-001"
    assert prediction.output_payload["score"] == 0.81
    assert service.list_request_logs(endpoint.id, actor)[0].latency_ms == 17.4
    assert snapshot.p95_latency_ms == 46.8
    assert service.list_metric_snapshots(endpoint.id, actor)[0].prediction_count == 1200


def test_inference_service_rejects_duplicate_route() -> None:
    repository = FakeInferenceRepository()
    service = InferenceService(repository=repository, runtime=FakeInferenceRuntime())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    repository.references[revision_id] = _serving_reference(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        revision_id=revision_id,
        revision_status="healthy",
        traffic_percentage=100,
    )
    actor = principal(organization_id, user_id, {"inference_endpoints:create"})
    command = CreateInferenceEndpointCommand(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        deployment_revision_id=revision_id,
        name="Fraud Risk Online",
        description="",
        route_path="/inference/fraud-risk",
        created_by=user_id,
    )

    service.create_endpoint(command, actor)

    with pytest.raises(ConflictError):
        service.create_endpoint(command, actor)


def test_inference_service_rejects_unservable_revision() -> None:
    repository = FakeInferenceRepository()
    service = InferenceService(repository=repository, runtime=FakeInferenceRuntime())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    repository.references[revision_id] = _serving_reference(
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=deployment_id,
        revision_id=revision_id,
        revision_status="failed",
        traffic_percentage=0,
    )
    actor = principal(organization_id, user_id, {"inference_endpoints:create"})

    with pytest.raises(DomainValidationError):
        service.create_endpoint(
            CreateInferenceEndpointCommand(
                organization_id=organization_id,
                project_id=project_id,
                deployment_id=deployment_id,
                deployment_revision_id=revision_id,
                name="Fraud Risk Online",
                description="",
                route_path=None,
                created_by=user_id,
            ),
            actor,
        )


def _serving_reference(
    *,
    organization_id: UUID,
    project_id: UUID,
    deployment_id: UUID,
    revision_id: UUID,
    revision_status: str,
    traffic_percentage: int,
) -> DeploymentRevisionServingReference:
    return DeploymentRevisionServingReference(
        deployment_id=deployment_id,
        deployment_revision_id=revision_id,
        organization_id=organization_id,
        project_id=project_id,
        deployment_status="active",
        revision_status=revision_status,
        traffic_percentage=traffic_percentage,
        model_version_id=uuid4(),
        model_signature={"inputs": ["amount"], "outputs": ["score"]},
    )
