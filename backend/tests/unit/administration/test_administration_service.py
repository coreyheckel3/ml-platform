from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from forgeml.modules.administration.application.services import (
    AdminControlsRuntimeConfig,
    AdministrationService,
    GetPlatformAdminControlsQuery,
    GetReleaseEvidenceRefreshStatusQuery,
    GetReleaseEvidenceReportQuery,
    ListAuditLogQuery,
    ListReleaseEvidenceReportsQuery,
    ReleaseEvidenceRetrievalConfig,
    RetrieveReleaseEvidenceCommand,
)
from forgeml.modules.administration.domain.entities import (
    AdminControlPlaneSnapshot,
    AdminOrganizationProfile,
    AdminUserAccessProfile,
    AuditLogEntry,
    AuditLogEvent,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.repositories.interfaces import (
    AuditLogFilters,
    ReleaseEvidenceReportFilters,
)
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.notifications import (
    NotificationDeliveryResult,
    ReleaseEvidenceNotification,
    ReleaseEvidenceNotificationPolicy,
)
from forgeml.platform.release_evidence import (
    RELEASE_EVIDENCE_REQUIRED_ARTIFACTS,
    RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES,
    ReleaseEvidenceRetrievalError,
    ReleaseEvidenceRun,
)
from forgeml.platform.security.rbac import Principal


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.filters: AuditLogFilters | None = None
        self.limit: int | None = None
        self.recorded_events: list[AuditLogEvent] = []

    def list_entries(
        self,
        organization_id: UUID,
        *,
        filters: AuditLogFilters,
        limit: int,
    ) -> list[AuditLogEntry]:
        self.filters = filters
        self.limit = limit
        return [
            AuditLogEntry(
                id=uuid4(),
                organization_id=organization_id,
                actor_type="user",
                actor_id="user-1",
                action="models.approve",
                resource_type="model_version",
                resource_id="model-version-1",
                metadata={"status": "approved"},
                created_at=datetime.now(UTC),
            )
        ]

    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        self.recorded_events.append(event)
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


class FakeReleaseEvidenceReportRepository:
    def __init__(self, reports: list[ReleaseEvidenceReport] | None = None) -> None:
        self.reports = reports or []
        self.filters: ReleaseEvidenceReportFilters | None = None
        self.limit: int | None = None

    def save(self, report: ReleaseEvidenceReport) -> ReleaseEvidenceReport:
        self.reports.append(report)
        return report

    def list_reports(
        self,
        organization_id: UUID,
        *,
        filters: ReleaseEvidenceReportFilters,
        limit: int,
    ) -> list[ReleaseEvidenceReport]:
        self.filters = filters
        self.limit = limit
        return [
            report
            for report in self.reports
            if report.organization_id == organization_id
            and (not filters.status or report.status == filters.status)
        ][:limit]

    def get_report(
        self,
        organization_id: UUID,
        report_id: UUID,
    ) -> ReleaseEvidenceReport | None:
        for report in self.reports:
            if report.organization_id == organization_id and report.id == report_id:
                return report
        return None


class FakeReleaseEvidenceGateway:
    def __init__(
        self,
        *,
        manifest: dict[str, object] | None = None,
        error_message: str | None = None,
    ) -> None:
        self.manifest = manifest or release_manifest()
        self.error_message = error_message

    def latest_successful_run(self) -> ReleaseEvidenceRun:
        if self.error_message:
            raise ReleaseEvidenceRetrievalError(self.error_message)
        return ReleaseEvidenceRun(
            id=12345,
            head_sha="a" * 40,
            branch="main",
            status="completed",
            conclusion="success",
            html_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        )

    def download_release_manifest(
        self,
        run: ReleaseEvidenceRun,
    ) -> dict[str, object]:
        return self.manifest


class FakeReleaseEvidenceNotificationGateway:
    def __init__(
        self,
        *,
        status: str = "delivered",
        error_message: str | None = None,
    ) -> None:
        self.status = status
        self.error_message = error_message
        self.notifications: list[ReleaseEvidenceNotification] = []

    def send(
        self,
        notification: ReleaseEvidenceNotification,
    ) -> NotificationDeliveryResult:
        self.notifications.append(notification)
        return NotificationDeliveryResult(
            channel_type="webhook",
            target="https://hooks.example.com/...",
            status=self.status,
            response_status=202 if self.status == "delivered" else None,
            error_message=self.error_message,
            delivered_at=datetime(2026, 8, 17, 18, 5, tzinfo=UTC),
        )


class FakeAdminControlPlaneRepository:
    def __init__(
        self,
        organization: AdminOrganizationProfile | None,
        users: tuple[AdminUserAccessProfile, ...],
    ) -> None:
        self.organization = organization
        self.users = users
        self.organization_id: UUID | None = None

    def load_snapshot(self, organization_id: UUID) -> AdminControlPlaneSnapshot:
        self.organization_id = organization_id
        return AdminControlPlaneSnapshot(
            organization=self.organization,
            users=self.users,
            project_count=3,
            audit_event_count=7,
            release_evidence_report_count=2,
        )


def test_administration_service_returns_platform_admin_controls_summary() -> None:
    organization_id = uuid4()
    repository = FakeAdminControlPlaneRepository(
        organization=admin_organization(organization_id),
        users=(
            admin_user(organization_id, "admin@forgeml.dev", ("*",)),
            admin_user(
                organization_id,
                "auditor@forgeml.dev",
                (
                    "admin:audit_log:read",
                    "admin:controls:read",
                    "admin:release_evidence:read",
                    "projects:read",
                ),
            ),
        ),
    )
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        admin_controls=repository,
        admin_controls_runtime_config=admin_runtime_config(),
    )

    controls = service.get_platform_admin_controls(
        GetPlatformAdminControlsQuery(organization_id=organization_id),
        principal(organization_id, {"admin:controls:read"}),
    )

    assert repository.organization_id == organization_id
    assert controls.organization.slug == "forgeml-local"
    assert controls.stats.total_users == 2
    assert controls.stats.active_users == 2
    assert controls.stats.project_count == 3
    assert controls.stats.audit_event_count == 7
    assert controls.stats.release_evidence_report_count == 2
    assert controls.environment.environment == "local"
    assert controls.environment.production_like is False
    assert "make production-readiness" in controls.operator_commands
    assert any(safeguard.label == "RBAC mutations" for safeguard in controls.safeguards)

    role_counts = {role.code: role.assigned_user_count for role in controls.role_presets}
    assert role_counts["platform_admin"] == 1
    assert role_counts["security_auditor"] == 1

    administration_group = next(
        group for group in controls.permission_groups if group.module == "administration"
    )
    assert any(
        permission.code == "admin:controls:read"
        and permission.granted_to_current_principal
        for permission in administration_group.permissions
    )


