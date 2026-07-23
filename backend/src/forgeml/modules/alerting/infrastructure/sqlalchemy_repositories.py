from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.alerting.domain.entities import (
    AlertEvent,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertRule,
    AlertSeverity,
    EndpointMetricSnapshotReference,
)
from forgeml.modules.alerting.infrastructure.sqlalchemy_models import (
    AlertEventModel,
    AlertRuleModel,
)
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
)


class SqlAlchemyAlertingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_rule(self, rule: AlertRule) -> AlertRule:
        model = AlertRuleModel(
            id=rule.id,
            organization_id=rule.organization_id,
            project_id=rule.project_id,
            name=rule.name,
            slug=rule.slug,
            description=rule.description,
            severity=rule.severity.value,
            metric=rule.metric.value,
            operator=rule.operator.value,
            threshold=rule.threshold,
            window_seconds=rule.window_seconds,
            enabled=rule.enabled,
            created_by=rule.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _rule_to_domain(model)

    def get_rule(self, rule_id: UUID) -> AlertRule | None:
        model = self._session.get(AlertRuleModel, rule_id)
        return _rule_to_domain(model) if model else None

    def list_rules(self, organization_id: UUID, project_id: UUID) -> list[AlertRule]:
        models = self._session.scalars(
            select(AlertRuleModel)
            .where(
                AlertRuleModel.organization_id == organization_id,
                AlertRuleModel.project_id == project_id,
            )
            .order_by(AlertRuleModel.name)
        ).all()
        return [_rule_to_domain(model) for model in models]

    def rule_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(AlertRuleModel.id).where(
                    AlertRuleModel.organization_id == organization_id,
                    AlertRuleModel.project_id == project_id,
                    AlertRuleModel.slug == slug,
                )
            )
            is not None
        )

    def add_event(self, event: AlertEvent) -> AlertEvent:
        model = AlertEventModel(
            id=event.id,
            organization_id=event.organization_id,
            project_id=event.project_id,
            alert_rule_id=event.alert_rule_id,
            endpoint_id=event.endpoint_id,
            severity=event.severity.value,
            status=event.status.value,
            message=event.message,
            observed_value=event.observed_value,
            threshold=event.threshold,
            metadata_json=event.metadata,
            acknowledged_by=event.acknowledged_by,
            resolved_by=event.resolved_by,
        )
        self._session.add(model)
        self._session.flush()
        return _event_to_domain(model)

    def get_event(self, event_id: UUID) -> AlertEvent | None:
        model = self._session.get(AlertEventModel, event_id)
        return _event_to_domain(model) if model else None

    def get_open_event(self, rule_id: UUID, endpoint_id: UUID) -> AlertEvent | None:
        model = self._session.scalars(
            select(AlertEventModel)
            .where(
                AlertEventModel.alert_rule_id == rule_id,
                AlertEventModel.endpoint_id == endpoint_id,
                AlertEventModel.status.in_(("open", "acknowledged")),
            )
            .order_by(AlertEventModel.triggered_at.desc())
        ).first()
        return _event_to_domain(model) if model else None

    def list_events(self, organization_id: UUID, project_id: UUID) -> list[AlertEvent]:
        models = self._session.scalars(
            select(AlertEventModel)
            .where(
                AlertEventModel.organization_id == organization_id,
                AlertEventModel.project_id == project_id,
            )
            .order_by(AlertEventModel.triggered_at.desc())
        ).all()
        return [_event_to_domain(model) for model in models]

    def update_event(self, event: AlertEvent) -> AlertEvent:
        model = self._session.get(AlertEventModel, event.id)
        if model is None:
            raise ValueError("Alert event does not exist.")
        model.status = event.status.value
        model.acknowledged_by = event.acknowledged_by
        model.resolved_by = event.resolved_by
        now = datetime.now(tz=UTC)
        if event.status == AlertEventStatus.ACKNOWLEDGED and model.acknowledged_at is None:
            model.acknowledged_at = now
        if event.status == AlertEventStatus.RESOLVED and model.resolved_at is None:
            model.resolved_at = now
        self._session.flush()
        return _event_to_domain(model)

    def get_endpoint_snapshot_reference(
        self,
        endpoint_id: UUID,
    ) -> EndpointMetricSnapshotReference | None:
        endpoint = self._session.get(InferenceEndpointModel, endpoint_id)
        if endpoint is None:
            return None
        snapshot = self._session.scalars(
            select(InferenceMetricSnapshotModel)
            .where(InferenceMetricSnapshotModel.endpoint_id == endpoint_id)
            .order_by(InferenceMetricSnapshotModel.created_at.desc())
        ).first()
        if snapshot is None:
            return None
        return EndpointMetricSnapshotReference(
            endpoint_id=endpoint.id,
            organization_id=endpoint.organization_id,
            project_id=endpoint.project_id,
            endpoint_name=endpoint.name,
            route_path=endpoint.route_path,
            window_seconds=snapshot.window_seconds,
            prediction_count=snapshot.prediction_count,
            error_count=snapshot.error_count,
            p50_latency_ms=float(snapshot.p50_latency_ms),
            p95_latency_ms=float(snapshot.p95_latency_ms),
        )


def _rule_to_domain(model: AlertRuleModel) -> AlertRule:
    return AlertRule(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        severity=AlertSeverity(model.severity),
        metric=AlertMetric(model.metric),
        operator=AlertOperator(model.operator),
        threshold=float(model.threshold),
        window_seconds=model.window_seconds,
        enabled=model.enabled,
        created_by=model.created_by,
    )


def _event_to_domain(model: AlertEventModel) -> AlertEvent:
    return AlertEvent(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        alert_rule_id=model.alert_rule_id,
        endpoint_id=model.endpoint_id,
        severity=AlertSeverity(model.severity),
        status=AlertEventStatus(model.status),
        message=model.message,
        observed_value=float(model.observed_value),
        threshold=float(model.threshold),
        metadata=model.metadata_json,
        acknowledged_by=model.acknowledged_by,
        resolved_by=model.resolved_by,
    )
