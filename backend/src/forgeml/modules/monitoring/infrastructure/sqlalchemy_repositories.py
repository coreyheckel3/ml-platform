from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forgeml.modules.alerting.infrastructure.sqlalchemy_models import AlertEventModel
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
    InferenceRequestLogModel,
)
from forgeml.modules.monitoring.domain.entities import InferenceEndpointMonitoringSummary


class SqlAlchemyMonitoringRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_inference_endpoint_summaries(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[InferenceEndpointMonitoringSummary]:
        endpoints = self._session.scalars(
            select(InferenceEndpointModel)
            .where(
                InferenceEndpointModel.organization_id == organization_id,
                InferenceEndpointModel.project_id == project_id,
            )
            .order_by(InferenceEndpointModel.name)
        ).all()
        return [self._endpoint_summary(endpoint) for endpoint in endpoints]

    def count_active_alerts(self, organization_id: UUID, project_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count(AlertEventModel.id)).where(
                    AlertEventModel.organization_id == organization_id,
                    AlertEventModel.project_id == project_id,
                    AlertEventModel.status.in_(("open", "acknowledged")),
                )
            )
            or 0
        )

    def _endpoint_summary(
        self,
        endpoint: InferenceEndpointModel,
    ) -> InferenceEndpointMonitoringSummary:
        latest_snapshot = self._session.scalars(
            select(InferenceMetricSnapshotModel)
            .where(InferenceMetricSnapshotModel.endpoint_id == endpoint.id)
            .order_by(InferenceMetricSnapshotModel.created_at.desc())
        ).first()
        request_count = int(
            self._session.scalar(
                select(func.count(InferenceRequestLogModel.id)).where(
                    InferenceRequestLogModel.endpoint_id == endpoint.id
                )
            )
            or 0
        )
        prediction_count = latest_snapshot.prediction_count if latest_snapshot else request_count
        error_count = latest_snapshot.error_count if latest_snapshot else 0
        p50_latency_ms = float(latest_snapshot.p50_latency_ms) if latest_snapshot else 0.0
        p95_latency_ms = float(latest_snapshot.p95_latency_ms) if latest_snapshot else 0.0
        latest_window_seconds = latest_snapshot.window_seconds if latest_snapshot else 0
        return InferenceEndpointMonitoringSummary(
            endpoint_id=endpoint.id,
            endpoint_name=endpoint.name,
            route_path=endpoint.route_path,
            status=endpoint.status,
            deployment_id=endpoint.deployment_id,
            deployment_revision_id=endpoint.deployment_revision_id,
            latest_window_seconds=latest_window_seconds,
            prediction_count=prediction_count,
            error_count=error_count,
            request_count=request_count,
            error_rate=_safe_rate(error_count, prediction_count),
            p50_latency_ms=p50_latency_ms,
            p95_latency_ms=p95_latency_ms,
        )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
