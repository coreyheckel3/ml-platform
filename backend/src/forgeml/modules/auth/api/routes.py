from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forgeml.modules.auth.api.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from forgeml.modules.auth.application.services import (
    AuthenticationService,
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
)
from forgeml.modules.auth.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyRefreshSessionRepository,
    SqlAlchemyUserRepository,
)
from forgeml.platform.api.dependencies import (
    get_current_principal,
    get_db_session,
    get_token_signer,
)
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.security.jwt import JwtSigner
from forgeml.platform.security.passwords import PasswordHasher
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["auth"])


def get_auth_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    signer: JwtSigner = Depends(get_token_signer),
) -> AuthenticationService:
    return AuthenticationService(
        users=SqlAlchemyUserRepository(session),
        refresh_sessions=SqlAlchemyRefreshSessionRepository(session),
        password_hasher=PasswordHasher(),
        token_signer=signer,
        access_token_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    service: AuthenticationService = Depends(get_auth_service),
) -> TokenResponse:
    tokens = service.login(LoginCommand(email=request.email, password=request.password))
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshTokenRequest,
    service: AuthenticationService = Depends(get_auth_service),
) -> TokenResponse:
    tokens = service.refresh(RefreshCommand(refresh_token=request.refresh_token))
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    request: LogoutRequest,
    service: AuthenticationService = Depends(get_auth_service),
) -> LogoutResponse:
    return LogoutResponse(
        revoked=service.logout(LogoutCommand(refresh_token=request.refresh_token)),
    )


@router.get("/auth/me", response_model=CurrentUserResponse)
def me(principal: Principal = Depends(get_current_principal)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=principal.user_id,
        email=principal.email,
        organization_id=principal.organization_id,
        permissions=sorted(principal.permissions),
    )
