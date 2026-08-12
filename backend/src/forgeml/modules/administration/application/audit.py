from uuid import UUID

from forgeml.modules.administration.domain.entities import AuditLogEvent
from forgeml.modules.administration.repositories.interfaces import AuditEventRecorder

SENSITIVE_AUDIT_METADATA_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "credentials",
        "jwt",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)
REDACTED_AUDIT_METADATA_VALUE = "[REDACTED]"


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
            metadata=sanitize_audit_metadata(metadata),
        )
    )


def sanitize_audit_metadata(metadata: dict[str, object]) -> dict[str, object]:
    return {
        key: _sanitize_audit_metadata_value(key, value)
        for key, value in metadata.items()
    }


def _sanitize_audit_metadata_value(key: str, value: object) -> object:
    if _is_sensitive_audit_metadata_key(key):
        return REDACTED_AUDIT_METADATA_VALUE
    if isinstance(value, dict):
        return sanitize_audit_metadata(value)
    if isinstance(value, list):
        return [_sanitize_audit_metadata_value(key, item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_audit_metadata_value(key, item) for item in value]
    return value


def _is_sensitive_audit_metadata_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(sensitive_key in normalized for sensitive_key in SENSITIVE_AUDIT_METADATA_KEYS)
