from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.retraining.api.schemas import (
    CreateRetrainingPolicyRequest,
    EvaluateRetrainingPolicyRequest,
    RetrainingEvaluationResponse,
    RetrainingPolicyListResponse,
    RetrainingPolicyResponse,
    RetrainingRunListResponse,
    RetrainingRunResponse,
    TriggerRetrainingRunRequest,
)
from forgeml.modules.retraining.application.services import (
    CreateRetrainingPolicyCommand,
    EvaluateRetrainingPolicyCommand,
    RetrainingService,
    TriggerRetrainingRunCommand,
)
from forgeml.modules.retraining.domain.entities import (
    RetrainingEvaluation,
    RetrainingPolicy,
    RetrainingRun,
)
from forgeml.modules.retraining.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyRetrainingRepository,
)
from forgeml.modules.retraining.infrastructure.training_launcher import TrainingRunServiceLauncher
from forgeml.modules.training.application.services import TrainingRunService
from forgeml.modules.training.infrastructure.orchestrator import LocalTrainingWorkflowOrchestrator
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRunRecorder,
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["retraining"])


def get_retraining_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RetrainingService:
    training_service = TrainingRunService(
        training_runs=SqlAlchemyTrainingRunRepository(session),
        experiment_runs=SqlAlchemyExperimentRunRecorder(session),
        orchestrator=LocalTrainingWorkflowOrchestrator(),
        artifact_bucket=settings.object_storage_bucket,
    )
    return RetrainingService(
        repository=SqlAlchemyRetrainingRepository(session),
        training_launcher=TrainingRunServiceLauncher(training_service),
    )


@router.post(
    "/projects/{project_id}/retraining-policies",
    response_model=RetrainingPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_retraining_policy(
    project_id: UUID,
    request: CreateRetrainingPolicyRequest,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingPolicyResponse:
    policy = service.create_policy(
        CreateRetrainingPolicyCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            deployment_id=UUID(request.deployment_id),
            name=request.name,
            description=request.description,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
            training_template=request.training_template,
            cooldown_seconds=request.cooldown_seconds,
            max_runs_per_day=request.max_runs_per_day,
            approval_required=request.approval_required,
            enabled=request.enabled,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _policy_response(policy)


@router.get(
    "/projects/{project_id}/retraining-policies",
    response_model=RetrainingPolicyListResponse,
)
def list_retraining_policies(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingPolicyListResponse:
    return RetrainingPolicyListResponse(
        items=[
            _policy_response(policy)
            for policy in service.list_policies(project_id, principal)
        ]
    )


@router.post(
    "/retraining-policies/{policy_id}/evaluate",
    response_model=RetrainingEvaluationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def evaluate_retraining_policy(
    policy_id: UUID,
    request: EvaluateRetrainingPolicyRequest,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingEvaluationResponse:
    return _evaluation_response(
        service.evaluate_policy(
            EvaluateRetrainingPolicyCommand(
                policy_id=policy_id,
                drift_report_id=UUID(request.drift_report_id) if request.drift_report_id else None,
                alert_event_id=UUID(request.alert_event_id) if request.alert_event_id else None,
                reason=request.reason,
            ),
            principal,
        )
    )


@router.post(
    "/retraining-policies/{policy_id}/trigger",
    response_model=RetrainingEvaluationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_retraining_run(
    policy_id: UUID,
    request: TriggerRetrainingRunRequest,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingEvaluationResponse:
    return _evaluation_response(
        service.trigger_run(
            TriggerRetrainingRunCommand(policy_id=policy_id, reason=request.reason),
            principal,
        )
    )


@router.get("/projects/{project_id}/retraining-runs", response_model=RetrainingRunListResponse)
def list_retraining_runs(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingRunListResponse:
    return RetrainingRunListResponse(
        items=[_run_response(run) for run in service.list_runs(project_id, principal)]
    )


@router.get("/retraining-runs/{run_id}", response_model=RetrainingRunResponse)
def get_retraining_run(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingRunResponse:
    return _run_response(service.get_run(run_id, principal))


@router.post("/retraining-runs/{run_id}/approve", response_model=RetrainingRunResponse)
def approve_retraining_run(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingRunResponse:
    return _run_response(service.approve_run(run_id, principal))


@router.post("/retraining-runs/{run_id}/reject", response_model=RetrainingRunResponse)
def reject_retraining_run(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: RetrainingService = Depends(get_retraining_service),
) -> RetrainingRunResponse:
    return _run_response(service.reject_run(run_id, principal))


def _policy_response(policy: RetrainingPolicy) -> RetrainingPolicyResponse:
    return RetrainingPolicyResponse(
        id=str(policy.id),
        organization_id=str(policy.organization_id),
        project_id=str(policy.project_id),
        deployment_id=str(policy.deployment_id),
        name=policy.name,
        slug=policy.slug,
        description=policy.description,
        trigger_type=policy.trigger_type.value,
        trigger_config=policy.trigger_config,
        training_template=policy.training_template,
        cooldown_seconds=policy.cooldown_seconds,
        max_runs_per_day=policy.max_runs_per_day,
        approval_required=policy.approval_required,
        enabled=policy.enabled,
        status=policy.status.value,
        created_by=str(policy.created_by),
        created_at=_datetime_response(policy.created_at),
        updated_at=_datetime_response(policy.updated_at),
    )


def _run_response(run: RetrainingRun) -> RetrainingRunResponse:
    return RetrainingRunResponse(
        id=str(run.id),
        organization_id=str(run.organization_id),
        project_id=str(run.project_id),
        policy_id=str(run.policy_id),
        deployment_id=str(run.deployment_id),
        trigger_type=run.trigger_type.value,
        drift_report_id=str(run.drift_report_id) if run.drift_report_id else None,
        alert_event_id=str(run.alert_event_id) if run.alert_event_id else None,
        training_run_id=str(run.training_run_id) if run.training_run_id else None,
        status=run.status.value,
        reason=run.reason,
        training_config=run.training_config,
        decision_metadata=run.decision_metadata,
        requested_by=str(run.requested_by),
        approved_by=str(run.approved_by) if run.approved_by else None,
        rejected_by=str(run.rejected_by) if run.rejected_by else None,
        created_at=_datetime_response(run.created_at),
        updated_at=_datetime_response(run.updated_at),
    )


def _evaluation_response(evaluation: RetrainingEvaluation) -> RetrainingEvaluationResponse:
    return RetrainingEvaluationResponse(
        policy_id=str(evaluation.policy_id),
        decision=evaluation.decision.value,
        triggered=evaluation.triggered,
        reason=evaluation.reason,
        run=_run_response(evaluation.run) if evaluation.run else None,
    )


def _datetime_response(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
