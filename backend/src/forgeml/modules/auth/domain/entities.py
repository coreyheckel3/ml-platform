from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class RefreshSession:
    id: UUID
    user_id: UUID
    organization_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_session_id: UUID | None = None

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now
