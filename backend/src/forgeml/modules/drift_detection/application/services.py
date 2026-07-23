from dataclasses import dataclass
from uuid import UUID, uuid4

from forgeml.modules.drift_detection.domain.entities import (
    DriftFeatureResult,
    DriftProfile,
    DriftProfileStatus,
    DriftReport,
    DriftReportStatus,
)
from forgeml.modules.drift_detection.domain.policies import (
    build_drift_profile_slug,
    validate_baseline_profile,
    validate_drift_profile_name,
    validate_drift_threshold,
    validate_drift_window,
    validate_sample_count,
)
from forgeml.modules.drift_detection.repositories.interfaces import (
    DriftAnalyzer,
    DriftDetectionRepository,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateDriftProfileCommand:
    organization_id: UUID
    project_id: UUID
    name: str
    description: str
    model_version_id: UUID | None
    dataset_version_id: UUID | None
    baseline_profile: dict[str, object]
    created_by: UUID


@dataclass(frozen=True)
class RunDriftReportCommand:
    drift_profile_id: UUID
    endpoint_id: UUID
    window_seconds: int
    drift_threshold: float
    sample_limit: int
    report_uri: str


class DriftDetectionService:
    def __init__(
        self,
        *,
        repository: DriftDetectionRepository,
        analyzer: DriftAnalyzer,
    ) -> None:
        self._repository = repository
        self._analyzer = analyzer

    def create_profile(
        self,
        command: CreateDriftProfileCommand,
        principal: Principal,
    ) -> DriftProfile:
        self._require(principal, "drift_profiles:create")
        self._require_same_organization(command.organization_id, principal)
        validate_drift_profile_name(command.name)
        validate_baseline_profile(command.baseline_profile)
        slug = build_drift_profile_slug(command.name)
        if self._repository.profile_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("A drift profile with this name already exists in the project.")
        profile = DriftProfile(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            model_version_id=command.model_version_id,
            dataset_version_id=command.dataset_version_id,
            baseline_profile=command.baseline_profile,
            status=DriftProfileStatus.ACTIVE,
            created_by=command.created_by,
        )
        return self._repository.add_profile(profile)

    def list_profiles(self, project_id: UUID, principal: Principal) -> list[DriftProfile]:
        self._require(principal, "drift_profiles:read")
        return self._repository.list_profiles(UUID(principal.organization_id), project_id)

    def run_report(
        self,
        command: RunDriftReportCommand,
        principal: Principal,
    ) -> DriftReport:
        self._require(principal, "drift_reports:create")
        validate_drift_window(command.window_seconds)
        validate_drift_threshold(command.drift_threshold)
        profile = self._get_scoped_profile(command.drift_profile_id, principal)
        endpoint = self._repository.get_endpoint_reference(command.endpoint_id)
        if endpoint is None:
            raise ResourceNotFoundError("Inference endpoint was not found.")
        if (
            endpoint.organization_id != profile.organization_id
            or endpoint.project_id != profile.project_id
        ):
            raise ResourceNotFoundError("Inference endpoint was not found.")
        samples = self._repository.list_inference_payload_samples(
            endpoint.endpoint_id,
            command.sample_limit,
        )
        validate_sample_count(len(samples))
        report_id = uuid4()
        analysis = self._analyzer.analyze(
            report_id=report_id,
            baseline_profile=profile.baseline_profile,
            production_samples=samples,
            default_threshold=command.drift_threshold,
        )
        report = DriftReport(
            id=report_id,
            organization_id=profile.organization_id,
            project_id=profile.project_id,
            drift_profile_id=profile.id,
            endpoint_id=endpoint.endpoint_id,
            deployment_id=endpoint.deployment_id,
            deployment_revision_id=endpoint.deployment_revision_id,
            status=DriftReportStatus.COMPLETED,
            drift_score=analysis.drift_score,
            drifted_feature_count=analysis.drifted_feature_count,
            evaluated_feature_count=analysis.evaluated_feature_count,
            window_seconds=command.window_seconds,
            drift_threshold=command.drift_threshold,
            summary={
                **analysis.summary,
                "endpoint_name": endpoint.endpoint_name,
                "route_path": endpoint.route_path,
                "sample_count": len(samples),
            },
            report_uri=command.report_uri.strip(),
            error_message=None,
        )
        saved = self._repository.add_report(report)
        self._repository.add_feature_results(analysis.feature_results)
        return saved

    def list_reports_for_profile(
        self,
        profile_id: UUID,
        principal: Principal,
    ) -> list[DriftReport]:
        self._require(principal, "drift_reports:read")
        profile = self._get_scoped_profile(profile_id, principal)
        return self._repository.list_reports_for_profile(profile.id)

    def list_reports_for_project(
        self,
        project_id: UUID,
        principal: Principal,
    ) -> list[DriftReport]:
        self._require(principal, "drift_reports:read")
        return self._repository.list_reports_for_project(
            UUID(principal.organization_id),
            project_id,
        )

    def list_feature_results(
        self,
        report_id: UUID,
        principal: Principal,
    ) -> list[DriftFeatureResult]:
        self._require(principal, "drift_reports:read")
        report = self._repository.get_report(report_id)
        if report is None or str(report.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Drift report was not found.")
        return self._repository.list_feature_results(report.id)

    def _get_scoped_profile(self, profile_id: UUID, principal: Principal) -> DriftProfile:
        profile = self._repository.get_profile(profile_id)
        if profile is None or str(profile.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Drift profile was not found.")
        return profile

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage drift detection.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage drift profiles in another organization.")
