from typing import Protocol
from uuid import UUID

from forgeml.modules.drift_detection.domain.entities import (
    DriftAnalysisResult,
    DriftFeatureResult,
    DriftProfile,
    DriftReport,
    InferenceEndpointDriftReference,
)


class DriftDetectionRepository(Protocol):
    def add_profile(self, profile: DriftProfile) -> DriftProfile:
        raise NotImplementedError

    def get_profile(self, profile_id: UUID) -> DriftProfile | None:
        raise NotImplementedError

    def list_profiles(self, organization_id: UUID, project_id: UUID) -> list[DriftProfile]:
        raise NotImplementedError

    def profile_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        raise NotImplementedError

    def get_endpoint_reference(
        self,
        endpoint_id: UUID,
    ) -> InferenceEndpointDriftReference | None:
        raise NotImplementedError

    def list_inference_payload_samples(
        self,
        endpoint_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        raise NotImplementedError

    def add_report(self, report: DriftReport) -> DriftReport:
        raise NotImplementedError

    def list_reports_for_profile(self, profile_id: UUID) -> list[DriftReport]:
        raise NotImplementedError

    def list_reports_for_project(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[DriftReport]:
        raise NotImplementedError

    def get_report(self, report_id: UUID) -> DriftReport | None:
        raise NotImplementedError

    def add_feature_results(
        self,
        feature_results: list[DriftFeatureResult],
    ) -> list[DriftFeatureResult]:
        raise NotImplementedError

    def list_feature_results(self, report_id: UUID) -> list[DriftFeatureResult]:
        raise NotImplementedError


class DriftAnalyzer(Protocol):
    def analyze(
        self,
        *,
        report_id: UUID,
        baseline_profile: dict[str, object],
        production_samples: list[dict[str, object]],
        default_threshold: float,
    ) -> DriftAnalysisResult:
        raise NotImplementedError
