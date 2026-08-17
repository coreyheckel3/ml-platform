from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLogEvent:
    organization_id: UUID | None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, object]


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


@dataclass(frozen=True)
class ReleaseEvidenceReport:
    id: UUID
    organization_id: UUID
    requested_by_user_id: str
    provider: str
    status: str
    repository: str | None
    branch: str | None
    workflow: str | None
    artifact_name: str | None
    run_id: str | None
    run_url: str | None
    manifest_git_sha: str | None
    manifest_git_branch: str | None
    ci_run_url: str | None
    artifact_count: int
    quality_gate_count: int
    missing_artifacts: tuple[str, ...]
    missing_quality_gates: tuple[str, ...]
    comparison: dict[str, object]
    manifest_summary: dict[str, object]
    report: dict[str, object]
    error_message: str | None
    created_at: datetime
