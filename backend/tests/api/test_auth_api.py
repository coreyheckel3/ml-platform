from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.auth.api.routes import get_auth_service
from forgeml.modules.auth.application.services import AuthTokens
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


class FakeAuthService:
    def login(self, command):
        assert command.email == "ml.engineer@example.com"
        return AuthTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=900,
        )

    def refresh(self, command):
        assert command.refresh_token == "refresh-token"  # noqa: S105 - test fixture token.
        return AuthTokens(
            access_token="rotated-access-token",
            refresh_token="rotated-refresh-token",
            token_type="bearer",
            expires_in=900,
        )

    def logout(self, command):
        assert command.refresh_token == "refresh-token"  # noqa: S105 - test fixture token.
        return True


def test_login_route_returns_tokens() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ml.engineer@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "expires_in": 900,
    }


def test_refresh_route_rotates_tokens() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "rotated-access-token",
        "refresh_token": "rotated-refresh-token",
        "token_type": "bearer",
        "expires_in": 900,
    }


def test_logout_route_revokes_refresh_session() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"revoked": True}


def test_me_route_returns_current_principal() -> None:
    user_id = uuid4()
    organization_id = uuid4()
    app = create_app()
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="ml.engineer@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"projects:read"}),
    )
    client = TestClient(app)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    assert response.json()["permissions"] == ["projects:read"]
