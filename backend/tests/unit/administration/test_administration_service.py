from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from forgeml.modules.administration.application.services import (
    AdministrationService,
    ListAuditLogQuery,
)
from forgeml.modules.administration.domain.entities import AuditLogEntry
from forgeml.modules.administration.repositories.interfaces import AuditLogFilters
from forgeml.platform.domain.errors import PermissionDeniedError
from forgeml.platform.security.rbac import Principal


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.filters: AuditLogFilters | None = None
        self.limit: int | None = None

    def list_entries(
        self,
        organization_id: UUID,
        *,
        filters: AuditLogFilters,
        limit: int,
    ) -> list[AuditLogEntry]:
        self.filters = filters
        self.limit = limit
        return [
            AuditLogEntry(
                id=uuid4(),
                organization_id=organization_id,
                actor_type="user",
                actor_id="user-1",
                action="models.approve",
                resource_type="model_version",
                resource_id="model-version-1",
                metadata={"status": "approved"},
                created_at=datetime.now(UTC),
            )
        ]


def test_administration_service_lists_org_scoped_audit_log_with_filters() -> None:
    organization_id = uuid4()
    repository = FakeAuditLogRepository()
    service = AdministrationService(audit_log=repository)

    entries = service.list_audit_log(
        ListAuditLogQuery(
            organization_id=organization_id,
            actor_type=" user ",
            action=" models.approve ",
            resource_type=" model_version ",
            limit=500,
        ),
        principal(organization_id, {"admin:audit_log:read"}),
    )

    assert entries[0].action == "models.approve"
    assert repository.filters == AuditLogFilters(
        actor_type="user",
        action="models.approve",
        resource_type="model_version",
    )
    assert repository.limit == 200


def test_administration_service_requires_audit_permission() -> None:
    organization_id = uuid4()
    service = AdministrationService(audit_log=FakeAuditLogRepository())

    with pytest.raises(PermissionDeniedError):
        service.list_audit_log(
            ListAuditLogQuery(organization_id=organization_id),
            principal(organization_id, {"projects:read"}),
        )


def test_administration_service_rejects_cross_org_audit_reads() -> None:
    service = AdministrationService(audit_log=FakeAuditLogRepository())

    with pytest.raises(PermissionDeniedError):
        service.list_audit_log(
            ListAuditLogQuery(organization_id=uuid4()),
            principal(uuid4(), {"admin:audit_log:read"}),
        )


def principal(organization_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(uuid4()),
        email="admin@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )
