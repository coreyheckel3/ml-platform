from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

PLATFORM_ADMIN_CONTROLS_SCHEMA_VERSION = "forgeml.platform_admin_controls.v1"


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


@dataclass(frozen=True)
class AdminOrganizationProfile:
    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime | None


@dataclass(frozen=True)
class AdminUserAccessProfile:
    id: UUID
    email: str
    display_name: str
    status: str
    permissions: tuple[str, ...]
    last_login_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class AdminControlPlaneSnapshot:
    organization: AdminOrganizationProfile | None
    users: tuple[AdminUserAccessProfile, ...]
    project_count: int
    audit_event_count: int
    release_evidence_report_count: int


@dataclass(frozen=True)
class AdminPermissionSummary:
    code: str
    module: str
    action: str
    description: str
    granted_to_current_principal: bool


@dataclass(frozen=True)
class AdminPermissionGroupSummary:
    module: str
    permission_count: int
    granted_count: int
    permissions: tuple[AdminPermissionSummary, ...]


@dataclass(frozen=True)
class AdminRolePresetSummary:
    code: str
    name: str
    description: str
    permissions: tuple[str, ...]
    permission_count: int
    assigned_user_count: int
    granted_to_current_principal: bool


@dataclass(frozen=True)
class AdminEnvironmentSummary:
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


@dataclass(frozen=True)
class AdminSafeguardSummary:
    label: str
    status: str
    detail: str
    evidence: str


@dataclass(frozen=True)
class AdminControlPlaneStats:
    total_users: int
    active_users: int
    disabled_users: int
    project_count: int
    audit_event_count: int
    release_evidence_report_count: int
    role_preset_count: int
    permission_count: int
    permission_group_count: int


@dataclass(frozen=True)
class PlatformAdminControls:
    organization: AdminOrganizationProfile
    users: tuple[AdminUserAccessProfile, ...]
    role_presets: tuple[AdminRolePresetSummary, ...]
    permission_groups: tuple[AdminPermissionGroupSummary, ...]
    environment: AdminEnvironmentSummary
    safeguards: tuple[AdminSafeguardSummary, ...]
    operator_commands: tuple[str, ...]
    stats: AdminControlPlaneStats
