from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
)
from forgeml.modules.deployments.api.schemas import (
    CreateDeploymentRequest,
    CreateDeploymentRevisionRequest,
    DeploymentCanarySimulationResponse,
    DeploymentEventListResponse,
    DeploymentEventResponse,
    DeploymentHealthCheckListResponse,
    DeploymentHealthCheckResponse,
    DeploymentListResponse,
    DeploymentResponse,
    DeploymentRevisionListResponse,
    DeploymentRevisionResponse,
    RecordDeploymentHealthRequest,
    RollbackDeploymentRequest,
    SimulateCanaryTrafficRequest,
    UpdateDeploymentTrafficRequest,
)
from forgeml.modules.deployments.application.services import (
    CreateDeploymentCommand,
    CreateDeploymentRevisionCommand,
    DeploymentService,
    ProbeDeploymentRevisionCommand,
    RecordDeploymentHealthCommand,
    RollbackDeploymentCommand,
    SimulateCanaryTrafficCommand,
    UpdateDeploymentTrafficCommand,
)
from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentCanarySimulation,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
)
from forgeml.modules.deployments.infrastructure.orchestrator import LocalDeploymentOrchestrator
from forgeml.modules.deployments.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDeploymentRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["deployments"])


def get_deployment_service(
    session: Session = Depends(get_db_session),
) -> DeploymentService:
    return DeploymentService(
        repository=SqlAlchemyDeploymentRepository(session),
        orchestrator=LocalDeploymentOrchestrator(),
        audit_log=SqlAlchemyAuditLogRepository(session),
    )


