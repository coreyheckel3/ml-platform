from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.domain.entities import RefreshSession
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.auth.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyRefreshSessionRepository,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import OrganizationModel
from forgeml.platform.database.base import Base


def test_refresh_session_repository_persists_rotation_and_user_revocation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    user_id = uuid4()
    first_session_id = uuid4()
    replacement_session_id = uuid4()
    now = datetime.now(UTC)

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            UserModel(
                id=user_id,
                organization_id=organization_id,
                email="owner@example.com",
                display_name="Owner",
                password_hash="hash",
                permissions_csv="*",
            )
        )
        repository = SqlAlchemyRefreshSessionRepository(session)
        first = repository.add(
            RefreshSession(
                id=first_session_id,
                user_id=user_id,
                organization_id=organization_id,
                token_hash="a" * 64,
                issued_at=now,
                expires_at=now + timedelta(days=1),
            )
        )
        replacement = repository.add(
            RefreshSession(
                id=replacement_session_id,
                user_id=user_id,
                organization_id=organization_id,
                token_hash="b" * 64,
                issued_at=now,
                expires_at=now + timedelta(days=1),
            )
        )
        repository.revoke(
            first.id,
            revoked_at=now,
            replaced_by_session_id=replacement.id,
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyRefreshSessionRepository(session)
        loaded = repository.get_by_token_hash("a" * 64)
        assert loaded is not None
        assert loaded.revoked_at == now
        assert loaded.replaced_by_session_id == replacement_session_id
        revoked_count = repository.revoke_active_for_user(user_id, revoked_at=now)
        session.commit()

    assert revoked_count == 1
