from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib import error, request

RELEASE_EVIDENCE_NOTIFICATION_SCHEMA_VERSION = (
    "forgeml.release_evidence_notification.v1"
)


@dataclass(frozen=True)
class ReleaseEvidenceNotificationPolicy:
    enabled: bool
    channel_type: str
    target: str
    failure_statuses: tuple[str, ...]
    escalation_window_seconds: int
    escalation_command: str
    delivery_audit_actions: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseEvidenceNotification:
    organization_id: str
    report_id: str
    status: str
    severity: str
    title: str
    message: str
    source: dict[str, object]
    report_url: str | None
    action_url: str | None
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_payload(self) -> dict[str, object]:
        return {
            "schema_version": RELEASE_EVIDENCE_NOTIFICATION_SCHEMA_VERSION,
            "organization_id": self.organization_id,
            "report_id": self.report_id,
            "status": self.status,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "report_url": self.report_url,
            "action_url": self.action_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class NotificationDeliveryResult:
    channel_type: str
    target: str
    status: str
    response_status: int | None
    error_message: str | None
    delivered_at: datetime


class ReleaseEvidenceNotificationGateway(Protocol):
    def send(
        self,
        notification: ReleaseEvidenceNotification,
    ) -> NotificationDeliveryResult:
        raise NotImplementedError


@dataclass(frozen=True)
class NoopReleaseEvidenceNotificationGateway:
    channel_type: str = "noop"
    target: str = "audit-log only"
    reason: str = "release evidence notifications are disabled"

    def send(
        self,
        notification: ReleaseEvidenceNotification,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            channel_type=self.channel_type,
            target=self.target,
            status="skipped",
            response_status=None,
            error_message=self.reason,
            delivered_at=datetime.now(UTC),
        )


@dataclass(frozen=True)
class WebhookReleaseEvidenceNotificationGateway:
    webhook_url: str
    target: str
    timeout_seconds: float = 5.0

    def send(
        self,
        notification: ReleaseEvidenceNotification,
    ) -> NotificationDeliveryResult:
        payload = json.dumps(notification.as_payload()).encode("utf-8")
        webhook_request = request.Request(  # noqa: S310
            self.webhook_url,
            data=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "user-agent": "ForgeML release evidence notifications",
            },
            method="POST",
        )
        try:
            with request.urlopen(  # noqa: S310
                webhook_request,
                timeout=self.timeout_seconds,
            ) as response:
                response_status = response.status
        except error.HTTPError as exc:
            return NotificationDeliveryResult(
                channel_type="webhook",
                target=self.target,
                status="failed",
                response_status=exc.code,
                error_message=f"HTTP {exc.code}: {exc.reason}",
                delivered_at=datetime.now(UTC),
            )
        except OSError as exc:
            return NotificationDeliveryResult(
                channel_type="webhook",
                target=self.target,
                status="failed",
                response_status=None,
                error_message=str(exc),
                delivered_at=datetime.now(UTC),
            )

        return NotificationDeliveryResult(
            channel_type="webhook",
            target=self.target,
            status="delivered",
            response_status=response_status,
            error_message=None,
            delivered_at=datetime.now(UTC),
        )