def test_administration_service_requires_admin_controls_permission() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        admin_controls=FakeAdminControlPlaneRepository(
            admin_organization(organization_id),
            (),
        ),
        admin_controls_runtime_config=admin_runtime_config(),
    )

    with pytest.raises(PermissionDeniedError):
        service.get_platform_admin_controls(
            GetPlatformAdminControlsQuery(organization_id=organization_id),
            principal(organization_id, {"admin:audit_log:read"}),
        )


def test_administration_service_rejects_cross_org_admin_controls_reads() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        admin_controls=FakeAdminControlPlaneRepository(
            admin_organization(organization_id),
            (),
        ),
        admin_controls_runtime_config=admin_runtime_config(),
    )

    with pytest.raises(PermissionDeniedError):
        service.get_platform_admin_controls(
            GetPlatformAdminControlsQuery(organization_id=uuid4()),
            principal(organization_id, {"admin:controls:read"}),
        )


def test_administration_service_raises_for_missing_admin_controls_organization() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        admin_controls=FakeAdminControlPlaneRepository(None, ()),
        admin_controls_runtime_config=admin_runtime_config(),
    )

    with pytest.raises(ResourceNotFoundError):
        service.get_platform_admin_controls(
            GetPlatformAdminControlsQuery(organization_id=organization_id),
            principal(organization_id, {"admin:controls:read"}),
        )


