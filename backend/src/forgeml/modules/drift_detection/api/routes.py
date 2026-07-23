from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.drift_detection.api.schemas import (
    CreateDriftProfileRequest,
    DriftFeatureResultListResponse,
    DriftFeatureResultResponse,
    DriftProfileListResponse,
    DriftProfileResponse,
    DriftReportListResponse,
    DriftReportResponse,
    RunDriftReportRequest,
)
from forgeml.modules.drift_detection.application.services import (
    CreateDriftProfileCommand,
    DriftDetectionService,
    RunDriftReportCommand,
)
from forgeml.modules.drift_detection.domain.entities import (
    DriftFeatureResult,
    DriftProfile,
    DriftReport,
)
from forgeml.modules.drift_detection.infrastructure.analyzer import LocalDriftAnalyzer
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDriftDetectionRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["drift_detection"])


def get_drift_detection_service(
    session: Session = Depends(get_db_session),
) -> DriftDetectionService:
    return DriftDetectionService(
        repository=SqlAlchemyDriftDetectionRepository(session),
        analyzer=LocalDriftAnalyzer(),
    )


@router.post(
    "/projects/{project_id}/drift-profiles",
    response_model=DriftProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_drift_profile(
    project_id: UUID,
    request: CreateDriftProfileRequest,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftProfileResponse:
    profile = service.create_profile(
        CreateDriftProfileCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            name=request.name,
            description=request.description,
            model_version_id=UUID(request.model_version_id) if request.model_version_id else None,
            dataset_version_id=(
                UUID(request.dataset_version_id) if request.dataset_version_id else None
            ),
            baseline_profile=request.baseline_profile,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _profile_response(profile)


@router.get("/projects/{project_id}/drift-profiles", response_model=DriftProfileListResponse)
def list_drift_profiles(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftProfileListResponse:
    return DriftProfileListResponse(
        items=[
            _profile_response(profile)
            for profile in service.list_profiles(project_id, principal)
        ]
    )


@router.post(
    "/drift-profiles/{profile_id}/reports",
    response_model=DriftReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_drift_report(
    profile_id: UUID,
    request: RunDriftReportRequest,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftReportResponse:
    report = service.run_report(
        RunDriftReportCommand(
            drift_profile_id=profile_id,
            endpoint_id=UUID(request.endpoint_id),
            window_seconds=request.window_seconds,
            drift_threshold=request.drift_threshold,
            sample_limit=request.sample_limit,
            report_uri=request.report_uri,
        ),
        principal,
    )
    return _report_response(report)


@router.get(
    "/drift-profiles/{profile_id}/reports",
    response_model=DriftReportListResponse,
)
def list_drift_reports_for_profile(
    profile_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftReportListResponse:
    return DriftReportListResponse(
        items=[
            _report_response(report)
            for report in service.list_reports_for_profile(profile_id, principal)
        ]
    )


@router.get("/projects/{project_id}/drift-reports", response_model=DriftReportListResponse)
def list_drift_reports_for_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftReportListResponse:
    return DriftReportListResponse(
        items=[
            _report_response(report)
            for report in service.list_reports_for_project(project_id, principal)
        ]
    )


@router.get(
    "/drift-reports/{report_id}/features",
    response_model=DriftFeatureResultListResponse,
)
def list_drift_feature_results(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DriftDetectionService = Depends(get_drift_detection_service),
) -> DriftFeatureResultListResponse:
    return DriftFeatureResultListResponse(
        items=[
            _feature_result_response(feature_result)
            for feature_result in service.list_feature_results(report_id, principal)
        ]
    )


def _profile_response(profile: DriftProfile) -> DriftProfileResponse:
    return DriftProfileResponse(
        id=str(profile.id),
        organization_id=str(profile.organization_id),
        project_id=str(profile.project_id),
        name=profile.name,
        slug=profile.slug,
        description=profile.description,
        model_version_id=str(profile.model_version_id) if profile.model_version_id else None,
        dataset_version_id=str(profile.dataset_version_id) if profile.dataset_version_id else None,
        baseline_profile=profile.baseline_profile,
        status=profile.status.value,
        created_by=str(profile.created_by),
    )


def _report_response(report: DriftReport) -> DriftReportResponse:
    return DriftReportResponse(
        id=str(report.id),
        organization_id=str(report.organization_id),
        project_id=str(report.project_id),
        drift_profile_id=str(report.drift_profile_id),
        endpoint_id=str(report.endpoint_id),
        deployment_id=str(report.deployment_id),
        deployment_revision_id=str(report.deployment_revision_id),
        status=report.status.value,
        drift_score=report.drift_score,
        drifted_feature_count=report.drifted_feature_count,
        evaluated_feature_count=report.evaluated_feature_count,
        window_seconds=report.window_seconds,
        drift_threshold=report.drift_threshold,
        summary=report.summary,
        report_uri=report.report_uri,
        error_message=report.error_message,
    )


def _feature_result_response(
    feature_result: DriftFeatureResult,
) -> DriftFeatureResultResponse:
    return DriftFeatureResultResponse(
        id=str(feature_result.id),
        drift_report_id=str(feature_result.drift_report_id),
        feature_name=feature_result.feature_name,
        feature_type=feature_result.feature_type.value,
        drift_score=feature_result.drift_score,
        threshold=feature_result.threshold,
        drift_detected=feature_result.drift_detected,
        statistics=feature_result.statistics,
    )
