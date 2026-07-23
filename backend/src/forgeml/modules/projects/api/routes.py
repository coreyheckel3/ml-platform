from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.projects.api.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
)
from forgeml.modules.projects.application.services import CreateProjectCommand, ProjectService
from forgeml.modules.projects.domain.entities import Project
from forgeml.modules.projects.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyProjectRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["projects"])


def get_project_service(session: Session = Depends(get_db_session)) -> ProjectService:
    return ProjectService(projects=SqlAlchemyProjectRepository(session))


def _project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        organization_id=str(project.organization_id),
        name=project.name,
        slug=project.slug,
        description=project.description,
        status=project.status.value,
        owner_user_id=str(project.owner_user_id),
    )


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    request: CreateProjectRequest,
    principal: Principal = Depends(get_current_principal),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = service.create_project(
        CreateProjectCommand(
            organization_id=UUID(principal.organization_id),
            owner_user_id=UUID(principal.user_id),
            name=request.name,
            description=request.description,
        ),
        principal,
    )
    return _project_response(project)


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    principal: Principal = Depends(get_current_principal),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    return ProjectListResponse(
        items=[_project_response(project) for project in service.list_projects(principal)]
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return _project_response(service.get_project(project_id, principal))

