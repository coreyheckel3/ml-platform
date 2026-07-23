from typing import Protocol
from uuid import UUID

from forgeml.modules.projects.domain.entities import Project


class ProjectRepository(Protocol):
    def add(self, project: Project) -> Project:
        raise NotImplementedError

    def get(self, project_id: UUID) -> Project | None:
        raise NotImplementedError

    def list_for_organization(self, organization_id: UUID) -> list[Project]:
        raise NotImplementedError

    def slug_exists(self, organization_id: UUID, slug: str) -> bool:
        raise NotImplementedError

