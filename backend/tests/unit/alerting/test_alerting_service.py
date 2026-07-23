from uuid import UUID, uuid4

import pytest

from forgeml.modules.alerting.application.services import (
    AlertingService,
    CreateAlertRuleCommand,
    EvaluateAlertRuleCommand,
)
from forgeml.modules.alerting.domain.entities import (
    AlertEvent,
    AlertEventStatus,
    AlertRule,
    EndpointMetricSnapshotReference,
)
from forgeml.platform.domain.errors import ConflictError
from forgeml.platform.security.rbac import Principal


class FakeAlertingRepository:
    def __init__(self) -> None:
        self.rules: dict[UUID, AlertRule] = {}
        self.events: dict[UUID, AlertEvent] = {}
        self.snapshots: dict[UUID, EndpointMetricSnapshotReference] = {}

    def add_rule(self, rule: AlertRule) -> AlertRule:
        self.rules[rule.id] = rule
        return rule

    def get_rule(self, rule_id: UUID) -> AlertRule | None:
        return self.rules.get(rule_id)

    def list_rules(self, organization_id: UUID, project_id: UUID) -> list[AlertRule]:
        return [
            rule
            for rule in self.rules.values()
            if rule.organization_id == organization_id and rule.project_id == project_id
        ]

    def rule_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return any(
            rule.organization_id == organization_id
            and rule.project_id == project_id
            and rule.slug == slug
            for rule in self.rules.values()
        )

    def add_event(self, event: AlertEvent) -> AlertEvent:
        self.events[event.id] = event
        return event

    def get_event(self, event_id: UUID) -> AlertEvent | None:
        return self.events.get(event_id)

    def get_open_event(self, rule_id: UUID, endpoint_id: UUID) -> AlertEvent | None:
        for event in self.events.values():
            if event.alert_rule_id != rule_id or event.endpoint_id != endpoint_id:
                continue
            if event.status in {AlertEventStatus.OPEN, AlertEventStatus.ACKNOWLEDGED}:
                return event
        return None

    def list_events(self, organization_id: UUID, project_id: UUID) -> list[AlertEvent]:
        return [
            event
            for event in self.events.values()
            if event.organization_id == organization_id and event.project_id == project_id
        ]

    def update_event(self, event: AlertEvent) -> AlertEvent:
        self.events[event.id] = event
        return event

    def get_endpoint_snapshot_reference(
        self,
        endpoint_id: UUID,
    ) -> EndpointMetricSnapshotReference | None:
        return self.snapshots.get(endpoint_id)


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_alerting_service_creates_rule_evaluates_and_dedupes_event() -> None:
    repository = FakeAlertingRepository()
    service = AlertingService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    endpoint_id = uuid4()
    repository.snapshots[endpoint_id] = _snapshot(
        endpoint_id=endpoint_id,
        organization_id=organization_id,
        project_id=project_id,
        prediction_count=1000,
        error_count=45,
    )
    actor = principal(
        organization_id,
        user_id,
        {
            "alert_rules:create",
            "alert_rules:read",
            "alert_rules:evaluate",
            "alert_events:read",
            "alert_events:acknowledge",
            "alert_events:resolve",
        },
    )

    rule = service.create_rule(
        CreateAlertRuleCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Error Rate",
            description="Error budget alert.",
            severity="critical",
            metric="inference_error_rate",
            operator="gt",
            threshold=0.02,
            window_seconds=300,
            enabled=True,
            created_by=user_id,
        ),
        actor,
    )
    evaluation = service.evaluate_rule(
        EvaluateAlertRuleCommand(alert_rule_id=rule.id, endpoint_id=endpoint_id),
        actor,
    )
    duplicate_evaluation = service.evaluate_rule(
        EvaluateAlertRuleCommand(alert_rule_id=rule.id, endpoint_id=endpoint_id),
        actor,
    )
    acknowledged = service.acknowledge_event(evaluation.event.id, actor)  # type: ignore[union-attr]
    resolved = service.resolve_event(acknowledged.id, actor)

    assert rule.slug == "fraud-error-rate"
    assert evaluation.triggered
    assert evaluation.event is not None
    assert duplicate_evaluation.event is not None
    assert duplicate_evaluation.event.id == evaluation.event.id
    assert acknowledged.status == AlertEventStatus.ACKNOWLEDGED
    assert resolved.status == AlertEventStatus.RESOLVED
    assert resolved.resolved_by == user_id


def test_alerting_service_rejects_duplicate_rule_slug() -> None:
    repository = FakeAlertingRepository()
    service = AlertingService(repository=repository)
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"alert_rules:create"})
    command = CreateAlertRuleCommand(
        organization_id=organization_id,
        project_id=project_id,
        name="Fraud Error Rate",
        description="",
        severity="warning",
        metric="inference_error_rate",
        operator="gt",
        threshold=0.02,
        window_seconds=300,
        enabled=True,
        created_by=user_id,
    )

    service.create_rule(command, actor)

    with pytest.raises(ConflictError):
        service.create_rule(command, actor)


def _snapshot(
    *,
    endpoint_id: UUID,
    organization_id: UUID,
    project_id: UUID,
    prediction_count: int,
    error_count: int,
) -> EndpointMetricSnapshotReference:
    return EndpointMetricSnapshotReference(
        endpoint_id=endpoint_id,
        organization_id=organization_id,
        project_id=project_id,
        endpoint_name="Fraud Risk Online",
        route_path="/inference/fraud-risk-online",
        window_seconds=300,
        prediction_count=prediction_count,
        error_count=error_count,
        p50_latency_ms=18.2,
        p95_latency_ms=46.8,
    )
