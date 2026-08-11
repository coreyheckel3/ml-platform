from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.monitoring.api.routes import get_monitoring_service
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

    def get_operations_overview(self, project_id, principal):
        assert project_id == self.project_id
        observed_at = datetime.now(UTC)
        return MonitoringOperationsOverview(
            project_id=self.project_id,
            active_alert_count=1,
            inference=MonitoringInferenceOverview(
                endpoint_count=1,
                prediction_count=1200,
                error_count=3,
                request_count=12,
                error_rate=0.0025,
                weighted_p50_latency_ms=18.2,
                weighted_p95_latency_ms=46.8,
                latency_percentiles=(
                    MonitoringLatencyPercentile(
                        endpoint_id=self.endpoint_id,
                        endpoint_name="Fraud Risk Online",
                        p50_latency_ms=18.2,
                        p95_latency_ms=46.8,
                        prediction_count=1200,
                        latest_window_seconds=300,
                    ),
                ),
                error_breakdown=(
                    MonitoringInferenceErrorBreakdown(
                        endpoint_id=self.endpoint_id,
                        endpoint_name="Fraud Risk Online",
                        error_count=3,
                        request_count=12,
                        error_rate=0.0025,
                        status="active",
                    ),
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
                        endpoint_id=self.endpoint_id,
                        deployment_id=self.deployment_id,
                        status="completed",
                        drift_score=0.42,
                        drift_threshold=0.2,
                        drifted_feature_count=3,
                        evaluated_feature_count=24,
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
                        error_message="trainer failed",
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
                        deployment_id=self.deployment_id,
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
    operations = client.get(f"/api/v1/projects/{service.project_id}/monitoring/operations")
    endpoints = client.get(
        f"/api/v1/projects/{service.project_id}/monitoring/inference-endpoints"
    )

    assert summary.status_code == 200
    assert summary.json()["prediction_count"] == 1200
    assert summary.json()["active_alert_count"] == 1
    assert operations.status_code == 200
    assert operations.json()["drift"]["breached_report_count"] == 1
    assert operations.json()["training"]["latest_failures"][0]["algorithm"] == "xgboost"
    assert operations.json()["retraining"]["pending_approval_count"] == 1
    assert endpoints.status_code == 200
    assert endpoints.json()["items"][0]["route_path"] == "/inference/fraud-risk-online"
