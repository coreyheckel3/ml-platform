from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.administration.api.routes import get_administration_service
from forgeml.modules.administration.application.services import (
    GetPlatformAdminControlsQuery,
    GetReleaseEvidenceRefreshStatusQuery,
    GetReleaseEvidenceReportQuery,
    ListAuditLogQuery,
    ListReleaseEvidenceReportsQuery,
    ReleaseEvidenceRefreshStatus,
    RetrieveReleaseEvidenceCommand,
)
from forgeml.modules.administration.domain.entities import (
    AdminControlPlaneStats,
    AdminEnvironmentSummary,
    AdminOrganizationProfile,
    AdminPermissionGroupSummary,
    AdminPermissionSummary,
    AdminRolePresetSummary,
    AdminSafeguardSummary,
    AdminUserAccessProfile,
    AuditLogEntry,
    PlatformAdminControls,
    ReleaseEvidenceReport,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.notifications import ReleaseEvidenceNotificationPolicy
from forgeml.platform.security.rbac import Principal


class FakeAdministrationService:
    def __init__(self) -> None:
        self.organization_id = uuid4()
        self.entry_id = uuid4()
        self.report_id = uuid4()
        self.query: ListAuditLogQuery | None = None
        self.release_reports_query: ListReleaseEvidenceReportsQuery | None = None
        self.release_report_query: GetReleaseEvidenceReportQuery | None = None
        self.refresh_status_query: GetReleaseEvidenceRefreshStatusQuery | None = None
        self.retrieve_command: RetrieveReleaseEvidenceCommand | None = None
        self.admin_controls_query: GetPlatformAdminControlsQuery | None = None

    def get_platform_admin_controls(
        self,
        query: GetPlatformAdminControlsQuery,
        principal: Principal,
    ) -> PlatformAdminControls:
        self.admin_controls_query = query
        return PlatformAdminControls(
            organization=AdminOrganizationProfile(
                id=self.organization_id,
                name="ForgeML Local",
                slug="forgeml-local",
                status="active",
                created_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
            ),
            users=(
                AdminUserAccessProfile(
                    id=uuid4(),
                    email="admin@forgeml.dev",
                    display_name="Platform Admin",
                    status="active",
                    permissions=("*",),
                    last_login_at=datetime(2026, 8, 17, 12, 30, tzinfo=UTC),
                    created_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
                ),
            ),
            role_presets=(
                AdminRolePresetSummary(
                    code="platform_admin",
                    name="Platform Admin",
                    description="Full ForgeML platform administration across all modules.",
                    permissions=("*",),
                    permission_count=1,
                    assigned_user_count=1,
                    granted_to_current_principal=True,
                ),
            ),
            permission_groups=(
                AdminPermissionGroupSummary(
                    module="administration",
                    permission_count=1,
                    granted_count=1,
                    permissions=(
                        AdminPermissionSummary(
                            code="admin:controls:read",
                            module="administration",
                            action="read",
                            description="Read organization controls.",
                            granted_to_current_principal=True,
                        ),
                    ),
                ),
            ),
            environment=AdminEnvironmentSummary(
                environment="local",
                production_like=False,
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
                object_storage_configured=True,
                redis_configured=True,
                mlflow_tracking_configured=True,
                airflow_orchestration_enabled=False,
                cors_origin_count=1,
                access_token_ttl_seconds=900,
                refresh_token_ttl_seconds=2_592_000,
                jwt_issuer="forgeml",
            ),
            safeguards=(
                AdminSafeguardSummary(
                    label="RBAC mutations",
                    status="read-only",
                    detail="Role changes require an audited workflow.",
                    evidence="contracts/security/permission-catalog.v1.json",
                ),
            ),
            operator_commands=("make production-readiness",),
            stats=AdminControlPlaneStats(
                total_users=1,
                active_users=1,
                disabled_users=0,
                project_count=3,
                audit_event_count=7,
                release_evidence_report_count=2,
                role_preset_count=1,
                permission_count=1,
                permission_group_count=1,
            ),
        )

    def list_audit_log(
        self,
        query: ListAuditLogQuery,
        principal: Principal,
    ) -> list[AuditLogEntry]:
        self.query = query
        return [
            AuditLogEntry(
                id=self.entry_id,
                organization_id=self.organization_id,
                actor_type="user",
                actor_id="user-1",
                action="model_versions.review",
                resource_type="model_version",
                resource_id="model-version-1",
                metadata={"decision": "approved"},
                created_at=datetime(2026, 7, 26, 12, 30, tzinfo=UTC),
            )
        ]

    def list_release_evidence_reports(
        self,
        query: ListReleaseEvidenceReportsQuery,
        principal: Principal,
    ) -> list[ReleaseEvidenceReport]:
        self.release_reports_query = query
        return [self._release_evidence_report()]

    def get_release_evidence_report(
        self,
        query: GetReleaseEvidenceReportQuery,
        principal: Principal,
    ) -> ReleaseEvidenceReport:
        self.release_report_query = query
        return self._release_evidence_report()

    def retrieve_release_evidence(
        self,
        command: RetrieveReleaseEvidenceCommand,
        principal: Principal,
    ) -> ReleaseEvidenceReport:
        self.retrieve_command = command
        return self._release_evidence_report()

    def get_release_evidence_refresh_status(
        self,
        query: GetReleaseEvidenceRefreshStatusQuery,
        principal: Principal,
    ) -> ReleaseEvidenceRefreshStatus:
        self.refresh_status_query = query
        report = self._release_evidence_report()
        return ReleaseEvidenceRefreshStatus(
            organization_id=self.organization_id,
            provider="github_actions",
            repository="coreyheckel3/ml-platform",
            branch="main",
            workflow="ci.yml",
            artifact_name="forgeml-release-manifest",
            status="fresh",
            stale=False,
            stale_after_seconds=query.stale_after_seconds,
            refresh_interval_seconds=query.refresh_interval_seconds,
            latest_report=report,
            last_successful_report=report,
            latest_report_age_seconds=1_800,
            last_success_age_seconds=1_800,
            next_refresh_at=datetime(2026, 8, 17, 13, 30, tzinfo=UTC),
            checked_at=datetime(2026, 8, 17, 13, 0, tzinfo=UTC),
            stale_reasons=(),
            recommended_action="wait_until_next_refresh",
            operator_command=(
                "PYTHONPATH=backend/src:. python "
                "scripts/ops/refresh_release_evidence.py --base-url "
                "http://127.0.0.1:8001 --once --stale-after-seconds 86400"
            ),
            notification_policy=ReleaseEvidenceNotificationPolicy(
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
            ),
        )

    def _release_evidence_report(self) -> ReleaseEvidenceReport:
        return ReleaseEvidenceReport(
            id=self.report_id,
            organization_id=self.organization_id,
            requested_by_user_id="user-1",
            provider="github_actions",
            status="passed",
            repository="coreyheckel3/ml-platform",
            branch="main",
            workflow="ci.yml",
            artifact_name="forgeml-release-manifest",
            run_id="12345",
            run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
            manifest_git_sha="abc123",
            manifest_git_branch="main",
            ci_run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
            artifact_count=44,
            quality_gate_count=32,
            missing_artifacts=(),
            missing_quality_gates=(),
            comparison={"passed": True},
            manifest_summary={
                "git_sha": "abc123",
                "artifact_names": [
                    "release_evidence_drilldown_api_contract",
                    "lifecycle_polish_contract",
                ],
            },
            report={
                "schema_version": "forgeml.release_evidence_retrieval.v1",
                "status": "passed",
            },
            error_message=None,
            created_at=datetime(2026, 8, 17, 12, 30, tzinfo=UTC),
        )


def test_platform_admin_controls_route_uses_application_service_contract() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:controls:read"}),
    )
    client = TestClient(app)

    response = client.get("/api/v1/admin/controls")

    assert response.status_code == 200
    assert fake_service.admin_controls_query == GetPlatformAdminControlsQuery(
        organization_id=fake_service.organization_id,
    )
    payload = response.json()
    assert payload["schema_version"] == "forgeml.platform_admin_controls.v1"
    assert payload["organization"]["slug"] == "forgeml-local"
    assert payload["users"][0]["email"] == "admin@forgeml.dev"
    assert payload["users"][0]["role_codes"] == ["platform_admin"]
    assert payload["role_presets"][0]["code"] == "platform_admin"
    assert payload["permission_groups"][0]["permissions"][0]["code"] == (
        "admin:controls:read"
    )
    assert payload["environment"]["release_evidence_provider"] == "local_manifest"
    assert payload["safeguards"][0]["label"] == "RBAC mutations"
    assert payload["operator_commands"] == ["make production-readiness"]
    assert payload["stats"]["project_count"] == 3


