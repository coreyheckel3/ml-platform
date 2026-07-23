from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.modules.drift_detection.api.routes import get_drift_detection_service
from forgeml.modules.drift_detection.domain.entities import (
    DriftFeatureResult,
    DriftFeatureType,
    DriftProfile,
    DriftProfileStatus,
    DriftReport,
    DriftReportStatus,
)
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.security.rbac import Principal


@dataclass
class FakeDriftDetectionService:
    organization_id: UUID
    project_id: UUID
    user_id: UUID
    profile_id: UUID
    report_id: UUID
    endpoint_id: UUID
    deployment_id: UUID
    revision_id: UUID
    feature_result_id: UUID

    def create_profile(self, command, principal):
        assert command.name == "Fraud Baseline"
        return self._profile()

    def list_profiles(self, project_id, principal):
        assert project_id == self.project_id
        return [self._profile()]

    def run_report(self, command, principal):
        assert command.endpoint_id == self.endpoint_id
        return self._report()

    def list_reports_for_profile(self, profile_id, principal):
        assert profile_id == self.profile_id
        return [self._report()]

    def list_reports_for_project(self, project_id, principal):
        assert project_id == self.project_id
        return [self._report()]

    def list_feature_results(self, report_id, principal):
        assert report_id == self.report_id
        return [
            DriftFeatureResult(
                id=self.feature_result_id,
                drift_report_id=self.report_id,
                feature_name="amount",
                feature_type=DriftFeatureType.NUMERIC,
                drift_score=0.42,
                threshold=0.2,
                drift_detected=True,
                statistics={"observed_mean": 142.0},
            )
        ]

    def _profile(self) -> DriftProfile:
        return DriftProfile(
            id=self.profile_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            name="Fraud Baseline",
            slug="fraud-baseline",
            description="Fraud production reference.",
            model_version_id=None,
            dataset_version_id=None,
            baseline_profile={"amount": {"type": "numeric", "mean": 100.0, "std": 20.0}},
            status=DriftProfileStatus.ACTIVE,
            created_by=self.user_id,
        )

    def _report(self) -> DriftReport:
        return DriftReport(
            id=self.report_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            drift_profile_id=self.profile_id,
            endpoint_id=self.endpoint_id,
            deployment_id=self.deployment_id,
            deployment_revision_id=self.revision_id,
            status=DriftReportStatus.COMPLETED,
            drift_score=0.42,
            drifted_feature_count=1,
            evaluated_feature_count=1,
            window_seconds=3600,
            drift_threshold=0.2,
            summary={"endpoint_name": "Fraud Risk Online"},
            report_uri="s3://forgeml/reports/drift/fraud/report.json",
            error_message=None,
        )


def test_drift_routes_expose_profile_report_and_feature_lifecycle() -> None:
    organization_id = uuid4()
    user_id = uuid4()
    service = FakeDriftDetectionService(
        organization_id=organization_id,
        project_id=uuid4(),
        user_id=user_id,
        profile_id=uuid4(),
        report_id=uuid4(),
        endpoint_id=uuid4(),
        deployment_id=uuid4(),
        revision_id=uuid4(),
        feature_result_id=uuid4(),
    )
    app = create_app()
    app.dependency_overrides[get_drift_detection_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset({"*"}),
    )
    client = TestClient(app)

    created = client.post(
        f"/api/v1/projects/{service.project_id}/drift-profiles",
        json={
            "name": "Fraud Baseline",
            "description": "Fraud production reference.",
            "baseline_profile": {
                "amount": {"type": "numeric", "mean": 100.0, "std": 20.0}
            },
        },
    )
    profiles = client.get(f"/api/v1/projects/{service.project_id}/drift-profiles")
    report = client.post(
        f"/api/v1/drift-profiles/{service.profile_id}/reports",
        json={
            "endpoint_id": str(service.endpoint_id),
            "window_seconds": 3600,
            "drift_threshold": 0.2,
            "sample_limit": 200,
            "report_uri": "s3://forgeml/reports/drift/fraud/report.json",
        },
    )
    profile_reports = client.get(f"/api/v1/drift-profiles/{service.profile_id}/reports")
    project_reports = client.get(f"/api/v1/projects/{service.project_id}/drift-reports")
    feature_results = client.get(f"/api/v1/drift-reports/{service.report_id}/features")

    assert created.status_code == 201
    assert created.json()["slug"] == "fraud-baseline"
    assert profiles.status_code == 200
    assert profiles.json()["items"][0]["name"] == "Fraud Baseline"
    assert report.status_code == 201
    assert report.json()["drift_score"] == 0.42
    assert profile_reports.status_code == 200
    assert project_reports.status_code == 200
    assert feature_results.status_code == 200
    assert feature_results.json()["items"][0]["feature_name"] == "amount"
