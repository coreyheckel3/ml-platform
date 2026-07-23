from typing import Protocol
from uuid import UUID

from forgeml.modules.auth.domain.entities import User


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    def record_successful_login(self, user_id: UUID) -> None:
        raise NotImplementedError

