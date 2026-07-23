from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forgeml.modules.monitoring.api.schemas import (
    InferenceEndpointMonitoringSummaryListResponse,
    InferenceEndpointMonitoringSummaryResponse,
    ProjectMonitoringSummaryResponse,
)
from forgeml.modules.monitoring.application.services import MonitoringService
from forgeml.modules.monitoring.domain.entities import (
    InferenceEndpointMonitoringSummary,
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
