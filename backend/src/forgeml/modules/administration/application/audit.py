from uuid import UUID

from forgeml.modules.administration.domain.entities import AuditLogEvent
from forgeml.modules.administration.repositories.interfaces import AuditEventRecorder


def record_user_audit_event(
    audit_log: AuditEventRecorder | None,
    *,
    organization_id: UUID | None,
    actor_id: UUID | str,
    action: str,
    resource_type: str,
    resource_id: UUID | str,
    metadata: dict[str, object],
) -> None:
    if audit_log is None:
        return
    audit_log.record(
        AuditLogEvent(
            organization_id=organization_id,
            actor_type="user",
            actor_id=str(actor_id),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            metadata=metadata,
        )
    )
