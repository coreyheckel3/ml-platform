from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLogEntry:
    id: UUID
    organization_id: UUID | None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, object]
    created_at: datetime
