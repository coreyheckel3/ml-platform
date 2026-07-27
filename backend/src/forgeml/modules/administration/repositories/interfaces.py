from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from forgeml.modules.administration.domain.entities import AuditLogEntry


@dataclass(frozen=True)
class AuditLogFilters:
    actor_type: str | None = None
    action: str | None = None
    resource_type: str | None = None


class AuditLogRepository(Protocol):
    def list_entries(
        self,
        organization_id: UUID,
        *,
        filters: AuditLogFilters,
        limit: int,
    ) -> list[AuditLogEntry]:
        raise NotImplementedError
