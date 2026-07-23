from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.training.api.schemas import (
    RecordTrainingResultRequest,
    StartTrainingRunRequest,
    TrainingRunEventListResponse,
    TrainingRunEventResponse,
    TrainingRunListResponse,
    TrainingRunResponse,
)
from forgeml.modules.training.application.services import (
    RecordTrainingResultCommand,
    StartTrainingRunCommand,
    TrainingRunService,
)
from forgeml.modules.training.domain.entities import (
    TrainingRun,
    TrainingRunEvent,
    TrainingRunStatus,
)
from forgeml.modules.training.infrastructure.orchestrator import LocalTrainingWorkflowOrchestrator
from forgeml.modules.training.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRunRecorder,
    SqlAlchemyTrainingRunRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["training-runs"])


def get_training_run_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> TrainingRunService:
    return TrainingRunService(
        training_runs=SqlAlchemyTrainingRunRepository(session),
        experiment_runs=SqlAlchemyExperimentRunRecorder(session),
        orchestrator=LocalTrainingWorkflowOrchestrator(),
        artifact_bucket=settings.object_storage_bucket,
    )


@router.post(
    "/projects/{project_id}/training-runs",
    response_model=TrainingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_training_run(
    project_id: UUID,
    request: StartTrainingRunRequest,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    training_run = service.start_training_run(
        StartTrainingRunCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            experiment_id=UUID(request.experiment_id),
            run_name=request.run_name,
            dataset_version_id=(
                UUID(request.dataset_version_id) if request.dataset_version_id else None
            ),
            feature_set_id=UUID(request.feature_set_id) if request.feature_set_id else None,
            algorithm=request.algorithm,
            model_type=request.model_type,
            objective_metric_name=request.objective_metric_name,
            hyperparameters=request.hyperparameters,
            requested_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _training_run_response(training_run)


@router.get("/projects/{project_id}/training-runs", response_model=TrainingRunListResponse)
def list_training_runs(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunListResponse:
    return TrainingRunListResponse(
        items=[
            _training_run_response(training_run)
            for training_run in service.list_training_runs(project_id, principal)
        ]
    )


@router.get("/training-runs/{training_run_id}", response_model=TrainingRunResponse)
def get_training_run(
    training_run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    return _training_run_response(service.get_training_run(training_run_id, principal))


@router.post("/training-runs/{training_run_id}/result", response_model=TrainingRunResponse)
def record_training_result(
    training_run_id: UUID,
    request: RecordTrainingResultRequest,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    return _training_run_response(
        service.record_result(
            RecordTrainingResultCommand(
                training_run_id=training_run_id,
                status=TrainingRunStatus(request.status),
                metrics=request.metrics,
                evaluation_report=request.evaluation_report,
                error_message=request.error_message,
            ),
            principal,
        )
    )


@router.post("/training-runs/{training_run_id}/cancel", response_model=TrainingRunResponse)
def cancel_training_run(
    training_run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    return _training_run_response(service.cancel_training_run(training_run_id, principal))


@router.get(
    "/training-runs/{training_run_id}/events",
    response_model=TrainingRunEventListResponse,
)
def list_training_run_events(
    training_run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunEventListResponse:
    return TrainingRunEventListResponse(
        items=[
            _event_response(event)
            for event in service.list_events(training_run_id, principal)
        ]
    )


def _training_run_response(training_run: TrainingRun) -> TrainingRunResponse:
    return TrainingRunResponse(
        id=str(training_run.id),
        organization_id=str(training_run.organization_id),
        project_id=str(training_run.project_id),
        experiment_id=str(training_run.experiment_id),
        experiment_run_id=str(training_run.experiment_run_id),
        dataset_version_id=(
            str(training_run.dataset_version_id) if training_run.dataset_version_id else None
        ),
        feature_set_id=str(training_run.feature_set_id) if training_run.feature_set_id else None,
        algorithm=training_run.algorithm,
        model_type=training_run.model_type,
        objective_metric_name=training_run.objective_metric_name,
        hyperparameters=training_run.hyperparameters,
        status=training_run.status.value,
        requested_by=str(training_run.requested_by),
        artifact_uri=training_run.artifact_uri,
        orchestrator_run_id=training_run.orchestrator_run_id,
        metrics=training_run.metrics,
        error_message=training_run.error_message,
    )


def _event_response(event: TrainingRunEvent) -> TrainingRunEventResponse:
    return TrainingRunEventResponse(
        id=str(event.id),
        training_run_id=str(event.training_run_id),
        event_type=event.event_type,
        message=event.message,
        metadata=event.metadata,
    )
