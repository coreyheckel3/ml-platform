from datetime import UTC, datetime
from uuid import UUID, uuid4

from forgeml.modules.monitoring.application.services import MonitoringService
from forgeml.modules.monitoring.domain.entities import (
    InferenceEndpointMonitoringSummary,
    MonitoringDriftOverview,
    MonitoringDriftSignal,
    MonitoringInferenceErrorBreakdown,
    MonitoringInferenceOverview,
    MonitoringLatencyPercentile,
    MonitoringOperationsOverview,
    MonitoringRetrainingActivity,
    MonitoringRetrainingOverview,
    MonitoringTrainingFailure,
    MonitoringTrainingOverview,
)
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

    def get_operations_overview(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> MonitoringOperationsOverview:
        summaries = self.list_inference_endpoint_summaries(organization_id, project_id)
        return _operations_overview(project_id, summaries, self.active_alert_count)


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


def test_monitoring_service_returns_operations_overview() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    service = MonitoringService(
        repository=FakeMonitoringRepository(
            [
                _endpoint_summary(project_id, prediction_count=1000, error_count=50, p95=620.0),
                _endpoint_summary(project_id, prediction_count=500, error_count=5, p95=120.0),
            ],
            active_alert_count=3,
        )
    )
    actor = Principal(
        user_id=str(uuid4()),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"monitoring:read"}),
    )

    overview = service.get_operations_overview(project_id, actor)

    assert overview.active_alert_count == 3
    assert overview.inference.endpoint_count == 2
    assert overview.inference.error_count == 55
    assert round(overview.inference.weighted_p95_latency_ms, 3) == 453.333
    assert overview.drift.breached_report_count == 1
    assert overview.training.failed_count == 1
    assert overview.training.latest_failures[0].status == "failed"
    assert overview.retraining.pending_approval_count == 1


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


def _operations_overview(
    project_id: UUID,
    summaries: list[InferenceEndpointMonitoringSummary],
    active_alert_count: int,
) -> MonitoringOperationsOverview:
    endpoint = summaries[0]
    observed_at = datetime.now(UTC)
    prediction_count = sum(summary.prediction_count for summary in summaries)
    error_count = sum(summary.error_count for summary in summaries)
    weighted_p95 = sum(
        summary.p95_latency_ms * summary.prediction_count for summary in summaries
    ) / prediction_count
    return MonitoringOperationsOverview(
        project_id=project_id,
        active_alert_count=active_alert_count,
        inference=MonitoringInferenceOverview(
            endpoint_count=len(summaries),
            prediction_count=prediction_count,
            error_count=error_count,
            request_count=sum(summary.request_count for summary in summaries),
            error_rate=error_count / prediction_count,
            weighted_p50_latency_ms=18.2,
            weighted_p95_latency_ms=weighted_p95,
            latency_percentiles=tuple(
                MonitoringLatencyPercentile(
                    endpoint_id=summary.endpoint_id,
                    endpoint_name=summary.endpoint_name,
                    p50_latency_ms=summary.p50_latency_ms,
                    p95_latency_ms=summary.p95_latency_ms,
                    prediction_count=summary.prediction_count,
                    latest_window_seconds=summary.latest_window_seconds,
                )
                for summary in summaries
            ),
            error_breakdown=tuple(
                MonitoringInferenceErrorBreakdown(
                    endpoint_id=summary.endpoint_id,
                    endpoint_name=summary.endpoint_name,
                    error_count=summary.error_count,
                    request_count=summary.request_count,
                    error_rate=summary.error_rate,
                    status=summary.status,
                )
                for summary in summaries
            ),
        ),
        drift=MonitoringDriftOverview(
            report_count=2,
            failed_report_count=0,
            breached_report_count=1,
            latest_drift_score=0.42,
            drifted_feature_count=3,
            signals=(
                MonitoringDriftSignal(
                    drift_report_id=uuid4(),
                    endpoint_id=endpoint.endpoint_id,
                    deployment_id=endpoint.deployment_id,
                    status="completed",
                    drift_score=0.42,
                    drift_threshold=0.2,
                    drifted_feature_count=3,
                    evaluated_feature_count=20,
                    created_at=observed_at,
                ),
            ),
        ),
        training=MonitoringTrainingOverview(
            total_run_count=8,
            running_count=1,
            failed_count=1,
            dead_lettered_count=0,
            failure_rate=0.125,
            average_training_time_seconds=240.0,
            latest_failures=(
                MonitoringTrainingFailure(
                    training_run_id=uuid4(),
                    algorithm="xgboost",
                    model_type="classification",
                    status="failed",
                    objective_metric_name="auc",
                    error_message="validation split missing target",
                    attempt_count=2,
                    completed_at=observed_at,
                ),
            ),
        ),
        retraining=MonitoringRetrainingOverview(
            policy_count=2,
            enabled_policy_count=1,
            run_count=4,
            pending_approval_count=1,
            queued_count=1,
            running_count=0,
            succeeded_count=1,
            failed_count=0,
            skipped_count=1,
            latest_activity=(
                MonitoringRetrainingActivity(
                    retraining_run_id=uuid4(),
                    policy_id=uuid4(),
                    deployment_id=endpoint.deployment_id,
                    trigger_type="drift",
                    status="pending_approval",
                    training_run_id=None,
                    drift_report_id=uuid4(),
                    alert_event_id=None,
                    created_at=observed_at,
                ),
            ),
        ),
    )
