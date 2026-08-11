from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forgeml.modules.alerting.infrastructure.sqlalchemy_models import AlertEventModel
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import DriftReportModel
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
    InferenceRequestLogModel,
)
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
from forgeml.modules.retraining.infrastructure.sqlalchemy_models import (
    RetrainingPolicyModel,
    RetrainingRunModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel


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

    def get_operations_overview(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> MonitoringOperationsOverview:
        endpoints = self.list_inference_endpoint_summaries(
            organization_id,
            project_id,
        )
        return MonitoringOperationsOverview(
            project_id=project_id,
            active_alert_count=self.count_active_alerts(organization_id, project_id),
            inference=_build_inference_overview(endpoints),
            drift=self._drift_overview(organization_id, project_id),
            training=self._training_overview(organization_id, project_id),
            retraining=self._retraining_overview(organization_id, project_id),
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

    def _drift_overview(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> MonitoringDriftOverview:
        report_count = _count_rows(
            self._session,
            select(func.count(DriftReportModel.id)).where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
            ),
        )
        failed_report_count = _count_rows(
            self._session,
            select(func.count(DriftReportModel.id)).where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
                DriftReportModel.status == "failed",
            ),
        )
        breached_report_count = _count_rows(
            self._session,
            select(func.count(DriftReportModel.id)).where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
                DriftReportModel.status == "completed",
                DriftReportModel.drift_score >= DriftReportModel.drift_threshold,
            ),
        )
        recent_reports = self._session.scalars(
            select(DriftReportModel)
            .where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
            )
            .order_by(DriftReportModel.created_at.desc())
            .limit(5)
        ).all()
        latest_report = recent_reports[0] if recent_reports else None
        return MonitoringDriftOverview(
            report_count=report_count,
            failed_report_count=failed_report_count,
            breached_report_count=breached_report_count,
            latest_drift_score=float(latest_report.drift_score) if latest_report else 0.0,
            drifted_feature_count=(
                int(latest_report.drifted_feature_count) if latest_report else 0
            ),
            signals=tuple(_drift_signal(report) for report in recent_reports),
        )

    def _training_overview(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> MonitoringTrainingOverview:
        total_run_count = _count_rows(
            self._session,
            select(func.count(TrainingRunModel.id)).where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
            ),
        )
        running_count = _count_training_runs(
            self._session,
            organization_id,
            project_id,
            ("running",),
        )
        failed_count = _count_training_runs(
            self._session,
            organization_id,
            project_id,
            ("failed",),
        )
        dead_lettered_count = _count_training_runs(
            self._session,
            organization_id,
            project_id,
            ("dead_lettered",),
        )
        duration_rows = self._session.scalars(
            select(TrainingRunModel).where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
                TrainingRunModel.started_at.is_not(None),
                TrainingRunModel.completed_at.is_not(None),
            )
        ).all()
        durations = [
            (run.completed_at - run.started_at).total_seconds()
            for run in duration_rows
            if run.completed_at is not None and run.started_at is not None
        ]
        failure_rows = self._session.scalars(
            select(TrainingRunModel)
            .where(
                TrainingRunModel.organization_id == organization_id,
                TrainingRunModel.project_id == project_id,
                TrainingRunModel.status.in_(("failed", "dead_lettered")),
            )
            .order_by(TrainingRunModel.updated_at.desc())
            .limit(5)
        ).all()
        return MonitoringTrainingOverview(
            total_run_count=total_run_count,
            running_count=running_count,
            failed_count=failed_count,
            dead_lettered_count=dead_lettered_count,
            failure_rate=_safe_rate(failed_count + dead_lettered_count, total_run_count),
            average_training_time_seconds=(
                sum(durations) / len(durations) if durations else 0.0
            ),
            latest_failures=tuple(_training_failure(run) for run in failure_rows),
        )

    def _retraining_overview(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> MonitoringRetrainingOverview:
        policy_count = _count_rows(
            self._session,
            select(func.count(RetrainingPolicyModel.id)).where(
                RetrainingPolicyModel.organization_id == organization_id,
                RetrainingPolicyModel.project_id == project_id,
            ),
        )
        enabled_policy_count = _count_rows(
            self._session,
            select(func.count(RetrainingPolicyModel.id)).where(
                RetrainingPolicyModel.organization_id == organization_id,
                RetrainingPolicyModel.project_id == project_id,
                RetrainingPolicyModel.enabled.is_(True),
                RetrainingPolicyModel.status == "active",
            ),
        )
        run_count = _count_rows(
            self._session,
            select(func.count(RetrainingRunModel.id)).where(
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
            ),
        )
        latest_runs = self._session.scalars(
            select(RetrainingRunModel)
            .where(
                RetrainingRunModel.organization_id == organization_id,
                RetrainingRunModel.project_id == project_id,
            )
            .order_by(RetrainingRunModel.updated_at.desc())
            .limit(5)
        ).all()
        return MonitoringRetrainingOverview(
            policy_count=policy_count,
            enabled_policy_count=enabled_policy_count,
            run_count=run_count,
            pending_approval_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("pending_approval",),
            ),
            queued_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("queued",),
            ),
            running_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("running",),
            ),
            succeeded_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("succeeded",),
            ),
            failed_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("failed", "canceled", "rejected"),
            ),
            skipped_count=_count_retraining_runs(
                self._session,
                organization_id,
                project_id,
                ("skipped",),
            ),
            latest_activity=tuple(_retraining_activity(run) for run in latest_runs),
        )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _build_inference_overview(
    endpoints: list[InferenceEndpointMonitoringSummary],
) -> MonitoringInferenceOverview:
    prediction_count = sum(endpoint.prediction_count for endpoint in endpoints)
    error_count = sum(endpoint.error_count for endpoint in endpoints)
    request_count = sum(endpoint.request_count for endpoint in endpoints)
    return MonitoringInferenceOverview(
        endpoint_count=len(endpoints),
        prediction_count=prediction_count,
        error_count=error_count,
        request_count=request_count,
        error_rate=_safe_rate(error_count, prediction_count),
        weighted_p50_latency_ms=_weighted_latency(endpoints, "p50"),
        weighted_p95_latency_ms=_weighted_latency(endpoints, "p95"),
        latency_percentiles=tuple(
            MonitoringLatencyPercentile(
                endpoint_id=endpoint.endpoint_id,
                endpoint_name=endpoint.endpoint_name,
                p50_latency_ms=endpoint.p50_latency_ms,
                p95_latency_ms=endpoint.p95_latency_ms,
                prediction_count=endpoint.prediction_count,
                latest_window_seconds=endpoint.latest_window_seconds,
            )
            for endpoint in sorted(
                endpoints,
                key=lambda endpoint: endpoint.p95_latency_ms,
                reverse=True,
            )
        ),
        error_breakdown=tuple(
            MonitoringInferenceErrorBreakdown(
                endpoint_id=endpoint.endpoint_id,
                endpoint_name=endpoint.endpoint_name,
                error_count=endpoint.error_count,
                request_count=endpoint.request_count,
                error_rate=endpoint.error_rate,
                status=endpoint.status,
            )
            for endpoint in sorted(
                endpoints,
                key=lambda endpoint: endpoint.error_rate,
                reverse=True,
            )
        ),
    )


