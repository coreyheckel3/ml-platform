from collections.abc import Generator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from forgeml.platform.config import Settings, get_settings
from forgeml.platform.database.session import get_session
from forgeml.platform.domain.errors import AuthenticationFailedError
from forgeml.platform.security.jwt import JwtSigner, TokenError
from forgeml.platform.security.rbac import Principal

bearer_scheme = HTTPBearer(auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_token_signer(settings: Settings = Depends(get_settings)) -> JwtSigner:
    return JwtSigner(secret=settings.jwt_secret, issuer=settings.jwt_issuer)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    signer: JwtSigner = Depends(get_token_signer),
) -> Principal:
    if credentials is None:
        raise AuthenticationFailedError("Missing bearer token.")
    try:
        claims = signer.decode(credentials.credentials)
    except TokenError as exc:
        raise AuthenticationFailedError("Invalid bearer token.") from exc

    if claims.get("typ") != "access":
        raise AuthenticationFailedError("Bearer token is not an access token.")

    return Principal(
        user_id=str(claims["sub"]),
        email=str(claims["email"]),
        organization_id=str(claims["organization_id"]),
        permissions=frozenset(str(permission) for permission in claims.get("permissions", [])),
    )
