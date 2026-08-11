from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forgeml.modules.monitoring.api.schemas import (
    InferenceEndpointMonitoringSummaryListResponse,
    InferenceEndpointMonitoringSummaryResponse,
    MonitoringDriftOverviewResponse,
    MonitoringDriftSignalResponse,
    MonitoringInferenceErrorBreakdownResponse,
    MonitoringInferenceOverviewResponse,
    MonitoringLatencyPercentileResponse,
    MonitoringOperationsOverviewResponse,
    MonitoringRetrainingActivityResponse,
    MonitoringRetrainingOverviewResponse,
    MonitoringTrainingFailureResponse,
    MonitoringTrainingOverviewResponse,
    ProjectMonitoringSummaryResponse,
)
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
    ProjectMonitoringSummary,
)
from forgeml.modules.monitoring.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyMonitoringRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["monitoring"])


def get_monitoring_service(
    session: Session = Depends(get_db_session),
) -> MonitoringService:
    return MonitoringService(repository=SqlAlchemyMonitoringRepository(session))


@router.get(
    "/projects/{project_id}/monitoring/summary",
    response_model=ProjectMonitoringSummaryResponse,
)
def get_project_monitoring_summary(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: MonitoringService = Depends(get_monitoring_service),
) -> ProjectMonitoringSummaryResponse:
    return _project_summary_response(service.get_project_summary(project_id, principal))


@router.get(
    "/projects/{project_id}/monitoring/operations",
    response_model=MonitoringOperationsOverviewResponse,
)
def get_project_monitoring_operations(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: MonitoringService = Depends(get_monitoring_service),
) -> MonitoringOperationsOverviewResponse:
    return _operations_overview_response(
        service.get_operations_overview(project_id, principal)
    )


@router.get(
    "/projects/{project_id}/monitoring/inference-endpoints",
    response_model=InferenceEndpointMonitoringSummaryListResponse,
)
def list_inference_endpoint_monitoring_summaries(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: MonitoringService = Depends(get_monitoring_service),
) -> InferenceEndpointMonitoringSummaryListResponse:
    return InferenceEndpointMonitoringSummaryListResponse(
        items=[
            _endpoint_summary_response(summary)
            for summary in service.list_inference_endpoint_summaries(project_id, principal)
        ]
    )


def _project_summary_response(
    summary: ProjectMonitoringSummary,
) -> ProjectMonitoringSummaryResponse:
    return ProjectMonitoringSummaryResponse(
        project_id=str(summary.project_id),
        inference_endpoint_count=summary.inference_endpoint_count,
        prediction_count=summary.prediction_count,
        error_count=summary.error_count,
        request_count=summary.request_count,
        active_alert_count=summary.active_alert_count,
        error_rate=summary.error_rate,
        max_p95_latency_ms=summary.max_p95_latency_ms,
    )


def _endpoint_summary_response(
    summary: InferenceEndpointMonitoringSummary,
) -> InferenceEndpointMonitoringSummaryResponse:
    return InferenceEndpointMonitoringSummaryResponse(
        endpoint_id=str(summary.endpoint_id),
        endpoint_name=summary.endpoint_name,
        route_path=summary.route_path,
        status=summary.status,
        deployment_id=str(summary.deployment_id),
        deployment_revision_id=str(summary.deployment_revision_id),
        latest_window_seconds=summary.latest_window_seconds,
        prediction_count=summary.prediction_count,
        error_count=summary.error_count,
        request_count=summary.request_count,
        error_rate=summary.error_rate,
        p50_latency_ms=summary.p50_latency_ms,
        p95_latency_ms=summary.p95_latency_ms,
    )


def _operations_overview_response(
    overview: MonitoringOperationsOverview,
) -> MonitoringOperationsOverviewResponse:
    return MonitoringOperationsOverviewResponse(
        project_id=str(overview.project_id),
        active_alert_count=overview.active_alert_count,
        inference=_inference_overview_response(overview.inference),
        drift=_drift_overview_response(overview.drift),
        training=_training_overview_response(overview.training),
        retraining=_retraining_overview_response(overview.retraining),
    )


def _inference_overview_response(
    overview: MonitoringInferenceOverview,
) -> MonitoringInferenceOverviewResponse:
    return MonitoringInferenceOverviewResponse(
        endpoint_count=overview.endpoint_count,
        prediction_count=overview.prediction_count,
        error_count=overview.error_count,
        request_count=overview.request_count,
        error_rate=overview.error_rate,
        weighted_p50_latency_ms=overview.weighted_p50_latency_ms,
        weighted_p95_latency_ms=overview.weighted_p95_latency_ms,
        latency_percentiles=[
            _latency_percentile_response(percentile)
            for percentile in overview.latency_percentiles
        ],
        error_breakdown=[
            _error_breakdown_response(breakdown)
            for breakdown in overview.error_breakdown
        ],
    )