def test_administration_service_lists_org_scoped_audit_log_with_filters() -> None:
    organization_id = uuid4()
    repository = FakeAuditLogRepository()
    service = AdministrationService(audit_log=repository)

    entries = service.list_audit_log(
        ListAuditLogQuery(
            organization_id=organization_id,
            actor_type=" user ",
            action=" models.approve ",
            resource_type=" model_version ",
            limit=500,
        ),
        principal(organization_id, {"admin:audit_log:read"}),
    )

    assert entries[0].action == "models.approve"
    assert repository.filters == AuditLogFilters(
        actor_type="user",
        action="models.approve",
        resource_type="model_version",
    )
    assert repository.limit == 200


def test_administration_service_requires_audit_permission() -> None:
    organization_id = uuid4()
    service = AdministrationService(audit_log=FakeAuditLogRepository())

    with pytest.raises(PermissionDeniedError):
        service.list_audit_log(
            ListAuditLogQuery(organization_id=organization_id),
            principal(organization_id, {"projects:read"}),
        )


def test_administration_service_rejects_cross_org_audit_reads() -> None:
    service = AdministrationService(audit_log=FakeAuditLogRepository())

    with pytest.raises(PermissionDeniedError):
        service.list_audit_log(
            ListAuditLogQuery(organization_id=uuid4()),
            principal(uuid4(), {"admin:audit_log:read"}),
        )


def test_administration_service_lists_release_evidence_reports_with_filters() -> None:
    organization_id = uuid4()
    report = release_evidence_report(organization_id, status="passed")
    repository = FakeReleaseEvidenceReportRepository([report])
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=repository,
    )

    reports = service.list_release_evidence_reports(
        ListReleaseEvidenceReportsQuery(
            organization_id=organization_id,
            status=" passed ",
            limit=500,
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert [item.id for item in reports] == [report.id]
    assert repository.filters == ReleaseEvidenceReportFilters(status="passed")
    assert repository.limit == 100


def test_administration_service_requires_release_evidence_read_permission() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
    )

    with pytest.raises(PermissionDeniedError):
        service.list_release_evidence_reports(
            ListReleaseEvidenceReportsQuery(organization_id=organization_id),
            principal(organization_id, {"projects:read"}),
        )


def test_administration_service_returns_release_evidence_report_by_id() -> None:
    organization_id = uuid4()
    report = release_evidence_report(organization_id, status="passed")
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository([report]),
    )

    found = service.get_release_evidence_report(
        GetReleaseEvidenceReportQuery(
            organization_id=organization_id,
            report_id=report.id,
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert found == report


def test_administration_service_raises_for_missing_release_evidence_report() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
    )

    with pytest.raises(ResourceNotFoundError):
        service.get_release_evidence_report(
            GetReleaseEvidenceReportQuery(
                organization_id=organization_id,
                report_id=uuid4(),
            ),
            principal(organization_id, {"admin:release_evidence:read"}),
        )


def test_administration_service_retrieves_release_evidence_and_records_audit() -> None:
    organization_id = uuid4()
    audit_log = FakeAuditLogRepository()
    reports = FakeReleaseEvidenceReportRepository()
    service = AdministrationService(
        audit_log=audit_log,
        release_evidence_reports=reports,
        release_evidence_gateway=FakeReleaseEvidenceGateway(),
        release_evidence_config=release_evidence_config(),
    )

    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=organization_id),
        principal(organization_id, {"admin:release_evidence:retrieve"}),
    )

    assert report.status == "passed"
    assert report.artifact_count == len(RELEASE_EVIDENCE_REQUIRED_ARTIFACTS)
    assert report.quality_gate_count == len(RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES)
    assert report.report["schema_version"] == "forgeml.release_evidence_retrieval.v1"
    assert reports.reports == [report]
    assert audit_log.recorded_events[0].action == "release_evidence.retrieve"
    assert audit_log.recorded_events[0].resource_id == str(report.id)


