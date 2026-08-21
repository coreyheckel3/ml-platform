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


class ReleaseEvidenceNotificationPolicyResponse(BaseModel):
    enabled: bool
    channel_type: str
    target: str
    failure_statuses: list[str] = Field(default_factory=list)
    escalation_window_seconds: int
    escalation_command: str
    delivery_audit_actions: list[str] = Field(default_factory=list)


class ReleaseEvidenceRefreshStatusResponse(BaseModel):
    schema_version: str = "forgeml.release_evidence_refresh_status.v1"
    organization_id: str
    provider: str
    repository: str | None
    branch: str | None
    workflow: str | None
    artifact_name: str | None
    status: str
    stale: bool
    stale_after_seconds: int
    refresh_interval_seconds: int
    latest_report: ReleaseEvidenceReportResponse | None
    last_successful_report: ReleaseEvidenceReportResponse | None
    latest_report_age_seconds: int | None
    last_success_age_seconds: int | None
    next_refresh_at: str | None
    checked_at: str
    stale_reasons: list[str] = Field(default_factory=list)
    recommended_action: str
    operator_command: str
    notification_policy: ReleaseEvidenceNotificationPolicyResponse