def _latency_percentile_response(
    percentile: MonitoringLatencyPercentile,
) -> MonitoringLatencyPercentileResponse:
    return MonitoringLatencyPercentileResponse(
        endpoint_id=str(percentile.endpoint_id),
        endpoint_name=percentile.endpoint_name,
        p50_latency_ms=percentile.p50_latency_ms,
        p95_latency_ms=percentile.p95_latency_ms,
        prediction_count=percentile.prediction_count,
        latest_window_seconds=percentile.latest_window_seconds,
    )


def _error_breakdown_response(
    breakdown: MonitoringInferenceErrorBreakdown,
) -> MonitoringInferenceErrorBreakdownResponse:
    return MonitoringInferenceErrorBreakdownResponse(
        endpoint_id=str(breakdown.endpoint_id),
        endpoint_name=breakdown.endpoint_name,
        error_count=breakdown.error_count,
        request_count=breakdown.request_count,
        error_rate=breakdown.error_rate,
        status=breakdown.status,
    )


def _drift_overview_response(
    overview: MonitoringDriftOverview,
) -> MonitoringDriftOverviewResponse:
    return MonitoringDriftOverviewResponse(
        report_count=overview.report_count,
        failed_report_count=overview.failed_report_count,
        breached_report_count=overview.breached_report_count,
        latest_drift_score=overview.latest_drift_score,
        drifted_feature_count=overview.drifted_feature_count,
        signals=[_drift_signal_response(signal) for signal in overview.signals],
    )


def _drift_signal_response(signal: MonitoringDriftSignal) -> MonitoringDriftSignalResponse:
    return MonitoringDriftSignalResponse(
        drift_report_id=str(signal.drift_report_id),
        endpoint_id=str(signal.endpoint_id),
        deployment_id=str(signal.deployment_id),
        status=signal.status,
        drift_score=signal.drift_score,
        drift_threshold=signal.drift_threshold,
        drifted_feature_count=signal.drifted_feature_count,
        evaluated_feature_count=signal.evaluated_feature_count,
        created_at=signal.created_at.isoformat() if signal.created_at else None,
    )


def _training_overview_response(
    overview: MonitoringTrainingOverview,
) -> MonitoringTrainingOverviewResponse:
    return MonitoringTrainingOverviewResponse(
        total_run_count=overview.total_run_count,
        running_count=overview.running_count,
        failed_count=overview.failed_count,
        dead_lettered_count=overview.dead_lettered_count,
        failure_rate=overview.failure_rate,
        average_training_time_seconds=overview.average_training_time_seconds,
        latest_failures=[
            _training_failure_response(failure) for failure in overview.latest_failures
        ],
    )


def _training_failure_response(
    failure: MonitoringTrainingFailure,
) -> MonitoringTrainingFailureResponse:
    return MonitoringTrainingFailureResponse(
        training_run_id=str(failure.training_run_id),
        algorithm=failure.algorithm,
        model_type=failure.model_type,
        status=failure.status,
        objective_metric_name=failure.objective_metric_name,
        error_message=failure.error_message,
        attempt_count=failure.attempt_count,
        completed_at=failure.completed_at.isoformat() if failure.completed_at else None,
    )


def _retraining_overview_response(
    overview: MonitoringRetrainingOverview,
) -> MonitoringRetrainingOverviewResponse:
    return MonitoringRetrainingOverviewResponse(
        policy_count=overview.policy_count,
        enabled_policy_count=overview.enabled_policy_count,
        run_count=overview.run_count,
        pending_approval_count=overview.pending_approval_count,
        queued_count=overview.queued_count,
        running_count=overview.running_count,
        succeeded_count=overview.succeeded_count,
        failed_count=overview.failed_count,
        skipped_count=overview.skipped_count,
        latest_activity=[
            _retraining_activity_response(activity)
            for activity in overview.latest_activity
        ],
    )


def _retraining_activity_response(
    activity: MonitoringRetrainingActivity,
) -> MonitoringRetrainingActivityResponse:
    return MonitoringRetrainingActivityResponse(
        retraining_run_id=str(activity.retraining_run_id),
        policy_id=str(activity.policy_id),
        deployment_id=str(activity.deployment_id),
        trigger_type=activity.trigger_type,
        status=activity.status,
        training_run_id=str(activity.training_run_id) if activity.training_run_id else None,
        drift_report_id=str(activity.drift_report_id) if activity.drift_report_id else None,
        alert_event_id=str(activity.alert_event_id) if activity.alert_event_id else None,
        created_at=activity.created_at.isoformat() if activity.created_at else None,
    )
