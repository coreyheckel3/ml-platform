from dataclasses import dataclass
from uuid import UUID, uuid4

from forgeml.modules.administration.domain.entities import AuditLogEvent
from forgeml.modules.administration.repositories.interfaces import AuditEventRecorder
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
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        audit_log: AuditEventRecorder | None = None,
    ) -> None:
        self._projects = projects
        self._audit_log = audit_log

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
        created = self._projects.add(project)
        self._record_project_created(created, principal)
        return created

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

    def _record_project_created(self, project: Project, principal: Principal) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record(
            AuditLogEvent(
                organization_id=project.organization_id,
                actor_type="user",
                actor_id=principal.user_id,
                action="projects.create",
                resource_type="project",
                resource_id=str(project.id),
                metadata={
                    "slug": project.slug,
                    "name": project.name,
                },
            )
        )
