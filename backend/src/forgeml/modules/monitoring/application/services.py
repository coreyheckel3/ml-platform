from uuid import UUID

from forgeml.modules.monitoring.domain.entities import (
    InferenceEndpointMonitoringSummary,
    ProjectMonitoringSummary,
)
from forgeml.modules.monitoring.repositories.interfaces import MonitoringRepository
from forgeml.platform.domain.errors import PermissionDeniedError
from forgeml.platform.security.rbac import Principal


class MonitoringService:
    def __init__(self, *, repository: MonitoringRepository) -> None:
        self._repository = repository

    def get_project_summary(
        self,
        project_id: UUID,
        principal: Principal,
    ) -> ProjectMonitoringSummary:
        self._require(principal, "monitoring:read")
        organization_id = UUID(principal.organization_id)
        endpoint_summaries = self._repository.list_inference_endpoint_summaries(
            organization_id,
            project_id,
        )
        prediction_count = sum(summary.prediction_count for summary in endpoint_summaries)
        error_count = sum(summary.error_count for summary in endpoint_summaries)
        request_count = sum(summary.request_count for summary in endpoint_summaries)
        max_p95_latency_ms = max(
            (summary.p95_latency_ms for summary in endpoint_summaries),
            default=0.0,
        )
        return ProjectMonitoringSummary(
            project_id=project_id,
            inference_endpoint_count=len(endpoint_summaries),
            prediction_count=prediction_count,
            error_count=error_count,
            request_count=request_count,
            active_alert_count=self._repository.count_active_alerts(
                organization_id,
                project_id,
            ),
            error_rate=_safe_rate(error_count, prediction_count),
            max_p95_latency_ms=max_p95_latency_ms,
        )

    def list_inference_endpoint_summaries(
        self,
        project_id: UUID,
        principal: Principal,
    ) -> list[InferenceEndpointMonitoringSummary]:
        self._require(principal, "monitoring:read")
        return self._repository.list_inference_endpoint_summaries(
            UUID(principal.organization_id),
            project_id,
        )

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to read monitoring data.")


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
