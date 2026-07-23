from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.model_registry.api.schemas import (
    CreateRegisteredModelRequest,
    ModelApprovalListResponse,
    ModelApprovalResponse,
    ModelLineageListResponse,
    ModelLineageResponse,
    ModelVersionListResponse,
    ModelVersionResponse,
    RegisteredModelListResponse,
    RegisteredModelResponse,
    RegisterModelVersionRequest,
    RequestModelApprovalRequest,
    ReviewModelVersionRequest,
)
from forgeml.modules.model_registry.application.services import (
    CreateRegisteredModelCommand,
    ModelRegistryService,
    RegisterModelVersionCommand,
    RequestModelApprovalCommand,
    ReviewModelVersionCommand,
)
from forgeml.modules.model_registry.domain.entities import (
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    RegisteredModel,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyModelRegistryRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["model-registry"])


def get_model_registry_service(
    session: Session = Depends(get_db_session),
) -> ModelRegistryService:
    return ModelRegistryService(repository=SqlAlchemyModelRegistryRepository(session))


@router.post(
    "/projects/{project_id}/models",
    response_model=RegisteredModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_registered_model(
    project_id: UUID,
    request: CreateRegisteredModelRequest,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelResponse:
    model = service.create_registered_model(
        CreateRegisteredModelCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            owner_user_id=UUID(principal.user_id),
            name=request.name,
            description=request.description,
            task_type=request.task_type,
        ),
        principal,
    )
    return _registered_model_response(model)


@router.get("/projects/{project_id}/models", response_model=RegisteredModelListResponse)
def list_registered_models(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelListResponse:
    return RegisteredModelListResponse(
        items=[
            _registered_model_response(model)
            for model in service.list_registered_models(project_id, principal)
        ]
    )


@router.get("/models/{model_id}", response_model=RegisteredModelResponse)
def get_registered_model(
    model_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelResponse:
    return _registered_model_response(service.get_registered_model(model_id, principal))


@router.post(
    "/models/{model_id}/versions",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_model_version(
    model_id: UUID,
    request: RegisterModelVersionRequest,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelVersionResponse:
    version = service.register_model_version(
        RegisterModelVersionCommand(
            registered_model_id=model_id,
            training_run_id=UUID(request.training_run_id),
            model_format=request.model_format,
            signature=request.signature,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _model_version_response(version)


@router.get("/models/{model_id}/versions", response_model=ModelVersionListResponse)
def list_model_versions(
    model_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelVersionListResponse:
    return ModelVersionListResponse(
        items=[
            _model_version_response(version)
            for version in service.list_model_versions(model_id, principal)
        ]
    )


@router.get("/model-versions/{version_id}", response_model=ModelVersionResponse)
def get_model_version(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelVersionResponse:
    return _model_version_response(service.get_model_version(version_id, principal))


@router.post(
    "/model-versions/{version_id}/approval-request",
    response_model=ModelApprovalResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_model_approval(
    version_id: UUID,
    request: RequestModelApprovalRequest,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelApprovalResponse:
    approval = service.request_approval(
        RequestModelApprovalCommand(
            model_version_id=version_id,
            requested_by=UUID(principal.user_id),
            comment=request.comment,
        ),
        principal,
    )
    return _approval_response(approval)


@router.post("/model-versions/{version_id}/review", response_model=ModelApprovalResponse)
def review_model_version(
    version_id: UUID,
    request: ReviewModelVersionRequest,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelApprovalResponse:
    approval = service.review_model_version(
        ReviewModelVersionCommand(
            model_version_id=version_id,
            reviewer_id=UUID(principal.user_id),
            status=ModelApprovalStatus(request.status),
            comment=request.comment,
        ),
        principal,
    )
    return _approval_response(approval)


@router.get(
    "/model-versions/{version_id}/approvals",
    response_model=ModelApprovalListResponse,
)
def list_model_approvals(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelApprovalListResponse:
    return ModelApprovalListResponse(
        items=[
            _approval_response(approval)
            for approval in service.list_approvals(version_id, principal)
        ]
    )


@router.get("/model-versions/{version_id}/lineage", response_model=ModelLineageListResponse)
def list_model_lineage(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelLineageListResponse:
    lineage_items = service.list_lineage(version_id, principal)
    return ModelLineageListResponse(
        items=[_lineage_response(lineage) for lineage in lineage_items]
    )


def _registered_model_response(model: RegisteredModel) -> RegisteredModelResponse:
    return RegisteredModelResponse(
        id=str(model.id),
        organization_id=str(model.organization_id),
        project_id=str(model.project_id),
        name=model.name,
        slug=model.slug,
        description=model.description,
        task_type=model.task_type,
        owner_user_id=str(model.owner_user_id),
        status=model.status.value,
    )


def _model_version_response(version: ModelVersion) -> ModelVersionResponse:
    return ModelVersionResponse(
        id=str(version.id),
        registered_model_id=str(version.registered_model_id),
        version=version.version,
        training_run_id=str(version.training_run_id),
        experiment_run_id=str(version.experiment_run_id),
        artifact_uri=version.artifact_uri,
        model_format=version.model_format,
        signature=version.signature,
        metrics=version.metrics,
        status=version.status.value,
        created_by=str(version.created_by),
    )


def _approval_response(approval: ModelApproval) -> ModelApprovalResponse:
    return ModelApprovalResponse(
        id=str(approval.id),
        model_version_id=str(approval.model_version_id),
        status=approval.status.value,
        requested_by=str(approval.requested_by),
        reviewer_id=str(approval.reviewer_id) if approval.reviewer_id else None,
        comment=approval.comment,
        policy_snapshot=approval.policy_snapshot,
    )


def _lineage_response(lineage: ModelLineage) -> ModelLineageResponse:
    return ModelLineageResponse(
        id=str(lineage.id),
        model_version_id=str(lineage.model_version_id),
        source_type=lineage.source_type,
        source_id=lineage.source_id,
    )
