from dataclasses import dataclass
from uuid import UUID, uuid4

from forgeml.modules.projects.domain.entities import Project, ProjectStatus
from forgeml.modules.projects.domain.policies import build_project_slug, validate_project_name
from forgeml.modules.projects.repositories.interfaces import ProjectRepository
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateProjectCommand:
    organization_id: UUID
    owner_user_id: UUID
    name: str
    description: str = ""


class ProjectService:
    def __init__(self, *, projects: ProjectRepository) -> None:
        self._projects = projects

    def create_project(self, command: CreateProjectCommand, principal: Principal) -> Project:
        if not principal.has("projects:create"):
            raise PermissionDeniedError("You do not have permission to create projects.")
        if str(command.organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot create projects in another organization.")

        validate_project_name(command.name)
        slug = build_project_slug(command.name)
        if self._projects.slug_exists(command.organization_id, slug):
            raise ConflictError("A project with this name already exists.")

        project = Project(
            id=uuid4(),
            organization_id=command.organization_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            status=ProjectStatus.ACTIVE,
            owner_user_id=command.owner_user_id,
        )
        return self._projects.add(project)

    def list_projects(self, principal: Principal) -> list[Project]:
        if not principal.has("projects:read"):
            raise PermissionDeniedError("You do not have permission to list projects.")
        return self._projects.list_for_organization(UUID(principal.organization_id))

    def get_project(self, project_id: UUID, principal: Principal) -> Project:
        if not principal.has("projects:read"):
            raise PermissionDeniedError("You do not have permission to read projects.")
        project = self._projects.get(project_id)
        if project is None or str(project.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Project was not found.")
        return project
