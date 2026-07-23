from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class Project:
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str
    status: ProjectStatus
    owner_user_id: UUID

    def is_active(self) -> bool:
        return self.status == ProjectStatus.ACTIVE

