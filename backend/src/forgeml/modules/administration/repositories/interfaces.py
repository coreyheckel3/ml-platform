from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from forgeml.modules.administration.domain.entities import (
    AuditLogEntry,
    AuditLogEvent,
    ReleaseEvidenceReport,
)


@dataclass(frozen=True)
class AuditLogFilters:
    actor_type: str | None = None
    action: str | None = None
    resource_type: str | None = None


class AuditEventRecorder(Protocol):
    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        raise NotImplementedError


class AuditLogRepository(AuditEventRecorder, Protocol):
    def list_entries(
        self,
        organization_id: UUID,
        *,
        filters: AuditLogFilters,
        limit: int,
    ) -> list[AuditLogEntry]:
        raise NotImplementedError


@dataclass(frozen=True)
class ReleaseEvidenceReportFilters:
    status: str | None = None


class ReleaseEvidenceReportRepository(Protocol):
    def save(self, report: ReleaseEvidenceReport) -> ReleaseEvidenceReport:
        raise NotImplementedError

    def list_reports(
        self,
        organization_id: UUID,
        *,
        filters: ReleaseEvidenceReportFilters,
        limit: int,
    ) -> list[ReleaseEvidenceReport]:
        raise NotImplementedError

    def get_report(
        self,
        organization_id: UUID,
        report_id: UUID,
    ) -> ReleaseEvidenceReport | None:
        raise NotImplementedError
