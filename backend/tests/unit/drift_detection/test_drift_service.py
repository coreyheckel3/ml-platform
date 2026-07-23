from uuid import UUID, uuid4

import pytest

from forgeml.modules.drift_detection.application.services import (
    CreateDriftProfileCommand,
    DriftDetectionService,
    RunDriftReportCommand,
)
from forgeml.modules.drift_detection.domain.entities import (
    DriftAnalysisResult,
    DriftFeatureResult,
    DriftFeatureType,
    DriftProfile,
    DriftReport,
    InferenceEndpointDriftReference,
)
from forgeml.platform.domain.errors import ConflictError, DomainValidationError
from forgeml.platform.security.rbac import Principal


class FakeDriftRepository:
    def __init__(self) -> None:
        self.profiles: dict[UUID, DriftProfile] = {}
        self.reports: dict[UUID, DriftReport] = {}
        self.feature_results: list[DriftFeatureResult] = []
        self.endpoint_references: dict[UUID, InferenceEndpointDriftReference] = {}
        self.samples: dict[UUID, list[dict[str, object]]] = {}

    def add_profile(self, profile: DriftProfile) -> DriftProfile:
        self.profiles[profile.id] = profile
        return profile

    def get_profile(self, profile_id: UUID) -> DriftProfile | None:
        return self.profiles.get(profile_id)

    def list_profiles(self, organization_id: UUID, project_id: UUID) -> list[DriftProfile]:
        return [
            profile
            for profile in self.profiles.values()
            if profile.organization_id == organization_id and profile.project_id == project_id
        ]

    def profile_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return any(
            profile.organization_id == organization_id
            and profile.project_id == project_id
            and profile.slug == slug
            for profile in self.profiles.values()
        )

    def get_endpoint_reference(
        self,
        endpoint_id: UUID,
    ) -> InferenceEndpointDriftReference | None:
        return self.endpoint_references.get(endpoint_id)

    def list_inference_payload_samples(
        self,
        endpoint_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        return self.samples.get(endpoint_id, [])[:limit]

    def add_report(self, report: DriftReport) -> DriftReport:
        self.reports[report.id] = report
        return report

    def list_reports_for_profile(self, profile_id: UUID) -> list[DriftReport]:
        return [
            report for report in self.reports.values() if report.drift_profile_id == profile_id
        ]

    def list_reports_for_project(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[DriftReport]:
        return [
            report
            for report in self.reports.values()
            if report.organization_id == organization_id and report.project_id == project_id
        ]

    def get_report(self, report_id: UUID) -> DriftReport | None:
        return self.reports.get(report_id)

    def add_feature_results(
        self,
        feature_results: list[DriftFeatureResult],
    ) -> list[DriftFeatureResult]:
        self.feature_results.extend(feature_results)
        return feature_results

    def list_feature_results(self, report_id: UUID) -> list[DriftFeatureResult]:
        return [result for result in self.feature_results if result.drift_report_id == report_id]


class FakeDriftAnalyzer:
    def analyze(
        self,
        *,
        report_id: UUID,
        baseline_profile: dict[str, object],
        production_samples: list[dict[str, object]],
        default_threshold: float,
    ) -> DriftAnalysisResult:
        feature = DriftFeatureResult(
            id=uuid4(),
            drift_report_id=report_id,
            feature_name="amount",
            feature_type=DriftFeatureType.NUMERIC,
            drift_score=0.42,
            threshold=default_threshold,
            drift_detected=True,
            statistics={"observed_mean": 142.0},
        )
        return DriftAnalysisResult(
            drift_score=0.42,
            drifted_feature_count=1,
            evaluated_feature_count=1,
            summary={"max_feature_score": 0.42},
            feature_results=[feature],
        )


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_drift_service_creates_profile_and_runs_report() -> None:
    repository = FakeDriftRepository()
    service = DriftDetectionService(repository=repository, analyzer=FakeDriftAnalyzer())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    endpoint_id = uuid4()
    repository.endpoint_references[endpoint_id] = InferenceEndpointDriftReference(
        endpoint_id=endpoint_id,
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=uuid4(),
        deployment_revision_id=uuid4(),
        endpoint_name="Fraud Risk Online",
        route_path="/inference/fraud-risk-online",
    )
    repository.samples[endpoint_id] = [{"amount": 142.0}]
    actor = principal(
        organization_id,
        user_id,
        {
            "drift_profiles:create",
            "drift_profiles:read",
            "drift_reports:create",
            "drift_reports:read",
        },
    )

    profile = service.create_profile(
        CreateDriftProfileCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Baseline",
            description="Fraud production reference.",
            model_version_id=None,
            dataset_version_id=None,
            baseline_profile={"amount": {"type": "numeric", "mean": 100.0, "std": 20.0}},
            created_by=user_id,
        ),
        actor,
    )
    report = service.run_report(
        RunDriftReportCommand(
            drift_profile_id=profile.id,
            endpoint_id=endpoint_id,
            window_seconds=3600,
            drift_threshold=0.2,
            sample_limit=200,
            report_uri="s3://forgeml/reports/drift/fraud/report.json",
        ),
        actor,
    )

    assert profile.slug == "fraud-baseline"
    assert report.drift_score == 0.42
    assert report.summary["endpoint_name"] == "Fraud Risk Online"
    assert service.list_feature_results(report.id, actor)[0].feature_name == "amount"


def test_drift_service_rejects_duplicate_profile_slug() -> None:
    repository = FakeDriftRepository()
    service = DriftDetectionService(repository=repository, analyzer=FakeDriftAnalyzer())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"drift_profiles:create"})
    command = CreateDriftProfileCommand(
        organization_id=organization_id,
        project_id=project_id,
        name="Fraud Baseline",
        description="",
        model_version_id=None,
        dataset_version_id=None,
        baseline_profile={"amount": {"type": "numeric", "mean": 100.0, "std": 20.0}},
        created_by=user_id,
    )

    service.create_profile(command, actor)

    with pytest.raises(ConflictError):
        service.create_profile(command, actor)


def test_drift_service_requires_production_samples() -> None:
    repository = FakeDriftRepository()
    service = DriftDetectionService(repository=repository, analyzer=FakeDriftAnalyzer())
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    endpoint_id = uuid4()
    repository.endpoint_references[endpoint_id] = InferenceEndpointDriftReference(
        endpoint_id=endpoint_id,
        organization_id=organization_id,
        project_id=project_id,
        deployment_id=uuid4(),
        deployment_revision_id=uuid4(),
        endpoint_name="Fraud Risk Online",
        route_path="/inference/fraud-risk-online",
    )
    actor = principal(
        organization_id,
        user_id,
        {"drift_profiles:create", "drift_reports:create"},
    )
    profile = service.create_profile(
        CreateDriftProfileCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Baseline",
            description="",
            model_version_id=None,
            dataset_version_id=None,
            baseline_profile={"amount": {"type": "numeric", "mean": 100.0, "std": 20.0}},
            created_by=user_id,
        ),
        actor,
    )

    with pytest.raises(DomainValidationError):
        service.run_report(
            RunDriftReportCommand(
                drift_profile_id=profile.id,
                endpoint_id=endpoint_id,
                window_seconds=3600,
                drift_threshold=0.2,
                sample_limit=200,
                report_uri="",
            ),
            actor,
        )
