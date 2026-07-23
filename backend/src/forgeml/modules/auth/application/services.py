from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from forgeml.modules.auth.repositories.interfaces import UserRepository
from forgeml.platform.domain.errors import AuthenticationFailedError
from forgeml.platform.security.jwt import JwtSigner
from forgeml.platform.security.passwords import PasswordHasher


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class AuthenticationService:
    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        token_signer: JwtSigner,
        access_token_ttl_seconds: int,
        refresh_token_ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._token_signer = token_signer
        self._access_token_ttl_seconds = access_token_ttl_seconds
        self._refresh_token_ttl_seconds = refresh_token_ttl_seconds
        self._clock = clock or (lambda: datetime.now(UTC))

    def login(self, command: LoginCommand) -> AuthTokens:
        email = command.email.strip().lower()
        user = self._users.get_by_email(email)
        if user is None:
            raise AuthenticationFailedError("Invalid email or password.")
        if not user.can_authenticate():
            raise AuthenticationFailedError("User account is not active.")
        if not self._password_hasher.verify(command.password, user.password_hash):
            raise AuthenticationFailedError("Invalid email or password.")

        issued_at = self._clock()
        claims = {
            "sub": str(user.id),
            "email": user.email,
            "organization_id": str(user.organization_id),
            "permissions": sorted(user.permissions),
            "auth_time": int(issued_at.timestamp()),
        }
        access_token = self._token_signer.encode(
            {**claims, "typ": "access"},
            ttl_seconds=self._access_token_ttl_seconds,
        )
        refresh_token = self._token_signer.encode(
            {"sub": str(user.id), "organization_id": str(user.organization_id), "typ": "refresh"},
            ttl_seconds=self._refresh_token_ttl_seconds,
        )
        self._users.record_successful_login(user.id)
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106 - OAuth token type, not a secret.
            expires_in=self._access_token_ttl_seconds,
        )

    def get_user(self, user_id: UUID):
        user = self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationFailedError("User no longer exists.")
        return user
