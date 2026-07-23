from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from forgeml.modules.alerting.domain.entities import (
    AlertEvaluation,
    AlertEvent,
    AlertEventStatus,
    AlertRule,
)
from forgeml.modules.alerting.domain.policies import (
    build_alert_message,
    build_alert_rule_slug,
    condition_matches,
    observed_metric_value,
    parse_alert_metric,
    parse_alert_operator,
    parse_alert_severity,
    validate_alert_rule_name,
    validate_alert_rule_threshold,
    validate_alert_rule_window,
)
from forgeml.modules.alerting.repositories.interfaces import AlertingRepository
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateAlertRuleCommand:
    organization_id: UUID
    project_id: UUID
    name: str
    description: str
    severity: str
    metric: str
    operator: str
    threshold: float
    window_seconds: int
    enabled: bool
    created_by: UUID


@dataclass(frozen=True)
class EvaluateAlertRuleCommand:
    alert_rule_id: UUID
    endpoint_id: UUID


class AlertingService:
    def __init__(self, *, repository: AlertingRepository) -> None:
        self._repository = repository

    def create_rule(
        self,
        command: CreateAlertRuleCommand,
        principal: Principal,
    ) -> AlertRule:
        self._require(principal, "alert_rules:create")
        self._require_same_organization(command.organization_id, principal)
        validate_alert_rule_name(command.name)
        metric = parse_alert_metric(command.metric)
        severity = parse_alert_severity(command.severity)
        operator = parse_alert_operator(command.operator)
        validate_alert_rule_threshold(metric, command.threshold)
        validate_alert_rule_window(command.window_seconds)
        slug = build_alert_rule_slug(command.name)
        if self._repository.rule_slug_exists(command.organization_id, command.project_id, slug):
            raise ConflictError("An alert rule with this name already exists in the project.")

        rule = AlertRule(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            severity=severity,
            metric=metric,
            operator=operator,
            threshold=float(command.threshold),
            window_seconds=command.window_seconds,
            enabled=command.enabled,
            created_by=command.created_by,
        )
        return self._repository.add_rule(rule)

    def list_rules(self, project_id: UUID, principal: Principal) -> list[AlertRule]:
        self._require(principal, "alert_rules:read")
        return self._repository.list_rules(UUID(principal.organization_id), project_id)

    def evaluate_rule(
        self,
        command: EvaluateAlertRuleCommand,
        principal: Principal,
    ) -> AlertEvaluation:
        self._require(principal, "alert_rules:evaluate")
        rule = self._get_scoped_rule(command.alert_rule_id, principal)
        snapshot = self._repository.get_endpoint_snapshot_reference(command.endpoint_id)
        if snapshot is None:
            raise ResourceNotFoundError("Inference endpoint metrics were not found.")
        if (
            snapshot.organization_id != rule.organization_id
            or snapshot.project_id != rule.project_id
        ):
            raise ResourceNotFoundError("Inference endpoint metrics were not found.")
        observed_value = observed_metric_value(rule, snapshot)
        if not condition_matches(rule, observed_value):
            return AlertEvaluation(
                rule_id=rule.id,
                endpoint_id=snapshot.endpoint_id,
                triggered=False,
                observed_value=observed_value,
                event=None,
            )
        open_event = self._repository.get_open_event(rule.id, snapshot.endpoint_id)
        if open_event is not None:
            return AlertEvaluation(
                rule_id=rule.id,
                endpoint_id=snapshot.endpoint_id,
                triggered=True,
                observed_value=observed_value,
                event=open_event,
            )

        event = AlertEvent(
            id=uuid4(),
            organization_id=rule.organization_id,
            project_id=rule.project_id,
            alert_rule_id=rule.id,
            endpoint_id=snapshot.endpoint_id,
            severity=rule.severity,
            status=AlertEventStatus.OPEN,
            message=build_alert_message(rule, snapshot, observed_value),
            observed_value=observed_value,
            threshold=rule.threshold,
            metadata={
                "metric": rule.metric.value,
                "operator": rule.operator.value,
                "route_path": snapshot.route_path,
                "window_seconds": snapshot.window_seconds,
            },
            acknowledged_by=None,
            resolved_by=None,
        )
        saved = self._repository.add_event(event)
        return AlertEvaluation(
            rule_id=rule.id,
            endpoint_id=snapshot.endpoint_id,
            triggered=True,
            observed_value=observed_value,
            event=saved,
        )

    def list_events(self, project_id: UUID, principal: Principal) -> list[AlertEvent]:
        self._require(principal, "alert_events:read")
        return self._repository.list_events(UUID(principal.organization_id), project_id)

    def acknowledge_event(self, event_id: UUID, principal: Principal) -> AlertEvent:
        self._require(principal, "alert_events:acknowledge")
        event = self._get_scoped_event(event_id, principal)
        updated = replace(
            event,
            status=AlertEventStatus.ACKNOWLEDGED,
            acknowledged_by=UUID(principal.user_id),
        )
        return self._repository.update_event(updated)

    def resolve_event(self, event_id: UUID, principal: Principal) -> AlertEvent:
        self._require(principal, "alert_events:resolve")
        event = self._get_scoped_event(event_id, principal)
        updated = replace(
            event,
            status=AlertEventStatus.RESOLVED,
            resolved_by=UUID(principal.user_id),
        )
        return self._repository.update_event(updated)

    def _get_scoped_rule(self, rule_id: UUID, principal: Principal) -> AlertRule:
        rule = self._repository.get_rule(rule_id)
        if rule is None or str(rule.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Alert rule was not found.")
        return rule

    def _get_scoped_event(self, event_id: UUID, principal: Principal) -> AlertEvent:
        event = self._repository.get_event(event_id)
        if event is None or str(event.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Alert event was not found.")
        return event

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage alerts.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage alerts in another organization.")
