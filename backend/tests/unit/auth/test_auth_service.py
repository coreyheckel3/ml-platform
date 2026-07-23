from uuid import uuid4

import pytest

from forgeml.modules.auth.application.services import AuthenticationService, LoginCommand
from forgeml.modules.auth.domain.entities import User, UserStatus
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
    signer = JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test")
    service = AuthenticationService(
        users=repository,
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
    assert repository.recorded_login


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
        password_hasher=hasher,
        token_signer=JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test"),
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )

    with pytest.raises(AuthenticationFailedError):
        service.login(LoginCommand(email=user.email, password="not the right password"))
