from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from forgeml.modules.auth.domain.entities import RefreshSession, User, UserStatus
from forgeml.modules.auth.infrastructure.sqlalchemy_models import RefreshSessionModel, UserModel


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


class SqlAlchemyRefreshSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session: RefreshSession) -> RefreshSession:
        model = RefreshSessionModel(
            id=session.id,
            user_id=session.user_id,
            organization_id=session.organization_id,
            token_hash=session.token_hash,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            replaced_by_session_id=session.replaced_by_session_id,
        )
        self._session.add(model)
        self._session.flush()
        return _refresh_session_to_domain(model)

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        model = self._session.scalar(
            select(RefreshSessionModel).where(RefreshSessionModel.token_hash == token_hash)
        )
        return _refresh_session_to_domain(model) if model else None

    def revoke(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by_session_id: UUID | None = None,
    ) -> None:
        model = self._session.get(RefreshSessionModel, session_id)
        if model is None:
            return
        model.revoked_at = revoked_at
        model.replaced_by_session_id = replaced_by_session_id
        self._session.flush()

    def revoke_active_for_user(self, user_id: UUID, *, revoked_at: datetime) -> int:
        result = self._session.execute(
            update(RefreshSessionModel)
            .where(
                RefreshSessionModel.user_id == user_id,
                RefreshSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        self._session.flush()
        return int(result.rowcount or 0)


def _refresh_session_to_domain(model: RefreshSessionModel) -> RefreshSession:
    return RefreshSession(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        token_hash=model.token_hash,
        issued_at=_ensure_utc(model.issued_at),
        expires_at=_ensure_utc(model.expires_at),
        revoked_at=_ensure_utc(model.revoked_at) if model.revoked_at else None,
        replaced_by_session_id=model.replaced_by_session_id,
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
