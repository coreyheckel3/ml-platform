from dataclasses import dataclass
from uuid import UUID

from forgeml.modules.administration.domain.entities import AuditLogEntry
from forgeml.modules.administration.repositories.interfaces import (
    AuditLogFilters,
    AuditLogRepository,
)
from forgeml.platform.domain.errors import PermissionDeniedError
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class ListAuditLogQuery:
    organization_id: UUID
    actor_type: str | None = None
    action: str | None = None
    resource_type: str | None = None
    limit: int = 50


class AdministrationService:
    def __init__(self, *, audit_log: AuditLogRepository) -> None:
        self._audit_log = audit_log

    def list_audit_log(
        self,
        query: ListAuditLogQuery,
        principal: Principal,
    ) -> list[AuditLogEntry]:
        if not principal.has("admin:audit_log:read"):
            raise PermissionDeniedError("You do not have permission to read audit logs.")
        if str(query.organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot read audit logs for another organization.")

        return self._audit_log.list_entries(
            query.organization_id,
            filters=AuditLogFilters(
                actor_type=_clean_filter(query.actor_type),
                action=_clean_filter(query.action),
                resource_type=_clean_filter(query.resource_type),
            ),
            limit=min(max(query.limit, 1), 200),
        )


def _clean_filter(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
