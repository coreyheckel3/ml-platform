from uuid import UUID, uuid4

from forgeml.modules.monitoring.application.services import MonitoringService
from forgeml.modules.monitoring.domain.entities import InferenceEndpointMonitoringSummary
from forgeml.platform.security.rbac import Principal


class FakeMonitoringRepository:
    def __init__(
        self,
        summaries: list[InferenceEndpointMonitoringSummary],
        active_alert_count: int,
    ) -> None:
        self.summaries = summaries
        self.active_alert_count = active_alert_count

    def list_inference_endpoint_summaries(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[InferenceEndpointMonitoringSummary]:
        return self.summaries

    def count_active_alerts(self, organization_id: UUID, project_id: UUID) -> int:
        return self.active_alert_count


def test_monitoring_service_aggregates_project_summary() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    service = MonitoringService(
        repository=FakeMonitoringRepository(
            [
                _endpoint_summary(project_id, prediction_count=1000, error_count=5, p95=42.1),
                _endpoint_summary(project_id, prediction_count=500, error_count=10, p95=88.4),
            ],
            active_alert_count=2,
        )
    )
    actor = Principal(
        user_id=str(uuid4()),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"monitoring:read"}),
    )

    summary = service.get_project_summary(project_id, actor)

    assert summary.inference_endpoint_count == 2
    assert summary.prediction_count == 1500
    assert summary.error_count == 15
    assert summary.error_rate == 0.01
    assert summary.max_p95_latency_ms == 88.4
    assert summary.active_alert_count == 2


def _endpoint_summary(
    project_id: UUID,
    *,
    prediction_count: int,
    error_count: int,
    p95: float,
) -> InferenceEndpointMonitoringSummary:
    return InferenceEndpointMonitoringSummary(
        endpoint_id=uuid4(),
        endpoint_name="Fraud Risk Online",
        route_path="/inference/fraud-risk-online",
        status="active",
        deployment_id=uuid4(),
        deployment_revision_id=uuid4(),
        latest_window_seconds=300,
        prediction_count=prediction_count,
        error_count=error_count,
        request_count=prediction_count,
        error_rate=error_count / prediction_count,
        p50_latency_ms=18.2,
        p95_latency_ms=p95,
    )
