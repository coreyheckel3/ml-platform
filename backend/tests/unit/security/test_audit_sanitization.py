from datetime import UTC, datetime
from uuid import uuid4

from forgeml.modules.administration.application.audit import (
    REDACTED_AUDIT_METADATA_VALUE,
    record_user_audit_event,
    sanitize_audit_metadata,
)
from forgeml.modules.administration.domain.entities import AuditLogEntry, AuditLogEvent


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.events: list[AuditLogEvent] = []

    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        self.events.append(event)
        return AuditLogEntry(
            id=uuid4(),
            organization_id=event.organization_id,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata=event.metadata,
            created_at=datetime.now(UTC),
        )


def test_sanitize_audit_metadata_redacts_sensitive_key_families_recursively() -> None:
    sanitized = sanitize_audit_metadata(
        {
            "project_id": "project-1",
            "password": "super-secret",
            "nested": {
                "refresh-token": "refresh-token-value",
                "safe": "kept",
            },
            "headers": [{"Authorization": "Bearer access-token"}],
            "artifact_names": ("model.pkl", "metrics.json"),
        }
    )

    assert sanitized == {
        "project_id": "project-1",
        "password": REDACTED_AUDIT_METADATA_VALUE,
        "nested": {
            "refresh-token": REDACTED_AUDIT_METADATA_VALUE,
            "safe": "kept",
        },
        "headers": [{"Authorization": REDACTED_AUDIT_METADATA_VALUE}],
        "artifact_names": ["model.pkl", "metrics.json"],
    }


def test_record_user_audit_event_persists_sanitized_metadata() -> None:
    organization_id = uuid4()
    actor_id = uuid4()
    resource_id = uuid4()
    audit_log = FakeAuditLogRepository()

    record_user_audit_event(
        audit_log,
        organization_id=organization_id,
        actor_id=actor_id,
        action="api_keys.create",
        resource_type="api_key",
        resource_id=resource_id,
        metadata={
            "name": "notebook automation",
            "api_key": "fml_live_secret",
        },
    )

    assert audit_log.events[0].metadata == {
        "name": "notebook automation",
        "api_key": REDACTED_AUDIT_METADATA_VALUE,
    }
