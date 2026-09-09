from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from forgeml.modules.administration.api.schemas import (
    AdminControlPlaneStatsResponse,
    AdminEnvironmentResponse,
    AdminOrganizationResponse,
    AdminPermissionGroupResponse,
    AdminPermissionResponse,
    AdminRolePresetResponse,
    AdminSafeguardResponse,
    AdminUserAccessResponse,
    AuditLogEntryResponse,
    AuditLogListResponse,
    PlatformAdminControlsResponse,
    ReleaseEvidenceNotificationPolicyResponse,
    ReleaseEvidenceRefreshStatusResponse,
    ReleaseEvidenceReportListResponse,
    ReleaseEvidenceReportResponse,
)
from forgeml.modules.administration.application.services import (
    AdminControlsRuntimeConfig,
    AdministrationService,
    GetPlatformAdminControlsQuery,
    GetReleaseEvidenceRefreshStatusQuery,
    GetReleaseEvidenceReportQuery,
    ListAuditLogQuery,
    ListReleaseEvidenceReportsQuery,
    ReleaseEvidenceRefreshStatus,
    ReleaseEvidenceRetrievalConfig,
    RetrieveReleaseEvidenceCommand,
)
from forgeml.modules.administration.domain.entities import (
    AdminEnvironmentSummary,
    AdminPermissionGroupSummary,
    AdminRolePresetSummary,
    AdminUserAccessProfile,
    AuditLogEntry,
    PlatformAdminControls,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAdminControlPlaneRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyReleaseEvidenceReportRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.domain.errors import DomainValidationError
from forgeml.platform.notifications import (
    NoopReleaseEvidenceNotificationGateway,
    ReleaseEvidenceNotificationGateway,
    ReleaseEvidenceNotificationPolicy,
    WebhookReleaseEvidenceNotificationGateway,
)
from forgeml.platform.release_evidence import (
    GitHubActionsReleaseEvidenceGateway,
    LocalReleaseEvidenceGateway,
    ReleaseEvidenceGateway,
)
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["administration"])


def get_administration_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AdministrationService:
    return AdministrationService(
        audit_log=SqlAlchemyAuditLogRepository(session),
        admin_controls=SqlAlchemyAdminControlPlaneRepository(session),
        admin_controls_runtime_config=_admin_controls_runtime_config_from_settings(
            settings
        ),
        release_evidence_reports=SqlAlchemyReleaseEvidenceReportRepository(session),
        release_evidence_gateway=_release_evidence_gateway_from_settings(settings),
        release_evidence_config=_release_evidence_config_from_settings(settings),
        release_evidence_notifications=_release_evidence_notification_gateway_from_settings(
            settings
        ),
        release_evidence_notification_policy=(
            _release_evidence_notification_policy_from_settings(settings)
        ),
    )


@router.get("/admin/controls", response_model=PlatformAdminControlsResponse)
def get_platform_admin_controls(
    principal: Principal = Depends(get_current_principal),
    service: AdministrationService = Depends(get_administration_service),
) -> PlatformAdminControlsResponse:
    controls = service.get_platform_admin_controls(
        GetPlatformAdminControlsQuery(
            organization_id=UUID(principal.organization_id),
        ),
        principal,
    )
    return _platform_admin_controls_response(controls)


@router.get("/admin/audit-log", response_model=AuditLogListResponse)
def list_audit_log(
    actor_type: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(get_current_principal),
    service: AdministrationService = Depends(get_administration_service),
) -> AuditLogListResponse:
    entries = service.list_audit_log(
        ListAuditLogQuery(
            organization_id=UUID(principal.organization_id),
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            limit=limit,
        ),
        principal,
    )
    return AuditLogListResponse(items=[_audit_log_response(entry) for entry in entries])


@router.get(
    "/admin/release-evidence/reports",
    response_model=ReleaseEvidenceReportListResponse,
)
def list_release_evidence_reports(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    service: AdministrationService = Depends(get_administration_service),
) -> ReleaseEvidenceReportListResponse:
    reports = service.list_release_evidence_reports(
        ListReleaseEvidenceReportsQuery(
            organization_id=UUID(principal.organization_id),
            status=status,
            limit=limit,
        ),
        principal,
    )
    return ReleaseEvidenceReportListResponse(
        items=[_release_evidence_report_response(report) for report in reports],
    )


@router.post(
    "/admin/release-evidence/reports/retrieve",
    response_model=ReleaseEvidenceReportResponse,
    status_code=201,
)
def retrieve_release_evidence_report(
    principal: Principal = Depends(get_current_principal),
    service: AdministrationService = Depends(get_administration_service),
) -> ReleaseEvidenceReportResponse:
    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=UUID(principal.organization_id)),
        principal,
    )
    return _release_evidence_report_response(report)


