from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.administration.api.routes import get_administration_service
from forgeml.modules.administration.application.services import ListAuditLogQuery
from forgeml.modules.administration.domain.entities import AuditLogEntry
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


class FakeAdministrationService:
    def __init__(self) -> None:
        self.organization_id = uuid4()
        self.entry_id = uuid4()
        self.query: ListAuditLogQuery | None = None

    def list_audit_log(
        self,
        query: ListAuditLogQuery,
        principal: Principal,
    ) -> list[AuditLogEntry]:
        self.query = query
        return [
            AuditLogEntry(
                id=self.entry_id,
                organization_id=self.organization_id,
                actor_type="user",
                actor_id="user-1",
                action="model_versions.review",
                resource_type="model_version",
                resource_id="model-version-1",
                metadata={"decision": "approved"},
                created_at=datetime(2026, 7, 26, 12, 30, tzinfo=UTC),
            )
        ]


def test_administration_audit_log_route_uses_application_service_contract() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:audit_log:read"}),
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/audit-log",
        params={
            "actor_type": "user",
            "action": "model_versions.review",
            "resource_type": "model_version",
            "limit": 25,
        },
    )

    assert response.status_code == 200
    assert fake_service.query == ListAuditLogQuery(
        organization_id=fake_service.organization_id,
        actor_type="user",
        action="model_versions.review",
        resource_type="model_version",
        limit=25,
    )
    assert response.json() == {
        "items": [
            {
                "id": str(fake_service.entry_id),
                "organization_id": str(fake_service.organization_id),
                "actor_type": "user",
                "actor_id": "user-1",
                "action": "model_versions.review",
                "resource_type": "model_version",
                "resource_id": "model-version-1",
                "metadata": {"decision": "approved"},
                "created_at": "2026-07-26T12:30:00+00:00",
            }
        ],
        "next_cursor": None,
    }


def test_administration_audit_log_route_validates_limit() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:audit_log:read"}),
    )
    client = TestClient(app)

    response = client.get("/api/v1/admin/audit-log", params={"limit": 500})

    assert response.status_code == 422
