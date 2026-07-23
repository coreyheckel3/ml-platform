from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.experiments.api.schemas import (
    CompleteExperimentRunRequest,
    CreateExperimentRequest,
    ExperimentArtifactListResponse,
    ExperimentArtifactResponse,
    ExperimentListResponse,
    ExperimentResponse,
    ExperimentRunListResponse,
    ExperimentRunResponse,
    LogExperimentArtifactRequest,
    LogExperimentMetricsRequest,
    StartExperimentRunRequest,
)
from forgeml.modules.experiments.application.services import (
    CompleteExperimentRunCommand,
    CreateExperimentCommand,
    ExperimentTrackingService,
    LogExperimentArtifactCommand,
    LogExperimentMetricsCommand,
    StartExperimentRunCommand,
)
from forgeml.modules.experiments.domain.entities import (
    Experiment,
    ExperimentArtifact,
    ExperimentRun,
    ExperimentRunStatus,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyExperimentRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["experiments"])


def get_experiment_service(
    session: Session = Depends(get_db_session),
) -> ExperimentTrackingService:
    return ExperimentTrackingService(repository=SqlAlchemyExperimentRepository(session))


@router.post(
    "/projects/{project_id}/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    project_id: UUID,
    request: CreateExperimentRequest,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentResponse:
    experiment = service.create_experiment(
        CreateExperimentCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            owner_user_id=UUID(principal.user_id),
            name=request.name,
            description=request.description,
        ),
        principal,
    )
    return _experiment_response(experiment)


@router.get("/projects/{project_id}/experiments", response_model=ExperimentListResponse)
def list_experiments(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentListResponse:
    return ExperimentListResponse(
        items=[
            _experiment_response(experiment)
            for experiment in service.list_experiments(project_id, principal)
        ]
    )


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentResponse:
    return _experiment_response(service.get_experiment(experiment_id, principal))


@router.post(
    "/experiments/{experiment_id}/runs",
    response_model=ExperimentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_experiment_run(
    experiment_id: UUID,
    request: StartExperimentRunRequest,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentRunResponse:
    run = service.start_run(
        StartExperimentRunCommand(
            experiment_id=experiment_id,
            run_name=request.run_name,
            model_type=request.model_type,
            started_by=UUID(principal.user_id),
            artifact_uri=request.artifact_uri,
            dataset_version_id=(
                UUID(request.dataset_version_id) if request.dataset_version_id else None
            ),
            feature_set_id=UUID(request.feature_set_id) if request.feature_set_id else None,
            parameters=request.parameters,
        ),
        principal,
    )
    return _run_response(run)


@router.get("/experiments/{experiment_id}/runs", response_model=ExperimentRunListResponse)
def list_experiment_runs(
    experiment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentRunListResponse:
    return ExperimentRunListResponse(
        items=[_run_response(run) for run in service.list_runs(experiment_id, principal)]
    )


@router.get("/experiment-runs/{run_id}", response_model=ExperimentRunResponse)
def get_experiment_run(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentRunResponse:
    return _run_response(service.get_run(run_id, principal))


@router.post("/experiment-runs/{run_id}/metrics", response_model=ExperimentRunResponse)
def log_experiment_metrics(
    run_id: UUID,
    request: LogExperimentMetricsRequest,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentRunResponse:
    return _run_response(
        service.log_metrics(
            LogExperimentMetricsCommand(
                experiment_run_id=run_id,
                metrics=request.metrics,
                evaluation_report=request.evaluation_report,
            ),
            principal,
        )
    )


@router.post(
    "/experiment-runs/{run_id}/artifacts",
    response_model=ExperimentArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_experiment_artifact(
    run_id: UUID,
    request: LogExperimentArtifactRequest,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentArtifactResponse:
    return _artifact_response(
        service.log_artifact(
            LogExperimentArtifactCommand(
                experiment_run_id=run_id,
                name=request.name,
                artifact_type=request.artifact_type,
                uri=request.uri,
                metadata=request.metadata,
            ),
            principal,
        )
    )


@router.get(
    "/experiment-runs/{run_id}/artifacts",
    response_model=ExperimentArtifactListResponse,
)
def list_experiment_artifacts(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentArtifactListResponse:
    artifacts = service.list_artifacts(run_id, principal)
    return ExperimentArtifactListResponse(
        items=[_artifact_response(artifact) for artifact in artifacts]
    )


@router.post("/experiment-runs/{run_id}/complete", response_model=ExperimentRunResponse)
def complete_experiment_run(
    run_id: UUID,
    request: CompleteExperimentRunRequest,
    principal: Principal = Depends(get_current_principal),
    service: ExperimentTrackingService = Depends(get_experiment_service),
) -> ExperimentRunResponse:
    return _run_response(
        service.complete_run(
            CompleteExperimentRunCommand(
                experiment_run_id=run_id,
                status=ExperimentRunStatus(request.status),
                metrics=request.metrics,
                evaluation_report=request.evaluation_report,
                error_message=request.error_message,
            ),
            principal,
        )
    )


def _experiment_response(experiment: Experiment) -> ExperimentResponse:
    return ExperimentResponse(
        id=str(experiment.id),
        organization_id=str(experiment.organization_id),
        project_id=str(experiment.project_id),
        name=experiment.name,
        slug=experiment.slug,
        description=experiment.description,
        owner_user_id=str(experiment.owner_user_id),
        status=experiment.status.value,
    )


def _run_response(run: ExperimentRun) -> ExperimentRunResponse:
    return ExperimentRunResponse(
        id=str(run.id),
        experiment_id=str(run.experiment_id),
        project_id=str(run.project_id),
        run_name=run.run_name,
        status=run.status.value,
        model_type=run.model_type,
        started_by=str(run.started_by),
        dataset_version_id=str(run.dataset_version_id) if run.dataset_version_id else None,
        feature_set_id=str(run.feature_set_id) if run.feature_set_id else None,
        parameters=run.parameters,
        metrics=run.metrics,
        artifact_uri=run.artifact_uri,
        evaluation_report=run.evaluation_report,
        error_message=run.error_message,
    )


def _artifact_response(artifact: ExperimentArtifact) -> ExperimentArtifactResponse:
    return ExperimentArtifactResponse(
        id=str(artifact.id),
        experiment_run_id=str(artifact.experiment_run_id),
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        uri=artifact.uri,
        metadata=artifact.metadata,
    )
