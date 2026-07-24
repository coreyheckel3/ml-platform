from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from forgeml.modules.auth.domain.entities import RefreshSession, User
from forgeml.modules.auth.repositories.interfaces import RefreshSessionRepository, UserRepository
from forgeml.platform.domain.errors import AuthenticationFailedError
from forgeml.platform.security.jwt import JwtSigner, TokenError
from forgeml.platform.security.passwords import PasswordHasher


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class RefreshCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str


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
        refresh_sessions: RefreshSessionRepository,
        password_hasher: PasswordHasher,
        token_signer: JwtSigner,
        access_token_ttl_seconds: int,
        refresh_token_ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._refresh_sessions = refresh_sessions
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
        tokens, refresh_session = self._issue_token_pair(user, issued_at=issued_at)
        self._refresh_sessions.add(refresh_session)
        self._users.record_successful_login(user.id)
        return tokens

    def refresh(self, command: RefreshCommand) -> AuthTokens:
        claims = self._decode_refresh_token(command.refresh_token)
        token_hash = _hash_token(command.refresh_token)
        stored_session = self._refresh_sessions.get_by_token_hash(token_hash)
        now = self._clock()
        if stored_session is None:
            raise AuthenticationFailedError("Refresh token is not recognized.")
        if stored_session.revoked_at is not None:
            self._refresh_sessions.revoke_active_for_user(stored_session.user_id, revoked_at=now)
            raise AuthenticationFailedError("Refresh token has already been used or revoked.")
        if not stored_session.is_active(now):
            raise AuthenticationFailedError("Refresh token has expired.")

        subject = _claim_uuid(claims, "sub")
        token_session_id = _claim_uuid(claims, "jti")
        if subject != stored_session.user_id or token_session_id != stored_session.id:
            raise AuthenticationFailedError("Refresh token session does not match stored state.")

        user = self._users.get_by_id(stored_session.user_id)
        if user is None or not user.can_authenticate():
            raise AuthenticationFailedError("User account is not active.")
        if str(user.organization_id) != str(claims.get("organization_id")):
            raise AuthenticationFailedError("Refresh token organization does not match user.")

        tokens, replacement = self._issue_token_pair(user, issued_at=now)
        self._refresh_sessions.add(replacement)
        self._refresh_sessions.revoke(
            stored_session.id,
            revoked_at=now,
            replaced_by_session_id=replacement.id,
        )
        return tokens

    def logout(self, command: LogoutCommand) -> bool:
        stored_session = self._refresh_sessions.get_by_token_hash(
            _hash_token(command.refresh_token)
        )
        if stored_session is None or stored_session.revoked_at is not None:
            return False
        self._refresh_sessions.revoke(stored_session.id, revoked_at=self._clock())
        return True

    def get_user(self, user_id: UUID):
        user = self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationFailedError("User no longer exists.")
        return user

    def _issue_token_pair(
        self,
        user: User,
        *,
        issued_at: datetime,
    ) -> tuple[AuthTokens, RefreshSession]:
        access_token = self._token_signer.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "organization_id": str(user.organization_id),
                "permissions": sorted(user.permissions),
                "auth_time": int(issued_at.timestamp()),
                "typ": "access",
                "jti": str(uuid4()),
            },
            ttl_seconds=self._access_token_ttl_seconds,
        )
        refresh_session_id = uuid4()
        refresh_token = self._token_signer.encode(
            {
                "sub": str(user.id),
                "organization_id": str(user.organization_id),
                "typ": "refresh",
                "jti": str(refresh_session_id),
            },
            ttl_seconds=self._refresh_token_ttl_seconds,
        )
        refresh_session = RefreshSession(
            id=refresh_session_id,
            user_id=user.id,
            organization_id=user.organization_id,
            token_hash=_hash_token(refresh_token),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=self._refresh_token_ttl_seconds),
        )
        return (
            AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",  # noqa: S106 - OAuth token type, not a secret.
                expires_in=self._access_token_ttl_seconds,
            ),
            refresh_session,
        )

    def _decode_refresh_token(self, refresh_token: str) -> dict[str, object]:
        try:
            claims = self._token_signer.decode(refresh_token)
        except TokenError as exc:
            raise AuthenticationFailedError("Invalid refresh token.") from exc
        if claims.get("typ") != "refresh":
            raise AuthenticationFailedError("Token is not a refresh token.")
        return claims


def _hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def _claim_uuid(claims: dict[str, object], key: str) -> UUID:
    try:
        return UUID(str(claims[key]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationFailedError(
            "Refresh token is missing required session claims."
        ) from exc
