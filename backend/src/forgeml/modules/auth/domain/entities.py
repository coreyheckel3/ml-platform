from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True)
class User:
    id: UUID
    organization_id: UUID
    email: str
    display_name: str
    password_hash: str
    status: UserStatus
    permissions: frozenset[str]

    def can_authenticate(self) -> bool:
        return self.status == UserStatus.ACTIVE