def test_administration_audit_log_route_uses_application_service_contract() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:audit_log:read"}),
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/audit-log",
        params={
            "actor_type": "user",
            "action": "model_versions.review",
            "resource_type": "model_version",
            "limit": 25,
        },
    )

    assert response.status_code == 200
    assert fake_service.query == ListAuditLogQuery(
        organization_id=fake_service.organization_id,
        actor_type="user",
        action="model_versions.review",
        resource_type="model_version",
        limit=25,
    )
    assert response.json() == {
        "items": [
            {
                "id": str(fake_service.entry_id),
                "organization_id": str(fake_service.organization_id),
                "actor_type": "user",
                "actor_id": "user-1",
                "action": "model_versions.review",
                "resource_type": "model_version",
                "resource_id": "model-version-1",
                "metadata": {"decision": "approved"},
                "created_at": "2026-07-26T12:30:00+00:00",
            }
        ],
        "next_cursor": None,
    }


def test_administration_audit_log_route_validates_limit() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:audit_log:read"}),
    )
    client = TestClient(app)

    response = client.get("/api/v1/admin/audit-log", params={"limit": 500})

    assert response.status_code == 422


def test_release_evidence_reports_route_uses_application_service_contract() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:release_evidence:read"}),
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/release-evidence/reports",
        params={"status": "passed", "limit": 5},
    )

    assert response.status_code == 200
    assert fake_service.release_reports_query == ListReleaseEvidenceReportsQuery(
        organization_id=fake_service.organization_id,
        status="passed",
        limit=5,
    )
    assert response.json() == {
        "items": [release_evidence_report_response(fake_service)],
        "next_cursor": None,
    }


