from uuid import uuid4

import pytest

from forgeml.modules.auth.application.services import (
    AuthenticationService,
    LoginCommand,
    RefreshCommand,
)
from forgeml.modules.auth.domain.entities import RefreshSession, User, UserStatus
from forgeml.platform.domain.errors import AuthenticationFailedError
from forgeml.platform.security.jwt import JwtSigner
from forgeml.platform.security.passwords import PasswordHasher


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.recorded_login = False

    def get_by_email(self, email: str) -> User | None:
        if self.user and self.user.email == email:
            return self.user
        return None

    def get_by_id(self, user_id):
        if self.user and self.user.id == user_id:
            return self.user
        return None

    def record_successful_login(self, user_id):
        self.recorded_login = True


class FakeRefreshSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, RefreshSession] = {}
        self.replay_revocations = 0

    def add(self, session: RefreshSession) -> RefreshSession:
        self.sessions[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        return self.sessions.get(token_hash)

    def revoke(self, session_id, *, revoked_at, replaced_by_session_id=None):
        for token_hash, session in self.sessions.items():
            if session.id == session_id:
                self.sessions[token_hash] = RefreshSession(
                    id=session.id,
                    user_id=session.user_id,
                    organization_id=session.organization_id,
                    token_hash=session.token_hash,
                    issued_at=session.issued_at,
                    expires_at=session.expires_at,
                    revoked_at=revoked_at,
                    replaced_by_session_id=replaced_by_session_id,
                )
                return

    def revoke_active_for_user(self, user_id, *, revoked_at):
        revoked = 0
        self.replay_revocations += 1
        for token_hash, session in list(self.sessions.items()):
            if session.user_id == user_id and session.revoked_at is None:
                revoked += 1
                self.sessions[token_hash] = RefreshSession(
                    id=session.id,
                    user_id=session.user_id,
                    organization_id=session.organization_id,
                    token_hash=session.token_hash,
                    issued_at=session.issued_at,
                    expires_at=session.expires_at,
                    revoked_at=revoked_at,
                    replaced_by_session_id=session.replaced_by_session_id,
                )
        return revoked


def test_auth_service_issues_access_and_refresh_tokens() -> None:
    hasher = PasswordHasher()
    user = User(
        id=uuid4(),
        organization_id=uuid4(),
        email="ml.engineer@example.com",
        display_name="ML Engineer",
        password_hash=hasher.hash("correct horse battery staple"),
        status=UserStatus.ACTIVE,
        permissions=frozenset({"projects:create", "projects:read"}),
    )
    repository = FakeUserRepository(user)
    refresh_sessions = FakeRefreshSessionRepository()
    signer = JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test")
    service = AuthenticationService(
        users=repository,
        refresh_sessions=refresh_sessions,
        password_hasher=hasher,
        token_signer=signer,
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )

    tokens = service.login(
        LoginCommand(
            email="ML.Engineer@example.com",
            password="correct horse battery staple",
        )
    )
    access_claims = signer.decode(tokens.access_token)
    refresh_claims = signer.decode(tokens.refresh_token)

    assert access_claims["sub"] == str(user.id)
    assert access_claims["typ"] == "access"
    assert refresh_claims["typ"] == "refresh"
    assert refresh_claims["jti"]
    assert len(refresh_sessions.sessions) == 1
    assert repository.recorded_login


def test_auth_service_rotates_refresh_tokens_and_rejects_replay() -> None:
    hasher = PasswordHasher()
    user = User(
        id=uuid4(),
        organization_id=uuid4(),
        email="ml.engineer@example.com",
        display_name="ML Engineer",
        password_hash=hasher.hash("correct horse battery staple"),
        status=UserStatus.ACTIVE,
        permissions=frozenset({"projects:read"}),
    )
    users = FakeUserRepository(user)
    refresh_sessions = FakeRefreshSessionRepository()
    signer = JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test")
    service = AuthenticationService(
        users=users,
        refresh_sessions=refresh_sessions,
        password_hasher=hasher,
        token_signer=signer,
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )
    first = service.login(
        LoginCommand(email=user.email, password="correct horse battery staple")
    )

    second = service.refresh(RefreshCommand(refresh_token=first.refresh_token))

    assert second.refresh_token != first.refresh_token
    assert signer.decode(second.access_token)["typ"] == "access"
    assert len(refresh_sessions.sessions) == 2
    assert any(
        session.revoked_at is not None and session.replaced_by_session_id is not None
        for session in refresh_sessions.sessions.values()
    )

    with pytest.raises(AuthenticationFailedError):
        service.refresh(RefreshCommand(refresh_token=first.refresh_token))
    assert refresh_sessions.replay_revocations == 1


def test_auth_service_rejects_bad_password() -> None:
    hasher = PasswordHasher()
    user = User(
        id=uuid4(),
        organization_id=uuid4(),
        email="ml.engineer@example.com",
        display_name="ML Engineer",
        password_hash=hasher.hash("correct horse battery staple"),
        status=UserStatus.ACTIVE,
        permissions=frozenset(),
    )
    service = AuthenticationService(
        users=FakeUserRepository(user),
        refresh_sessions=FakeRefreshSessionRepository(),
        password_hasher=hasher,
        token_signer=JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test"),
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )

    with pytest.raises(AuthenticationFailedError):
        service.login(LoginCommand(email=user.email, password="not the right password"))