@router.get(
    "/admin/release-evidence/refresh/status",
    response_model=ReleaseEvidenceRefreshStatusResponse,
)
def get_release_evidence_refresh_status(
    stale_after_seconds: int | None = Query(default=None, ge=1, le=2_592_000),
    refresh_interval_seconds: int | None = Query(default=None, ge=1, le=604_800),
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
    service: AdministrationService = Depends(get_administration_service),
) -> ReleaseEvidenceRefreshStatusResponse:
    status = service.get_release_evidence_refresh_status(
        GetReleaseEvidenceRefreshStatusQuery(
            organization_id=UUID(principal.organization_id),
            stale_after_seconds=(
                stale_after_seconds
                if stale_after_seconds is not None
                else settings.release_evidence_stale_after_seconds
            ),
            refresh_interval_seconds=(
                refresh_interval_seconds
                if refresh_interval_seconds is not None
                else settings.release_evidence_refresh_interval_seconds
            ),
        ),
        principal,
    )
    return _release_evidence_refresh_status_response(status)


@router.get(
    "/admin/release-evidence/reports/{report_id}",
    response_model=ReleaseEvidenceReportResponse,
)
def get_release_evidence_report(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: AdministrationService = Depends(get_administration_service),
) -> ReleaseEvidenceReportResponse:
    report = service.get_release_evidence_report(
        GetReleaseEvidenceReportQuery(
            organization_id=UUID(principal.organization_id),
            report_id=report_id,
        ),
        principal,
    )
    return _release_evidence_report_response(report)


def _platform_admin_controls_response(
    controls: PlatformAdminControls,
) -> PlatformAdminControlsResponse:
    return PlatformAdminControlsResponse(
        organization=AdminOrganizationResponse(
            id=str(controls.organization.id),
            name=controls.organization.name,
            slug=controls.organization.slug,
            status=controls.organization.status,
            created_at=(
                controls.organization.created_at.isoformat()
                if controls.organization.created_at
                else None
            ),
        ),
        users=[
            _admin_user_access_response(user, controls.role_presets)
            for user in controls.users
        ],
        role_presets=[
            _admin_role_preset_response(role) for role in controls.role_presets
        ],
        permission_groups=[
            _admin_permission_group_response(group)
            for group in controls.permission_groups
        ],
        environment=_admin_environment_response(controls.environment),
        safeguards=[
            AdminSafeguardResponse(
                label=safeguard.label,
                status=safeguard.status,
                detail=safeguard.detail,
                evidence=safeguard.evidence,
            )
            for safeguard in controls.safeguards
        ],
        operator_commands=list(controls.operator_commands),
        stats=AdminControlPlaneStatsResponse(
            total_users=controls.stats.total_users,
            active_users=controls.stats.active_users,
            disabled_users=controls.stats.disabled_users,
            project_count=controls.stats.project_count,
            audit_event_count=controls.stats.audit_event_count,
            release_evidence_report_count=controls.stats.release_evidence_report_count,
            role_preset_count=controls.stats.role_preset_count,
            permission_count=controls.stats.permission_count,
            permission_group_count=controls.stats.permission_group_count,
        ),
    )


def _admin_user_access_response(
    user: AdminUserAccessProfile,
    role_presets: tuple[AdminRolePresetSummary, ...],
) -> AdminUserAccessResponse:
    return AdminUserAccessResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        permissions=list(user.permissions),
        permission_count=len(user.permissions),
        role_codes=[
            role.code
            for role in role_presets
            if _user_permissions_match_role(user.permissions, role.permissions)
        ],
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


def _admin_role_preset_response(
    role: AdminRolePresetSummary,
) -> AdminRolePresetResponse:
    return AdminRolePresetResponse(
        code=role.code,
        name=role.name,
        description=role.description,
        permissions=list(role.permissions),
        permission_count=role.permission_count,
        assigned_user_count=role.assigned_user_count,
        granted_to_current_principal=role.granted_to_current_principal,
    )


def _admin_permission_group_response(
    group: AdminPermissionGroupSummary,
) -> AdminPermissionGroupResponse:
    return AdminPermissionGroupResponse(
        module=group.module,
        permission_count=group.permission_count,
        granted_count=group.granted_count,
        permissions=[
            AdminPermissionResponse(
                code=permission.code,
                module=permission.module,
                action=permission.action,
                description=permission.description,
                granted_to_current_principal=permission.granted_to_current_principal,
            )
            for permission in group.permissions
        ],
    )