def test_release_evidence_report_route_returns_single_drilldown() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:release_evidence:read"}),
    )
    client = TestClient(app)

    response = client.get(f"/api/v1/admin/release-evidence/reports/{fake_service.report_id}")

    assert response.status_code == 200
    assert fake_service.release_report_query == GetReleaseEvidenceReportQuery(
        organization_id=fake_service.organization_id,
        report_id=fake_service.report_id,
    )
    assert response.json() == release_evidence_report_response(fake_service)


def test_release_evidence_retrieval_route_returns_created_report() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:release_evidence:retrieve"}),
    )
    client = TestClient(app)

    response = client.post("/api/v1/admin/release-evidence/reports/retrieve", json={})

    assert response.status_code == 201
    assert fake_service.retrieve_command == RetrieveReleaseEvidenceCommand(
        organization_id=fake_service.organization_id,
    )
    assert response.json() == release_evidence_report_response(fake_service)


def test_release_evidence_refresh_status_route_returns_last_success_summary() -> None:
    fake_service = FakeAdministrationService()
    app = create_app()
    app.dependency_overrides[get_administration_service] = lambda: fake_service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="user-1",
        email="admin@example.com",
        organization_id=str(fake_service.organization_id),
        permissions=frozenset({"admin:release_evidence:read"}),
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/release-evidence/refresh/status",
        params={
            "stale_after_seconds": 86_400,
            "refresh_interval_seconds": 3_600,
        },
    )

    assert response.status_code == 200
    assert fake_service.refresh_status_query == GetReleaseEvidenceRefreshStatusQuery(
        organization_id=fake_service.organization_id,
        stale_after_seconds=86_400,
        refresh_interval_seconds=3_600,
    )
    payload = response.json()
    assert payload["schema_version"] == "forgeml.release_evidence_refresh_status.v1"
    assert payload["status"] == "fresh"
    assert payload["stale"] is False
    assert payload["latest_report"] == release_evidence_report_response(fake_service)
    assert payload["last_successful_report"] == release_evidence_report_response(fake_service)
    assert payload["last_success_age_seconds"] == 1_800
    assert payload["next_refresh_at"] == "2026-08-17T13:30:00+00:00"
    assert payload["recommended_action"] == "wait_until_next_refresh"
    assert "refresh_release_evidence.py" in payload["operator_command"]
    assert payload["notification_policy"] == {
        "enabled": True,
        "channel_type": "webhook",
        "target": "https://hooks.example.com/...",
        "failure_statuses": ["failed"],
        "escalation_window_seconds": 1_800,
        "escalation_command": (
            "PYTHONPATH=backend/src:. python "
            "scripts/ops/refresh_release_evidence.py --base-url "
            "http://127.0.0.1:8001 --once --force"
        ),
        "delivery_audit_actions": [
            "release_evidence.notification_delivered",
            "release_evidence.notification_failed",
            "release_evidence.notification_skipped",
        ],
    }


def release_evidence_report_response(
    fake_service: FakeAdministrationService,
) -> dict[str, object]:
    return {
        "id": str(fake_service.report_id),
        "organization_id": str(fake_service.organization_id),
        "requested_by_user_id": "user-1",
        "provider": "github_actions",
        "status": "passed",
        "repository": "coreyheckel3/ml-platform",
        "branch": "main",
        "workflow": "ci.yml",
        "artifact_name": "forgeml-release-manifest",
        "run_id": "12345",
        "run_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        "manifest_git_sha": "abc123",
        "manifest_git_branch": "main",
        "ci_run_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        "artifact_count": 44,
        "quality_gate_count": 32,
        "missing_artifacts": [],
        "missing_quality_gates": [],
        "comparison": {"passed": True},
        "manifest_summary": {
            "git_sha": "abc123",
            "artifact_names": [
                "release_evidence_drilldown_api_contract",
                "lifecycle_polish_contract",
            ],
        },
        "report": {
            "schema_version": "forgeml.release_evidence_retrieval.v1",
            "status": "passed",
        },
        "error_message": None,
        "created_at": "2026-08-17T12:30:00+00:00",
    }
