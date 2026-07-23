from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.drift_detection.domain.entities import (
    DriftFeatureResult,
    DriftFeatureType,
    DriftProfile,
    DriftProfileStatus,
    DriftReport,
    DriftReportStatus,
    InferenceEndpointDriftReference,
)
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import (
    DriftFeatureResultModel,
    DriftProfileModel,
    DriftReportModel,
)
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceRequestLogModel,
)


class SqlAlchemyDriftDetectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_profile(self, profile: DriftProfile) -> DriftProfile:
        model = DriftProfileModel(
            id=profile.id,
            organization_id=profile.organization_id,
            project_id=profile.project_id,
            name=profile.name,
            slug=profile.slug,
            description=profile.description,
            model_version_id=profile.model_version_id,
            dataset_version_id=profile.dataset_version_id,
            baseline_profile_json=profile.baseline_profile,
            status=profile.status.value,
            created_by=profile.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _profile_to_domain(model)

    def get_profile(self, profile_id: UUID) -> DriftProfile | None:
        model = self._session.get(DriftProfileModel, profile_id)
        return _profile_to_domain(model) if model else None

    def list_profiles(self, organization_id: UUID, project_id: UUID) -> list[DriftProfile]:
        models = self._session.scalars(
            select(DriftProfileModel)
            .where(
                DriftProfileModel.organization_id == organization_id,
                DriftProfileModel.project_id == project_id,
            )
            .order_by(DriftProfileModel.name)
        ).all()
        return [_profile_to_domain(model) for model in models]

    def profile_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(DriftProfileModel.id).where(
                    DriftProfileModel.organization_id == organization_id,
                    DriftProfileModel.project_id == project_id,
                    DriftProfileModel.slug == slug,
                )
            )
            is not None
        )

    def get_endpoint_reference(
        self,
        endpoint_id: UUID,
    ) -> InferenceEndpointDriftReference | None:
        endpoint = self._session.get(InferenceEndpointModel, endpoint_id)
        if endpoint is None:
            return None
        return InferenceEndpointDriftReference(
            endpoint_id=endpoint.id,
            organization_id=endpoint.organization_id,
            project_id=endpoint.project_id,
            deployment_id=endpoint.deployment_id,
            deployment_revision_id=endpoint.deployment_revision_id,
            endpoint_name=endpoint.name,
            route_path=endpoint.route_path,
        )

    def list_inference_payload_samples(
        self,
        endpoint_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        models = self._session.scalars(
            select(InferenceRequestLogModel)
            .where(
                InferenceRequestLogModel.endpoint_id == endpoint_id,
                InferenceRequestLogModel.status == "succeeded",
            )
            .order_by(InferenceRequestLogModel.created_at.desc())
            .limit(limit)
        ).all()
        return [model.input_payload_json for model in models]

    def add_report(self, report: DriftReport) -> DriftReport:
        model = DriftReportModel(
            id=report.id,
            organization_id=report.organization_id,
            project_id=report.project_id,
            drift_profile_id=report.drift_profile_id,
            endpoint_id=report.endpoint_id,
            deployment_id=report.deployment_id,
            deployment_revision_id=report.deployment_revision_id,
            status=report.status.value,
            drift_score=report.drift_score,
            drifted_feature_count=report.drifted_feature_count,
            evaluated_feature_count=report.evaluated_feature_count,
            window_seconds=report.window_seconds,
            drift_threshold=report.drift_threshold,
            summary_json=report.summary,
            report_uri=report.report_uri,
            error_message=report.error_message,
        )
        self._session.add(model)
        self._session.flush()
        return _report_to_domain(model)

    def list_reports_for_profile(self, profile_id: UUID) -> list[DriftReport]:
        models = self._session.scalars(
            select(DriftReportModel)
            .where(DriftReportModel.drift_profile_id == profile_id)
            .order_by(DriftReportModel.created_at.desc())
        ).all()
        return [_report_to_domain(model) for model in models]

    def list_reports_for_project(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[DriftReport]:
        models = self._session.scalars(
            select(DriftReportModel)
            .where(
                DriftReportModel.organization_id == organization_id,
                DriftReportModel.project_id == project_id,
            )
            .order_by(DriftReportModel.created_at.desc())
        ).all()
        return [_report_to_domain(model) for model in models]

    def get_report(self, report_id: UUID) -> DriftReport | None:
        model = self._session.get(DriftReportModel, report_id)
        return _report_to_domain(model) if model else None

    def add_feature_results(
        self,
        feature_results: list[DriftFeatureResult],
    ) -> list[DriftFeatureResult]:
        models = [
            DriftFeatureResultModel(
                id=result.id,
                drift_report_id=result.drift_report_id,
                feature_name=result.feature_name,
                feature_type=result.feature_type.value,
                drift_score=result.drift_score,
                threshold=result.threshold,
                drift_detected=result.drift_detected,
                statistics_json=result.statistics,
            )
            for result in feature_results
        ]
        self._session.add_all(models)
        self._session.flush()
        return [_feature_result_to_domain(model) for model in models]

    def list_feature_results(self, report_id: UUID) -> list[DriftFeatureResult]:
        models = self._session.scalars(
            select(DriftFeatureResultModel)
            .where(DriftFeatureResultModel.drift_report_id == report_id)
            .order_by(DriftFeatureResultModel.drift_score.desc())
        ).all()
        return [_feature_result_to_domain(model) for model in models]


def _profile_to_domain(model: DriftProfileModel) -> DriftProfile:
    return DriftProfile(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        model_version_id=model.model_version_id,
        dataset_version_id=model.dataset_version_id,
        baseline_profile=model.baseline_profile_json,
        status=DriftProfileStatus(model.status),
        created_by=model.created_by,
    )


def _report_to_domain(model: DriftReportModel) -> DriftReport:
    return DriftReport(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        drift_profile_id=model.drift_profile_id,
        endpoint_id=model.endpoint_id,
        deployment_id=model.deployment_id,
        deployment_revision_id=model.deployment_revision_id,
        status=DriftReportStatus(model.status),
        drift_score=float(model.drift_score),
        drifted_feature_count=model.drifted_feature_count,
        evaluated_feature_count=model.evaluated_feature_count,
        window_seconds=model.window_seconds,
        drift_threshold=float(model.drift_threshold),
        summary=model.summary_json,
        report_uri=model.report_uri,
        error_message=model.error_message,
    )


def _feature_result_to_domain(model: DriftFeatureResultModel) -> DriftFeatureResult:
    return DriftFeatureResult(
        id=model.id,
        drift_report_id=model.drift_report_id,
        feature_name=model.feature_name,
        feature_type=DriftFeatureType(model.feature_type),
        drift_score=float(model.drift_score),
        threshold=float(model.threshold),
        drift_detected=model.drift_detected,
        statistics=model.statistics_json,
    )
