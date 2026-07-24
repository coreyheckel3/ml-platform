from datetime import datetime
from typing import Protocol
from uuid import UUID

from forgeml.modules.auth.domain.entities import RefreshSession, User


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    def record_successful_login(self, user_id: UUID) -> None:
        raise NotImplementedError


class RefreshSessionRepository(Protocol):
    def add(self, session: RefreshSession) -> RefreshSession:
        raise NotImplementedError

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        raise NotImplementedError

    def revoke(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by_session_id: UUID | None = None,
    ) -> None:
        raise NotImplementedError

    def revoke_active_for_user(self, user_id: UUID, *, revoked_at: datetime) -> int:
        raise NotImplementedError
