from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.alerting.api.routes import get_alerting_service
from forgeml.modules.alerting.domain.entities import (
    AlertEvaluation,
    AlertEvent,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertRule,
    AlertSeverity,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeAlertingService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    rule_id: UUID
    endpoint_id: UUID
    event_id: UUID

    def create_rule(self, command, principal):
        assert command.name == "Fraud Error Rate"
        assert command.threshold == 0.02
        return self._rule()

    def list_rules(self, project_id, principal):
        assert project_id == self.project_id
        return [self._rule()]

    def evaluate_rule(self, command, principal):
        assert command.endpoint_id == self.endpoint_id
        return AlertEvaluation(
            rule_id=self.rule_id,
            endpoint_id=self.endpoint_id,
            triggered=True,
            observed_value=0.035,
            event=self._event(AlertEventStatus.OPEN),
        )

    def list_events(self, project_id, principal):
        assert project_id == self.project_id
        return [self._event(AlertEventStatus.OPEN)]

    def acknowledge_event(self, event_id, principal):
        assert event_id == self.event_id
        return self._event(AlertEventStatus.ACKNOWLEDGED)

    def resolve_event(self, event_id, principal):
        assert event_id == self.event_id
        return self._event(AlertEventStatus.RESOLVED)

    def _rule(self) -> AlertRule:
        return AlertRule(
            id=self.rule_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Error Rate",
            slug="fraud-error-rate",
            description="Error budget alert.",
            severity=AlertSeverity.CRITICAL,
            metric=AlertMetric.INFERENCE_ERROR_RATE,
            operator=AlertOperator.GREATER_THAN,
            threshold=0.02,
            window_seconds=300,
            enabled=True,
            created_by=self.user_id,
        )

    def _event(self, status: AlertEventStatus) -> AlertEvent:
        return AlertEvent(
            id=self.event_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            alert_rule_id=self.rule_id,
            endpoint_id=self.endpoint_id,
            severity=AlertSeverity.CRITICAL,
            status=status,
            message="Fraud Error Rate triggered.",
            observed_value=0.035,
            threshold=0.02,
            metadata={"metric": "inference_error_rate"},
            acknowledged_by=self.user_id if status == AlertEventStatus.ACKNOWLEDGED else None,
            resolved_by=self.user_id if status == AlertEventStatus.RESOLVED else None,
        )


def test_alerting_routes_expose_rule_event_and_evaluation_lifecycle() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = FakeAlertingService(
        organization_id=organization_id,
        project_id=uuid4(),
        user_id=user_id,
        rule_id=uuid4(),
        endpoint_id=uuid4(),
        event_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_alerting_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{service.project_id}/alert-rules",
        json={
            "name": "Fraud Error Rate",
            "description": "Error budget alert.",
            "severity": "critical",
            "metric": "inference_error_rate",
            "operator": "gt",
            "threshold": 0.02,
            "window_seconds": 300,
            "enabled": True,
        },
    )
    rules = client.get(f"/api/v1/projects/{service.project_id}/alert-rules")
    evaluation = client.post(
        f"/api/v1/alert-rules/{service.rule_id}/evaluate",
        json={"endpoint_id": str(service.endpoint_id)},
    )
    events = client.get(f"/api/v1/projects/{service.project_id}/alert-events")
    acknowledged = client.post(f"/api/v1/alert-events/{service.event_id}/acknowledge")
    resolved = client.post(f"/api/v1/alert-events/{service.event_id}/resolve")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-error-rate"
    assert rules.status_code == 200
    assert rules.json()["items"][0]["metric"] == "inference_error_rate"
    assert evaluation.status_code == 200
    assert evaluation.json()["triggered"]
    assert events.status_code == 200
    assert events.json()["items"][0]["status"] == "open"
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
