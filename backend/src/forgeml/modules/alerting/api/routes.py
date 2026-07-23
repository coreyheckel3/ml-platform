from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.alerting.api.schemas import (
    AlertEvaluationResponse,
    AlertEventListResponse,
    AlertEventResponse,
    AlertRuleListResponse,
    AlertRuleResponse,
    CreateAlertRuleRequest,
    EvaluateAlertRuleRequest,
)
from forgeml.modules.alerting.application.services import (
    AlertingService,
    CreateAlertRuleCommand,
    EvaluateAlertRuleCommand,
)
from forgeml.modules.alerting.domain.entities import AlertEvaluation, AlertEvent, AlertRule
from forgeml.modules.alerting.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAlertingRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["alerting"])


def get_alerting_service(
    session: Session = Depends(get_db_session),
) -> AlertingService:
    return AlertingService(repository=SqlAlchemyAlertingRepository(session))


@router.post(
    "/projects/{project_id}/alert-rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_rule(
    project_id: UUID,
    request: CreateAlertRuleRequest,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertRuleResponse:
    rule = service.create_rule(
        CreateAlertRuleCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            name=request.name,
            description=request.description,
            severity=request.severity,
            metric=request.metric,
            operator=request.operator,
            threshold=request.threshold,
            window_seconds=request.window_seconds,
            enabled=request.enabled,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _rule_response(rule)


@router.get("/projects/{project_id}/alert-rules", response_model=AlertRuleListResponse)
def list_alert_rules(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertRuleListResponse:
    return AlertRuleListResponse(
        items=[_rule_response(rule) for rule in service.list_rules(project_id, principal)]
    )


@router.post("/alert-rules/{rule_id}/evaluate", response_model=AlertEvaluationResponse)
def evaluate_alert_rule(
    rule_id: UUID,
    request: EvaluateAlertRuleRequest,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertEvaluationResponse:
    evaluation = service.evaluate_rule(
        EvaluateAlertRuleCommand(
            alert_rule_id=rule_id,
            endpoint_id=UUID(request.endpoint_id),
        ),
        principal,
    )
    return _evaluation_response(evaluation)


@router.get("/projects/{project_id}/alert-events", response_model=AlertEventListResponse)
def list_alert_events(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertEventListResponse:
    return AlertEventListResponse(
        items=[_event_response(event) for event in service.list_events(project_id, principal)]
    )


@router.post("/alert-events/{event_id}/acknowledge", response_model=AlertEventResponse)
def acknowledge_alert_event(
    event_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertEventResponse:
    return _event_response(service.acknowledge_event(event_id, principal))


@router.post("/alert-events/{event_id}/resolve", response_model=AlertEventResponse)
def resolve_alert_event(
    event_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: AlertingService = Depends(get_alerting_service),
) -> AlertEventResponse:
    return _event_response(service.resolve_event(event_id, principal))


def _rule_response(rule: AlertRule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=str(rule.id),
        organization_id=str(rule.organization_id),
        project_id=str(rule.project_id),
        name=rule.name,
        slug=rule.slug,
        description=rule.description,
        severity=rule.severity.value,
        metric=rule.metric.value,
        operator=rule.operator.value,
        threshold=rule.threshold,
        window_seconds=rule.window_seconds,
        enabled=rule.enabled,
        created_by=str(rule.created_by),
    )


def _event_response(event: AlertEvent) -> AlertEventResponse:
    return AlertEventResponse(
        id=str(event.id),
        organization_id=str(event.organization_id),
        project_id=str(event.project_id),
        alert_rule_id=str(event.alert_rule_id),
        endpoint_id=str(event.endpoint_id) if event.endpoint_id else None,
        severity=event.severity.value,
        status=event.status.value,
        message=event.message,
        observed_value=event.observed_value,
        threshold=event.threshold,
        metadata=event.metadata,
        acknowledged_by=str(event.acknowledged_by) if event.acknowledged_by else None,
        resolved_by=str(event.resolved_by) if event.resolved_by else None,
    )


def _evaluation_response(evaluation: AlertEvaluation) -> AlertEvaluationResponse:
    return AlertEvaluationResponse(
        rule_id=str(evaluation.rule_id),
        endpoint_id=str(evaluation.endpoint_id),
        triggered=evaluation.triggered,
        observed_value=evaluation.observed_value,
        event=_event_response(evaluation.event) if evaluation.event else None,
    )