def test_administration_service_persists_failed_release_evidence_comparison() -> None:
    organization_id = uuid4()
    missing_gate = "release_evidence_drilldown_api_contract"
    manifest = release_manifest(
        quality_gates=tuple(
            gate
            for gate in RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES
            if gate != missing_gate
        ),
    )
    audit_log = FakeAuditLogRepository()
    service = AdministrationService(
        audit_log=audit_log,
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
        release_evidence_gateway=FakeReleaseEvidenceGateway(manifest=manifest),
        release_evidence_config=release_evidence_config(),
    )

    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=organization_id),
        principal(organization_id, {"admin:release_evidence:retrieve"}),
    )

    assert report.status == "failed"
    assert report.missing_quality_gates == (missing_gate,)
    assert report.comparison["passed"] is False
    assert audit_log.recorded_events[0].action == "release_evidence.retrieve_failed"


def test_administration_service_persists_release_evidence_retrieval_errors() -> None:
    organization_id = uuid4()
    reports = FakeReleaseEvidenceReportRepository()
    audit_log = FakeAuditLogRepository()
    service = AdministrationService(
        audit_log=audit_log,
        release_evidence_reports=reports,
        release_evidence_gateway=FakeReleaseEvidenceGateway(
            error_message="No successful ci.yml runs found on main."
        ),
        release_evidence_config=release_evidence_config(),
    )

    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=organization_id),
        principal(organization_id, {"admin:release_evidence:retrieve"}),
    )

    assert report.status == "failed"
    assert report.run_id is None
    assert report.error_message == "No successful ci.yml runs found on main."
    assert reports.reports == [report]
    assert audit_log.recorded_events[0].metadata["error_message"] == report.error_message


def test_administration_service_notifies_on_failed_release_evidence() -> None:
    organization_id = uuid4()
    missing_gate = "release_evidence_drilldown_api_contract"
    manifest = release_manifest(
        quality_gates=tuple(
            gate
            for gate in RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES
            if gate != missing_gate
        ),
    )
    audit_log = FakeAuditLogRepository()
    notifications = FakeReleaseEvidenceNotificationGateway()
    service = AdministrationService(
        audit_log=audit_log,
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
        release_evidence_gateway=FakeReleaseEvidenceGateway(manifest=manifest),
        release_evidence_config=release_evidence_config(),
        release_evidence_notifications=notifications,
        release_evidence_notification_policy=release_evidence_notification_policy(),
    )

    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=organization_id),
        principal(organization_id, {"admin:release_evidence:retrieve"}),
    )

    assert report.status == "failed"
    assert len(notifications.notifications) == 1
    notification = notifications.notifications[0]
    assert notification.status == "failed"
    assert notification.severity == "critical"
    assert notification.metadata["missing_quality_gates"] == [missing_gate]
    assert [event.action for event in audit_log.recorded_events] == [
        "release_evidence.retrieve_failed",
        "release_evidence.notification_delivered",
    ]
    assert audit_log.recorded_events[-1].metadata["delivery_status"] == "delivered"
    assert audit_log.recorded_events[-1].metadata["channel_type"] == "webhook"


def test_administration_service_audits_notification_delivery_failure() -> None:
    organization_id = uuid4()
    audit_log = FakeAuditLogRepository()
    notifications = FakeReleaseEvidenceNotificationGateway(
        status="failed",
        error_message="webhook timed out",
    )
    service = AdministrationService(
        audit_log=audit_log,
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
        release_evidence_gateway=FakeReleaseEvidenceGateway(
            error_message="No successful ci.yml runs found on main."
        ),
        release_evidence_config=release_evidence_config(),
        release_evidence_notifications=notifications,
        release_evidence_notification_policy=release_evidence_notification_policy(),
    )

    report = service.retrieve_release_evidence(
        RetrieveReleaseEvidenceCommand(organization_id=organization_id),
        principal(organization_id, {"admin:release_evidence:retrieve"}),
    )

    assert report.status == "failed"
    assert len(notifications.notifications) == 1
    assert audit_log.recorded_events[-1].action == "release_evidence.notification_failed"
    assert audit_log.recorded_events[-1].resource_type == "release_evidence_notification"
    assert audit_log.recorded_events[-1].metadata["error_message"] == "webhook timed out"