@router.post(
    "/projects/{project_id}/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deployment(
    project_id: UUID,
    request: CreateDeploymentRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentResponse:
    deployment = service.create_deployment(
        CreateDeploymentCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            name=request.name,
            description=request.description,
            environment=request.environment,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _deployment_response(deployment)


@router.get("/projects/{project_id}/deployments", response_model=DeploymentListResponse)
def list_deployments(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentListResponse:
    return DeploymentListResponse(
        items=[
            _deployment_response(deployment)
            for deployment in service.list_deployments(project_id, principal)
        ]
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentResponse:
    return _deployment_response(service.get_deployment(deployment_id, principal))


@router.post(
    "/deployments/{deployment_id}/revisions",
    response_model=DeploymentRevisionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_deployment_revision(
    deployment_id: UUID,
    request: CreateDeploymentRevisionRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentRevisionResponse:
    revision = service.create_revision(
        CreateDeploymentRevisionCommand(
            deployment_id=deployment_id,
            model_version_id=UUID(request.model_version_id),
            serving_image=request.serving_image,
            runtime_config=request.runtime_config,
            traffic_percentage=request.traffic_percentage,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _revision_response(revision)


@router.get(
    "/deployments/{deployment_id}/revisions",
    response_model=DeploymentRevisionListResponse,
)
def list_deployment_revisions(
    deployment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentRevisionListResponse:
    return DeploymentRevisionListResponse(
        items=[
            _revision_response(revision)
            for revision in service.list_revisions(deployment_id, principal)
        ]
    )


@router.post(
    "/deployment-revisions/{revision_id}/traffic",
    response_model=DeploymentRevisionResponse,
)
def update_deployment_traffic(
    revision_id: UUID,
    request: UpdateDeploymentTrafficRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentRevisionResponse:
    return _revision_response(
        service.update_traffic(
            UpdateDeploymentTrafficCommand(
                revision_id=revision_id,
                traffic_percentage=request.traffic_percentage,
            ),
            principal,
        )
    )


@router.post(
    "/deployment-revisions/{revision_id}/health-checks",
    response_model=DeploymentHealthCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_deployment_health(
    revision_id: UUID,
    request: RecordDeploymentHealthRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentHealthCheckResponse:
    return _health_check_response(
        service.record_health(
            RecordDeploymentHealthCommand(
                revision_id=revision_id,
                status=DeploymentHealthStatus(request.status),
                latency_ms=request.latency_ms,
                error_rate=request.error_rate,
                details=request.details,
            ),
            principal,
        )
    )


@router.get(
    "/deployment-revisions/{revision_id}/health-checks",
    response_model=DeploymentHealthCheckListResponse,
)
def list_deployment_health_checks(
    revision_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentHealthCheckListResponse:
    return DeploymentHealthCheckListResponse(
        items=[
            _health_check_response(health_check)
            for health_check in service.list_health_checks(revision_id, principal)
        ]
    )


@router.post(
    "/deployment-revisions/{revision_id}/health-probe",
    response_model=DeploymentHealthCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
def probe_deployment_revision_health(
    revision_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentHealthCheckResponse:
    return _health_check_response(
        service.probe_revision_health(
            ProbeDeploymentRevisionCommand(revision_id=revision_id),
            principal,
        )
    )


@router.post(
    "/deployments/{deployment_id}/rollback",
    response_model=DeploymentRevisionResponse,
)
def rollback_deployment(
    deployment_id: UUID,
    request: RollbackDeploymentRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentRevisionResponse:
    return _revision_response(
        service.rollback_deployment(
            RollbackDeploymentCommand(
                deployment_id=deployment_id,
                target_revision_id=UUID(request.target_revision_id),
            ),
            principal,
        )
    )


@router.post(
    "/deployments/{deployment_id}/canary-simulation",
    response_model=DeploymentCanarySimulationResponse,
)
def simulate_deployment_canary_traffic(
    deployment_id: UUID,
    request: SimulateCanaryTrafficRequest,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentCanarySimulationResponse:
    simulation = service.simulate_canary_traffic(
        SimulateCanaryTrafficCommand(
            deployment_id=deployment_id,
            canary_revision_id=UUID(request.canary_revision_id),
            request_count=request.request_count,
            canary_percentage=request.canary_percentage,
            routing_seed=request.routing_seed,
        ),
        principal,
    )
    return _canary_simulation_response(simulation)


@router.get("/deployments/{deployment_id}/events", response_model=DeploymentEventListResponse)
def list_deployment_events(
    deployment_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DeploymentService = Depends(get_deployment_service),
) -> DeploymentEventListResponse:
    return DeploymentEventListResponse(
        items=[_event_response(event) for event in service.list_events(deployment_id, principal)]
    )


def _deployment_response(deployment: Deployment) -> DeploymentResponse:
    return DeploymentResponse(
        id=str(deployment.id),
        organization_id=str(deployment.organization_id),
        project_id=str(deployment.project_id),
        name=deployment.name,
        slug=deployment.slug,
        description=deployment.description,
        environment=deployment.environment.value,
        status=deployment.status.value,
        created_by=str(deployment.created_by),
    )


def _revision_response(revision: DeploymentRevision) -> DeploymentRevisionResponse:
    return DeploymentRevisionResponse(
        id=str(revision.id),
        deployment_id=str(revision.deployment_id),
        model_version_id=str(revision.model_version_id),
        revision=revision.revision,
        serving_image=revision.serving_image,
        runtime_config=revision.runtime_config,
        traffic_percentage=revision.traffic_percentage,
        status=revision.status.value,
        orchestrator_deployment_id=revision.orchestrator_deployment_id,
        created_by=str(revision.created_by),
    )


def _health_check_response(health_check: DeploymentHealthCheck) -> DeploymentHealthCheckResponse:
    return DeploymentHealthCheckResponse(
        id=str(health_check.id),
        deployment_revision_id=str(health_check.deployment_revision_id),
        status=health_check.status.value,
        latency_ms=health_check.latency_ms,
        error_rate=health_check.error_rate,
        details=health_check.details,
    )


def _canary_simulation_response(
    simulation: DeploymentCanarySimulation,
) -> DeploymentCanarySimulationResponse:
    return DeploymentCanarySimulationResponse(
        deployment_id=str(simulation.deployment_id),
        canary_revision_id=str(simulation.canary_revision_id),
        request_count=simulation.request_count,
        routing_seed=simulation.routing_seed,
        allocations=[
            {
                "deployment_revision_id": str(allocation.deployment_revision_id),
                "revision": allocation.revision,
                "traffic_percentage": allocation.traffic_percentage,
                "simulated_request_count": allocation.simulated_request_count,
            }
            for allocation in simulation.allocations
        ],
        metadata=simulation.metadata,
    )


def _event_response(event: DeploymentEvent) -> DeploymentEventResponse:
    return DeploymentEventResponse(
        id=str(event.id),
        deployment_id=str(event.deployment_id),
        deployment_revision_id=(
            str(event.deployment_revision_id) if event.deployment_revision_id else None
        ),
        event_type=event.event_type,
        message=event.message,
        metadata=event.metadata,
    )
