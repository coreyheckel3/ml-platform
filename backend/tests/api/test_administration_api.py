from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.administration.api.routes import get_administration_service
from forgeml.modules.administration.application.services import (
    GetReleaseEvidenceReportQuery,
    ListAuditLogQuery,
    ListReleaseEvidenceReportsQuery,
    RetrieveReleaseEvidenceCommand,
)
from forgeml.modules.administration.domain.entities import (
    AuditLogEntry,
    ReleaseEvidenceReport,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


class FakeAdministrationService:
    def __init__(self) -> None:
        self.organization_id = uuid4()
        self.entry_id = uuid4()
        self.report_id = uuid4()
        self.query: ListAuditLogQuery | None = None
        self.release_reports_query: ListReleaseEvidenceReportsQuery | None = None
        self.release_report_query: GetReleaseEvidenceReportQuery | None = None
        self.retrieve_command: RetrieveReleaseEvidenceCommand | None = None

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
            artifact_count=37,
            quality_gate_count=26,
            missing_artifacts=(),
            missing_quality_gates=(),
            comparison={"passed": True},
            manifest_summary={
                "git_sha": "abc123",
                "artifact_names": ["release_evidence_drilldown_api_contract"],
            },
            report={
                "schema_version": "forgeml.release_evidence_retrieval.v1",
                "status": "passed",
            },
            error_message=None,
            created_at=datetime(2026, 8, 17, 12, 30, tzinfo=UTC),
        )


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
        "artifact_count": 37,
        "quality_gate_count": 26,
        "missing_artifacts": [],
        "missing_quality_gates": [],
        "comparison": {"passed": True},
        "manifest_summary": {
            "git_sha": "abc123",
            "artifact_names": ["release_evidence_drilldown_api_contract"],
        },
        "report": {
            "schema_version": "forgeml.release_evidence_retrieval.v1",
            "status": "passed",
        },
        "error_message": None,
        "created_at": "2026-08-17T12:30:00+00:00",
    }
