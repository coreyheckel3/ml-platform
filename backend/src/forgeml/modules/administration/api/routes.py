from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from forgeml.modules.administration.api.schemas import (
    AuditLogEntryResponse,
    AuditLogListResponse,
    ReleaseEvidenceReportListResponse,
    ReleaseEvidenceReportResponse,
)
from forgeml.modules.administration.application.services import (
    AdministrationService,
    GetReleaseEvidenceReportQuery,
    ListAuditLogQuery,
    ListReleaseEvidenceReportsQuery,
    ReleaseEvidenceRetrievalConfig,
    RetrieveReleaseEvidenceCommand,
)
from forgeml.modules.administration.domain.entities import (
    AuditLogEntry,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyReleaseEvidenceReportRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.domain.errors import DomainValidationError
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
        release_evidence_reports=SqlAlchemyReleaseEvidenceReportRepository(session),
        release_evidence_gateway=_release_evidence_gateway_from_settings(settings),
        release_evidence_config=_release_evidence_config_from_settings(settings),
    )


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