def test_administration_service_returns_fresh_release_evidence_refresh_status() -> None:
    organization_id = uuid4()
    now = datetime(2026, 8, 17, 18, 0, tzinfo=UTC)
    report = release_evidence_report(
        organization_id,
        status="passed",
        created_at=now - timedelta(minutes=30),
    )
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository([report]),
        release_evidence_config=release_evidence_config(),
    )

    status = service.get_release_evidence_refresh_status(
        GetReleaseEvidenceRefreshStatusQuery(
            organization_id=organization_id,
            stale_after_seconds=86_400,
            refresh_interval_seconds=3_600,
            now=now,
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert status.status == "fresh"
    assert status.stale is False
    assert status.latest_report == report
    assert status.last_successful_report == report
    assert status.last_success_age_seconds == 1_800
    assert status.stale_reasons == ()
    assert status.recommended_action == "wait_until_next_refresh"
    assert "refresh_release_evidence.py" in status.operator_command
    assert status.notification_policy.channel_type == "noop"
    assert "release_evidence.notification_failed" in (
        status.notification_policy.delivery_audit_actions
    )


def test_administration_service_marks_release_evidence_refresh_status_stale() -> None:
    organization_id = uuid4()
    now = datetime(2026, 8, 17, 18, 0, tzinfo=UTC)
    report = release_evidence_report(
        organization_id,
        status="passed",
        created_at=now - timedelta(days=2),
    )
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository([report]),
        release_evidence_config=release_evidence_config(),
    )

    status = service.get_release_evidence_refresh_status(
        GetReleaseEvidenceRefreshStatusQuery(
            organization_id=organization_id,
            stale_after_seconds=86_400,
            refresh_interval_seconds=3_600,
            now=now,
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert status.status == "stale"
    assert status.stale is True
    assert status.last_success_age_seconds == 172_800
    assert status.stale_reasons == ("last_success_older_than_threshold",)
    assert status.recommended_action == "retrieve_now"


def test_administration_service_marks_release_evidence_refresh_status_missing() -> None:
    organization_id = uuid4()
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository(),
        release_evidence_config=release_evidence_config(),
    )

    status = service.get_release_evidence_refresh_status(
        GetReleaseEvidenceRefreshStatusQuery(
            organization_id=organization_id,
            stale_after_seconds=86_400,
            refresh_interval_seconds=3_600,
            now=datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert status.status == "missing"
    assert status.stale is True
    assert status.latest_report is None
    assert status.last_successful_report is None
    assert status.stale_reasons == ("no_reports", "no_successful_report")


def test_administration_service_marks_latest_failed_refresh_status_attention() -> None:
    organization_id = uuid4()
    now = datetime(2026, 8, 17, 18, 0, tzinfo=UTC)
    failed = release_evidence_report(
        organization_id,
        status="failed",
        created_at=now - timedelta(minutes=5),
    )
    passed = release_evidence_report(
        organization_id,
        status="passed",
        created_at=now - timedelta(minutes=20),
    )
    service = AdministrationService(
        audit_log=FakeAuditLogRepository(),
        release_evidence_reports=FakeReleaseEvidenceReportRepository([failed, passed]),
        release_evidence_config=release_evidence_config(),
    )

    status = service.get_release_evidence_refresh_status(
        GetReleaseEvidenceRefreshStatusQuery(
            organization_id=organization_id,
            stale_after_seconds=86_400,
            refresh_interval_seconds=3_600,
            now=now,
        ),
        principal(organization_id, {"admin:release_evidence:read"}),
    )

    assert status.status == "attention"
    assert status.stale is False
    assert status.latest_report == failed
    assert status.last_successful_report == passed
    assert status.stale_reasons == ("latest_report_failed",)
    assert status.recommended_action == "retrieve_now"


def principal(organization_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(uuid4()),
        email="admin@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def admin_organization(organization_id: UUID) -> AdminOrganizationProfile:
    return AdminOrganizationProfile(
        id=organization_id,
        name="ForgeML Local",
        slug="forgeml-local",
        status="active",
        created_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )


def admin_user(
    organization_id: UUID,
    email: str,
    permissions: tuple[str, ...],
) -> AdminUserAccessProfile:
    return AdminUserAccessProfile(
        id=uuid4(),
        email=email,
        display_name=email.split("@", maxsplit=1)[0].replace(".", " ").title(),
        status="active",
        permissions=permissions,
        last_login_at=datetime(2026, 8, 17, 13, 0, tzinfo=UTC),
        created_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )


def admin_runtime_config() -> AdminControlsRuntimeConfig:
    return AdminControlsRuntimeConfig(
        environment="local",
        docs_enabled=True,
        rate_limit_enabled=True,
        request_logging_enabled=True,
        structured_logging_enabled=True,
        readiness_checks_enabled=False,
        external_training_profiles_enabled=True,
        release_evidence_provider="local_manifest",
        release_evidence_repository="coreyheckel3/ml-platform",
        release_evidence_branch="main",
        release_evidence_workflow="ci.yml",
        release_evidence_artifact_name="forgeml-release-manifest",
        object_storage_endpoint="http://localhost:9000",
        redis_url="redis://localhost:6379/0",
        mlflow_tracking_uri="http://localhost:5000",
        airflow_orchestration_enabled=False,
        cors_origin_count=1,
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=2_592_000,
        jwt_issuer="forgeml",
    )


def release_evidence_config() -> ReleaseEvidenceRetrievalConfig:
    return ReleaseEvidenceRetrievalConfig(
        provider="github_actions",
        repository="coreyheckel3/ml-platform",
        branch="main",
        workflow="ci.yml",
        artifact_name="forgeml-release-manifest",
    )


def release_evidence_notification_policy() -> ReleaseEvidenceNotificationPolicy:
    return ReleaseEvidenceNotificationPolicy(
        enabled=True,
        channel_type="webhook",
        target="https://hooks.example.com/...",
        failure_statuses=("failed",),
        escalation_window_seconds=1_800,
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


def release_evidence_report(
    organization_id: UUID,
    *,
    status: str,
    created_at: datetime | None = None,
) -> ReleaseEvidenceReport:
    return ReleaseEvidenceReport(
        id=uuid4(),
        organization_id=organization_id,
        requested_by_user_id="user-1",
        provider="github_actions",
        status=status,
        repository="coreyheckel3/ml-platform",
        branch="main",
        workflow="ci.yml",
        artifact_name="forgeml-release-manifest",
        run_id="12345",
        run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        manifest_git_sha="a" * 40,
        manifest_git_branch="main",
        ci_run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        artifact_count=len(RELEASE_EVIDENCE_REQUIRED_ARTIFACTS),
        quality_gate_count=len(RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES),
        missing_artifacts=(),
        missing_quality_gates=(),
        comparison={"passed": status == "passed"},
        manifest_summary={"git_sha": "a" * 40},
        report={"schema_version": "forgeml.release_evidence_retrieval.v1"},
        error_message=None,
        created_at=created_at or datetime.now(UTC),
    )


def release_manifest(
    *,
    quality_gates: tuple[str, ...] = RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES,
) -> dict[str, object]:
    return {
        "schema_version": "forgeml.release_manifest.v1",
        "release": {
            "version": "0.1.0",
            "created_at": "2026-08-17T00:00:00Z",
            "ci_run_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        },
        "source": {"git_sha": "a" * 40, "git_branch": "main", "dirty": False},
        "artifacts": [
            {"name": name} for name in RELEASE_EVIDENCE_REQUIRED_ARTIFACTS
        ],
        "quality_gates": [{"name": name, "required": True} for name in quality_gates],
        "images": [{"name": "backend"}, {"name": "frontend"}],
        "evidence": [{"kind": "ci_run"}],
    }
