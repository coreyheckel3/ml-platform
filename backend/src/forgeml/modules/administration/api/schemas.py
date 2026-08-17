from pydantic import BaseModel, Field


class AuditLogEntryResponse(BaseModel):
    id: str
    organization_id: str | None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    next_cursor: str | None = None


class ReleaseEvidenceReportResponse(BaseModel):
    id: str
    organization_id: str
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
    missing_artifacts: list[str] = Field(default_factory=list)
    missing_quality_gates: list[str] = Field(default_factory=list)
    comparison: dict[str, object] = Field(default_factory=dict)
    manifest_summary: dict[str, object] = Field(default_factory=dict)
    report: dict[str, object] = Field(default_factory=dict)
    error_message: str | None
    created_at: str


class ReleaseEvidenceReportListResponse(BaseModel):
    items: list[ReleaseEvidenceReportResponse]
    next_cursor: str | None = None