def _weighted_latency(
    endpoints: list[InferenceEndpointMonitoringSummary],
    percentile: str,
) -> float:
    weighted_total = 0.0
    weight = 0
    for endpoint in endpoints:
        endpoint_weight = endpoint.prediction_count
        value = endpoint.p50_latency_ms if percentile == "p50" else endpoint.p95_latency_ms
        weighted_total += value * endpoint_weight
        weight += endpoint_weight
    if weight == 0:
        return 0.0
    return weighted_total / weight


def _count_rows(session: Session, statement) -> int:  # noqa: ANN001
    return int(session.scalar(statement) or 0)


def _count_training_runs(
    session: Session,
    organization_id: UUID,
    project_id: UUID,
    statuses: tuple[str, ...],
) -> int:
    return _count_rows(
        session,
        select(func.count(TrainingRunModel.id)).where(
            TrainingRunModel.organization_id == organization_id,
            TrainingRunModel.project_id == project_id,
            TrainingRunModel.status.in_(statuses),
        ),
    )


def _count_retraining_runs(
    session: Session,
    organization_id: UUID,
    project_id: UUID,
    statuses: tuple[str, ...],
) -> int:
    return _count_rows(
        session,
        select(func.count(RetrainingRunModel.id)).where(
            RetrainingRunModel.organization_id == organization_id,
            RetrainingRunModel.project_id == project_id,
            RetrainingRunModel.status.in_(statuses),
        ),
    )


def _drift_signal(report: DriftReportModel) -> MonitoringDriftSignal:
    return MonitoringDriftSignal(
        drift_report_id=report.id,
        endpoint_id=report.endpoint_id,
        deployment_id=report.deployment_id,
        status=report.status,
        drift_score=float(report.drift_score),
        drift_threshold=float(report.drift_threshold),
        drifted_feature_count=report.drifted_feature_count,
        evaluated_feature_count=report.evaluated_feature_count,
        created_at=report.created_at,
    )


def _training_failure(run: TrainingRunModel) -> MonitoringTrainingFailure:
    return MonitoringTrainingFailure(
        training_run_id=run.id,
        algorithm=run.algorithm,
        model_type=run.model_type,
        status=run.status,
        objective_metric_name=run.objective_metric_name,
        error_message=run.error_message,
        attempt_count=run.attempt_count,
        completed_at=run.completed_at,
    )


def _retraining_activity(run: RetrainingRunModel) -> MonitoringRetrainingActivity:
    return MonitoringRetrainingActivity(
        retraining_run_id=run.id,
        policy_id=run.policy_id,
        deployment_id=run.deployment_id,
        trigger_type=run.trigger_type,
        status=run.status,
        training_run_id=run.training_run_id,
        drift_report_id=run.drift_report_id,
        alert_event_id=run.alert_event_id,
        created_at=run.created_at,
    )
