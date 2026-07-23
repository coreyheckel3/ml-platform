from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.auth.domain.entities import User, UserStatus
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel


def _to_domain(model: UserModel) -> User:
    permissions = frozenset(
        permission for permission in model.permissions_csv.split(",") if permission
    )
    return User(
        id=model.id,
        organization_id=model.organization_id,
        email=model.email,
        display_name=model.display_name,
        password_hash=model.password_hash,
        status=UserStatus(model.status),
        permissions=permissions,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_domain(model) if model else None

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_domain(model) if model else None

    def record_successful_login(self, user_id: UUID) -> None:
        model = self._session.get(UserModel, user_id)
        if model is not None:
            model.last_login_at = datetime.now(UTC)

