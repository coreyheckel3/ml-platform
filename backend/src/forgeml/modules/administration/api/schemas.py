from pydantic import BaseModel, Field


class AdminOrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    created_at: str | None


class AdminUserAccessResponse(BaseModel):
    id: str
    email: str
    display_name: str
    status: str
    permissions: list[str] = Field(default_factory=list)
    permission_count: int
    role_codes: list[str] = Field(default_factory=list)
    last_login_at: str | None
    created_at: str | None
    updated_at: str | None


class AdminRolePresetResponse(BaseModel):
    code: str
    name: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    permission_count: int
    assigned_user_count: int
    granted_to_current_principal: bool


class AdminPermissionResponse(BaseModel):
    code: str
    module: str
    action: str
    description: str
    granted_to_current_principal: bool


class AdminPermissionGroupResponse(BaseModel):
    module: str
    permission_count: int
    granted_count: int
    permissions: list[AdminPermissionResponse] = Field(default_factory=list)


class AdminEnvironmentResponse(BaseModel):
    environment: str
    production_like: bool
    docs_enabled: bool
    rate_limit_enabled: bool
    request_logging_enabled: bool
    structured_logging_enabled: bool
    readiness_checks_enabled: bool
    external_training_profiles_enabled: bool
    release_evidence_provider: str
    release_evidence_repository: str | None
    release_evidence_branch: str | None
    release_evidence_workflow: str | None
    release_evidence_artifact_name: str | None
    object_storage_configured: bool
    redis_configured: bool
    mlflow_tracking_configured: bool
    airflow_orchestration_enabled: bool
    cors_origin_count: int
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    jwt_issuer: str


class AdminSafeguardResponse(BaseModel):
    label: str
    status: str
    detail: str
    evidence: str


class AdminControlPlaneStatsResponse(BaseModel):
    total_users: int
    active_users: int
    disabled_users: int
    project_count: int
    audit_event_count: int
    release_evidence_report_count: int
    role_preset_count: int
    permission_count: int
    permission_group_count: int


class PlatformAdminControlsResponse(BaseModel):
    schema_version: str = "forgeml.platform_admin_controls.v1"
    organization: AdminOrganizationResponse
    users: list[AdminUserAccessResponse] = Field(default_factory=list)
    role_presets: list[AdminRolePresetResponse] = Field(default_factory=list)
    permission_groups: list[AdminPermissionGroupResponse] = Field(default_factory=list)
    environment: AdminEnvironmentResponse
    safeguards: list[AdminSafeguardResponse] = Field(default_factory=list)
    operator_commands: list[str] = Field(default_factory=list)
    stats: AdminControlPlaneStatsResponse


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