def _admin_environment_response(
    environment: AdminEnvironmentSummary,
) -> AdminEnvironmentResponse:
    return AdminEnvironmentResponse(
        environment=environment.environment,
        production_like=environment.production_like,
        docs_enabled=environment.docs_enabled,
        rate_limit_enabled=environment.rate_limit_enabled,
        request_logging_enabled=environment.request_logging_enabled,
        structured_logging_enabled=environment.structured_logging_enabled,
        readiness_checks_enabled=environment.readiness_checks_enabled,
        external_training_profiles_enabled=environment.external_training_profiles_enabled,
        release_evidence_provider=environment.release_evidence_provider,
        release_evidence_repository=environment.release_evidence_repository,
        release_evidence_branch=environment.release_evidence_branch,
        release_evidence_workflow=environment.release_evidence_workflow,
        release_evidence_artifact_name=environment.release_evidence_artifact_name,
        object_storage_configured=environment.object_storage_configured,
        redis_configured=environment.redis_configured,
        mlflow_tracking_configured=environment.mlflow_tracking_configured,
        airflow_orchestration_enabled=environment.airflow_orchestration_enabled,
        cors_origin_count=environment.cors_origin_count,
        access_token_ttl_seconds=environment.access_token_ttl_seconds,
        refresh_token_ttl_seconds=environment.refresh_token_ttl_seconds,
        jwt_issuer=environment.jwt_issuer,
    )


def _user_permissions_match_role(
    user_permissions: tuple[str, ...],
    role_permissions: tuple[str, ...],
) -> bool:
    user_permission_set = frozenset(user_permissions)
    role_permission_set = frozenset(role_permissions)
    if "*" in user_permission_set:
        return "*" in role_permission_set
    if "*" in role_permission_set:
        return False
    return role_permission_set.issubset(user_permission_set)


def _audit_log_response(entry: AuditLogEntry) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        id=str(entry.id),
        organization_id=str(entry.organization_id) if entry.organization_id else None,
        actor_type=entry.actor_type,
        actor_id=entry.actor_id,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        metadata=entry.metadata,
        created_at=entry.created_at.isoformat(),
    )


def _release_evidence_report_response(
    report: ReleaseEvidenceReport,
) -> ReleaseEvidenceReportResponse:
    return ReleaseEvidenceReportResponse(
        id=str(report.id),
        organization_id=str(report.organization_id),
        requested_by_user_id=report.requested_by_user_id,
        provider=report.provider,
        status=report.status,
        repository=report.repository,
        branch=report.branch,
        workflow=report.workflow,
        artifact_name=report.artifact_name,
        run_id=report.run_id,
        run_url=report.run_url,
        manifest_git_sha=report.manifest_git_sha,
        manifest_git_branch=report.manifest_git_branch,
        ci_run_url=report.ci_run_url,
        artifact_count=report.artifact_count,
        quality_gate_count=report.quality_gate_count,
        missing_artifacts=list(report.missing_artifacts),
        missing_quality_gates=list(report.missing_quality_gates),
        comparison=report.comparison,
        manifest_summary=report.manifest_summary,
        report=report.report,
        error_message=report.error_message,
        created_at=report.created_at.isoformat(),
    )


def _release_evidence_refresh_status_response(
    status: ReleaseEvidenceRefreshStatus,
) -> ReleaseEvidenceRefreshStatusResponse:
    return ReleaseEvidenceRefreshStatusResponse(
        organization_id=str(status.organization_id),
        provider=status.provider,
        repository=status.repository,
        branch=status.branch,
        workflow=status.workflow,
        artifact_name=status.artifact_name,
        status=status.status,
        stale=status.stale,
        stale_after_seconds=status.stale_after_seconds,
        refresh_interval_seconds=status.refresh_interval_seconds,
        latest_report=(
            _release_evidence_report_response(status.latest_report)
            if status.latest_report
            else None
        ),
        last_successful_report=(
            _release_evidence_report_response(status.last_successful_report)
            if status.last_successful_report
            else None
        ),
        latest_report_age_seconds=status.latest_report_age_seconds,
        last_success_age_seconds=status.last_success_age_seconds,
        next_refresh_at=(
            status.next_refresh_at.isoformat() if status.next_refresh_at else None
        ),
        checked_at=status.checked_at.isoformat(),
        stale_reasons=list(status.stale_reasons),
        recommended_action=status.recommended_action,
        operator_command=status.operator_command,
        notification_policy=_release_evidence_notification_policy_response(
            status.notification_policy
        ),
    )


def _admin_controls_runtime_config_from_settings(
    settings: Settings,
) -> AdminControlsRuntimeConfig:
    return AdminControlsRuntimeConfig(
        environment=settings.environment,
        docs_enabled=settings.enable_docs,
        rate_limit_enabled=settings.rate_limit_enabled,
        request_logging_enabled=settings.request_logging_enabled,
        structured_logging_enabled=settings.structured_logging_enabled,
        readiness_checks_enabled=settings.readiness_checks_enabled,
        external_training_profiles_enabled=settings.external_training_profiles_enabled,
        release_evidence_provider=settings.release_evidence_provider,
        release_evidence_repository=settings.release_evidence_github_repository,
        release_evidence_branch=settings.release_evidence_github_branch,
        release_evidence_workflow=settings.release_evidence_github_workflow,
        release_evidence_artifact_name=settings.release_evidence_github_artifact_name,
        object_storage_endpoint=settings.object_storage_endpoint,
        redis_url=settings.redis_url,
        mlflow_tracking_uri=settings.mlflow_tracking_uri,
        airflow_orchestration_enabled=settings.airflow_orchestration_enabled,
        cors_origin_count=len(settings.cors_origins),
        access_token_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
        jwt_issuer=settings.jwt_issuer,
    )


