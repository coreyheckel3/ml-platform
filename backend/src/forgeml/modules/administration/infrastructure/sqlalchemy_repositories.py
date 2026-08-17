from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from forgeml.modules.administration.domain.entities import (
    AuditLogEntry,
    AuditLogEvent,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.infrastructure.sqlalchemy_models import (
    AuditLogModel,
    ReleaseEvidenceReportModel,
)
from forgeml.modules.administration.repositories.interfaces import (
    AuditLogFilters,
    ReleaseEvidenceReportFilters,
)


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_entries(
        self,
        organization_id: UUID,
        *,
        filters: AuditLogFilters,
        limit: int,
    ) -> list[AuditLogEntry]:
        statement = (
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.desc(), AuditLogModel.id.desc())
            .limit(limit)
        )
        statement = _apply_filters(statement, filters)
        models = self._session.scalars(statement).all()
        return [_to_domain(model) for model in models]

    def record(self, event: AuditLogEvent) -> AuditLogEntry:
        model = AuditLogModel(
            id=uuid4(),
            organization_id=event.organization_id,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata_json=dict(event.metadata),
            created_at=datetime.now(UTC),
        )
        self._session.add(model)
        self._session.flush()
        return _to_domain(model)


class SqlAlchemyReleaseEvidenceReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, report: ReleaseEvidenceReport) -> ReleaseEvidenceReport:
        model = ReleaseEvidenceReportModel(
            id=report.id,
            organization_id=report.organization_id,
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
            missing_artifacts_json=list(report.missing_artifacts),
            missing_quality_gates_json=list(report.missing_quality_gates),
            comparison_json=dict(report.comparison),
            manifest_summary_json=dict(report.manifest_summary),
            report_json=dict(report.report),
            error_message=report.error_message,
            created_at=report.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return _release_evidence_to_domain(model)

    def list_reports(
        self,
        organization_id: UUID,
        *,
        filters: ReleaseEvidenceReportFilters,
        limit: int,
    ) -> list[ReleaseEvidenceReport]:
        statement = (
            select(ReleaseEvidenceReportModel)
            .where(ReleaseEvidenceReportModel.organization_id == organization_id)
            .order_by(
                ReleaseEvidenceReportModel.created_at.desc(),
                ReleaseEvidenceReportModel.id.desc(),
            )
            .limit(limit)
        )
        if filters.status:
            statement = statement.where(ReleaseEvidenceReportModel.status == filters.status)
        models = self._session.scalars(statement).all()
        return [_release_evidence_to_domain(model) for model in models]

    def get_report(
        self,
        organization_id: UUID,
        report_id: UUID,
    ) -> ReleaseEvidenceReport | None:
        model = self._session.scalar(
            select(ReleaseEvidenceReportModel)
            .where(ReleaseEvidenceReportModel.organization_id == organization_id)
            .where(ReleaseEvidenceReportModel.id == report_id)
        )
        if model is None:
            return None
        return _release_evidence_to_domain(model)


def _apply_filters(
    statement: Select[tuple[AuditLogModel]],
    filters: AuditLogFilters,
) -> Select[tuple[AuditLogModel]]:
    if filters.actor_type:
        statement = statement.where(AuditLogModel.actor_type == filters.actor_type)
    if filters.action:
        statement = statement.where(AuditLogModel.action == filters.action)
    if filters.resource_type:
        statement = statement.where(AuditLogModel.resource_type == filters.resource_type)
    return statement


def _to_domain(model: AuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=model.id,
        organization_id=model.organization_id,
        actor_type=model.actor_type,
        actor_id=model.actor_id,
        action=model.action,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        metadata=dict(model.metadata_json),
        created_at=_ensure_utc(model.created_at),
    )


def _release_evidence_to_domain(
    model: ReleaseEvidenceReportModel,
) -> ReleaseEvidenceReport:
    return ReleaseEvidenceReport(
        id=model.id,
        organization_id=model.organization_id,
        requested_by_user_id=model.requested_by_user_id,
        provider=model.provider,
        status=model.status,
        repository=model.repository,
        branch=model.branch,
        workflow=model.workflow,
        artifact_name=model.artifact_name,
        run_id=model.run_id,
        run_url=model.run_url,
        manifest_git_sha=model.manifest_git_sha,
        manifest_git_branch=model.manifest_git_branch,
        ci_run_url=model.ci_run_url,
        artifact_count=model.artifact_count,
        quality_gate_count=model.quality_gate_count,
        missing_artifacts=tuple(str(item) for item in model.missing_artifacts_json),
        missing_quality_gates=tuple(str(item) for item in model.missing_quality_gates_json),
        comparison=dict(model.comparison_json),
        manifest_summary=dict(model.manifest_summary_json),
        report=dict(model.report_json),
        error_message=model.error_message,
        created_at=_ensure_utc(model.created_at),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