def _release_evidence_gateway_from_settings(settings: Settings) -> ReleaseEvidenceGateway:
    provider = settings.release_evidence_provider.strip().lower()
    if provider == "github_actions":
        return GitHubActionsReleaseEvidenceGateway(
            repository=settings.release_evidence_github_repository,
            token=settings.release_evidence_github_token,
            branch=settings.release_evidence_github_branch,
            workflow_file=settings.release_evidence_github_workflow,
            artifact_name=settings.release_evidence_github_artifact_name,
        )
    if provider == "local_manifest":
        return LocalReleaseEvidenceGateway(
            settings.release_evidence_manifest_path,
            branch=settings.release_evidence_github_branch,
        )
    raise DomainValidationError(
        "Release evidence provider must be github_actions or local_manifest."
    )


def _release_evidence_config_from_settings(
    settings: Settings,
) -> ReleaseEvidenceRetrievalConfig:
    provider = settings.release_evidence_provider.strip().lower()
    return ReleaseEvidenceRetrievalConfig(
        provider=provider,
        repository=(
            settings.release_evidence_github_repository
            if provider == "github_actions"
            else None
        ),
        branch=settings.release_evidence_github_branch,
        workflow=settings.release_evidence_github_workflow,
        artifact_name=settings.release_evidence_github_artifact_name,
    )


def _release_evidence_notification_gateway_from_settings(
    settings: Settings,
) -> ReleaseEvidenceNotificationGateway:
    policy = _release_evidence_notification_policy_from_settings(settings)
    if policy.enabled and policy.channel_type == "webhook":
        webhook_url = settings.release_evidence_notification_webhook_url
        if webhook_url:
            return WebhookReleaseEvidenceNotificationGateway(
                webhook_url=webhook_url,
                target=policy.target,
                timeout_seconds=settings.release_evidence_notification_timeout_seconds,
            )
    return NoopReleaseEvidenceNotificationGateway(
        channel_type=policy.channel_type,
        target=policy.target,
        reason="release evidence notifications are disabled or not configured",
    )


def _release_evidence_notification_policy_from_settings(
    settings: Settings,
) -> ReleaseEvidenceNotificationPolicy:
    channel_type = settings.release_evidence_notification_channel.strip().lower()
    if channel_type not in {"noop", "webhook"}:
        raise DomainValidationError(
            "Release evidence notification channel must be noop or webhook."
        )
    webhook_url = settings.release_evidence_notification_webhook_url
    enabled = (
        settings.release_evidence_notifications_enabled
        and channel_type == "webhook"
        and bool(webhook_url)
    )
    target = (
        _redacted_webhook_target(webhook_url)
        if channel_type == "webhook" and webhook_url
        else "audit-log only"
    )
    return ReleaseEvidenceNotificationPolicy(
        enabled=enabled,
        channel_type=channel_type,
        target=target,
        failure_statuses=("failed",),
        escalation_window_seconds=(
            settings.release_evidence_notification_escalation_window_seconds
        ),
        escalation_command=(
            "PYTHONPATH=backend/src:. python "
            "scripts/ops/refresh_release_evidence.py --base-url "
            "http://127.0.0.1:8001 --once --force"
        ),
        delivery_audit_actions=(
            "release_evidence.notification_delivered",
            "release_evidence.notification_failed",
            "release_evidence.notification_skipped",
        ),
    )


def _release_evidence_notification_policy_response(
    policy: ReleaseEvidenceNotificationPolicy,
) -> ReleaseEvidenceNotificationPolicyResponse:
    return ReleaseEvidenceNotificationPolicyResponse(
        enabled=policy.enabled,
        channel_type=policy.channel_type,
        target=policy.target,
        failure_statuses=list(policy.failure_statuses),
        escalation_window_seconds=policy.escalation_window_seconds,
        escalation_command=policy.escalation_command,
        delivery_audit_actions=list(policy.delivery_audit_actions),
    )


def _redacted_webhook_target(webhook_url: str) -> str:
    parsed = urlsplit(webhook_url)
    if not parsed.scheme or not parsed.netloc:
        return "configured webhook"
    return f"{parsed.scheme}://{parsed.netloc}/..."
