from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from forgeml.modules.administration.domain.entities import (
    AuditLogEntry,
    AuditLogEvent,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.repositories.interfaces import (
    AuditLogFilters,
    AuditLogRepository,
    ReleaseEvidenceReportFilters,
    ReleaseEvidenceReportRepository,
)
from forgeml.platform.domain.errors import (
    DomainValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.release_evidence import (
    RELEASE_EVIDENCE_REQUIRED_ARTIFACTS,
    RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES,
    RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION,
    ReleaseEvidenceGateway,
    ReleaseEvidenceRetrievalError,
    ReleaseEvidenceRun,
    compare_release_manifest_to_contract,
    summarize_release_manifest,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class ListAuditLogQuery:
    organization_id: UUID
    actor_type: str | None = None
    action: str | None = None
    resource_type: str | None = None
    limit: int = 50


@dataclass(frozen=True)
class ListReleaseEvidenceReportsQuery:
    organization_id: UUID
    status: str | None = None
    limit: int = 20


@dataclass(frozen=True)
class GetReleaseEvidenceReportQuery:
    organization_id: UUID
    report_id: UUID


@dataclass(frozen=True)
class RetrieveReleaseEvidenceCommand:
    organization_id: UUID


@dataclass(frozen=True)
class GetReleaseEvidenceRefreshStatusQuery:
    organization_id: UUID
    stale_after_seconds: int
    refresh_interval_seconds: int
    now: datetime | None = None


@dataclass(frozen=True)
class ReleaseEvidenceRetrievalConfig:
    provider: str
    repository: str | None
    branch: str | None
    workflow: str | None
    artifact_name: str | None


@dataclass(frozen=True)
class ReleaseEvidenceRefreshStatus:
    organization_id: UUID
    provider: str
    repository: str | None
    branch: str | None
    workflow: str | None
    artifact_name: str | None
    status: str
    stale: bool
    stale_after_seconds: int
    refresh_interval_seconds: int
    latest_report: ReleaseEvidenceReport | None
    last_successful_report: ReleaseEvidenceReport | None
    latest_report_age_seconds: int | None
    last_success_age_seconds: int | None
    next_refresh_at: datetime | None
    checked_at: datetime
    stale_reasons: tuple[str, ...]
    recommended_action: str
    operator_command: str


class AdministrationService:
    def __init__(
        self,
        *,
        audit_log: AuditLogRepository,
        release_evidence_reports: ReleaseEvidenceReportRepository | None = None,
        release_evidence_gateway: ReleaseEvidenceGateway | None = None,
        release_evidence_config: ReleaseEvidenceRetrievalConfig | None = None,
    ) -> None:
        self._audit_log = audit_log
        self._release_evidence_reports = release_evidence_reports
        self._release_evidence_gateway = release_evidence_gateway
        self._release_evidence_config = release_evidence_config

    def list_audit_log(
        self,
        query: ListAuditLogQuery,
        principal: Principal,
    ) -> list[AuditLogEntry]:
        if not principal.has("admin:audit_log:read"):
            raise PermissionDeniedError("You do not have permission to read audit logs.")
        if str(query.organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot read audit logs for another organization.")

        return self._audit_log.list_entries(
            query.organization_id,
            filters=AuditLogFilters(
                actor_type=_clean_filter(query.actor_type),
                action=_clean_filter(query.action),
                resource_type=_clean_filter(query.resource_type),
            ),
            limit=min(max(query.limit, 1), 200),
        )

    def list_release_evidence_reports(
        self,
        query: ListReleaseEvidenceReportsQuery,
        principal: Principal,
    ) -> list[ReleaseEvidenceReport]:
        self._require_release_evidence_read(query.organization_id, principal)
        return self._require_release_evidence_repository().list_reports(
            query.organization_id,
            filters=ReleaseEvidenceReportFilters(status=_clean_filter(query.status)),
            limit=min(max(query.limit, 1), 100),
        )

    def get_release_evidence_report(
        self,
        query: GetReleaseEvidenceReportQuery,
        principal: Principal,
    ) -> ReleaseEvidenceReport:
        self._require_release_evidence_read(query.organization_id, principal)
        report = self._require_release_evidence_repository().get_report(
            query.organization_id,
            query.report_id,
        )
        if report is None:
            raise ResourceNotFoundError("Release evidence report was not found.")
        return report

    def retrieve_release_evidence(
        self,
        command: RetrieveReleaseEvidenceCommand,
        principal: Principal,
    ) -> ReleaseEvidenceReport:
        if not principal.has("admin:release_evidence:retrieve"):
            raise PermissionDeniedError(
                "You do not have permission to retrieve release evidence."
            )
        self._assert_same_organization(command.organization_id, principal)
        repository = self._require_release_evidence_repository()
        gateway = self._require_release_evidence_gateway()
        config = self._require_release_evidence_config()

        try:
            report = _retrieve_release_evidence_report(
                organization_id=command.organization_id,
                requested_by_user_id=principal.user_id,
                gateway=gateway,
                config=config,
            )
        except ReleaseEvidenceRetrievalError as exc:
            report = _failed_release_evidence_report(
                organization_id=command.organization_id,
                requested_by_user_id=principal.user_id,
                config=config,
                error_message=str(exc),
            )

        saved = repository.save(report)
        self._audit_log.record(
            AuditLogEvent(
                organization_id=saved.organization_id,
                actor_type="user",
                actor_id=principal.user_id,
                action=(
                    "release_evidence.retrieve"
                    if saved.status == "passed"
                    else "release_evidence.retrieve_failed"
                ),
                resource_type="release_evidence_report",
                resource_id=str(saved.id),
                metadata={
                    "status": saved.status,
                    "provider": saved.provider,
                    "repository": saved.repository,
                    "branch": saved.branch,
                    "workflow": saved.workflow,
                    "artifact_name": saved.artifact_name,
                    "ci_run_url": saved.ci_run_url,
                    "missing_artifact_count": len(saved.missing_artifacts),
                    "missing_quality_gate_count": len(saved.missing_quality_gates),
                    "error_message": saved.error_message,
                },
            )
        )
        return saved

    def get_release_evidence_refresh_status(
        self,
        query: GetReleaseEvidenceRefreshStatusQuery,
        principal: Principal,
    ) -> ReleaseEvidenceRefreshStatus:
        self._require_release_evidence_read(query.organization_id, principal)
        repository = self._require_release_evidence_repository()
        config = self._require_release_evidence_config()
        now = _ensure_utc(query.now or datetime.now(UTC))
        stale_after_seconds = max(query.stale_after_seconds, 1)
        refresh_interval_seconds = max(query.refresh_interval_seconds, 1)
        latest_report = _first_or_none(
            repository.list_reports(
                query.organization_id,
                filters=ReleaseEvidenceReportFilters(),
                limit=1,
            )
        )
        last_successful_report = _first_or_none(
            repository.list_reports(
                query.organization_id,
                filters=ReleaseEvidenceReportFilters(status="passed"),
                limit=1,
            )
        )
        latest_age_seconds = (
            _age_seconds(latest_report.created_at, now) if latest_report else None
        )
        last_success_age_seconds = (
            _age_seconds(last_successful_report.created_at, now)
            if last_successful_report
            else None
        )
        stale_reasons = _release_evidence_stale_reasons(
            latest_report=latest_report,
            last_successful_report=last_successful_report,
            last_success_age_seconds=last_success_age_seconds,
            stale_after_seconds=stale_after_seconds,
        )
        stale = (
            "no_successful_report" in stale_reasons
            or "last_success_older_than_threshold" in stale_reasons
        )
        status = _refresh_status_label(
            latest_report=latest_report,
            stale=stale,
            stale_reasons=stale_reasons,
        )
        next_refresh_at = (
            last_successful_report.created_at + timedelta(seconds=refresh_interval_seconds)
            if last_successful_report
            else now
        )
        recommended_action = (
            "retrieve_now"
            if stale or "latest_report_failed" in stale_reasons
            else "wait_until_next_refresh"
        )
        return ReleaseEvidenceRefreshStatus(
            organization_id=query.organization_id,
            provider=config.provider,
            repository=config.repository,
            branch=config.branch,
            workflow=config.workflow,
            artifact_name=config.artifact_name,
            status=status,
            stale=stale,
            stale_after_seconds=stale_after_seconds,
            refresh_interval_seconds=refresh_interval_seconds,
            latest_report=latest_report,
            last_successful_report=last_successful_report,
            latest_report_age_seconds=latest_age_seconds,
            last_success_age_seconds=last_success_age_seconds,
            next_refresh_at=next_refresh_at,
            checked_at=now,
            stale_reasons=stale_reasons,
            recommended_action=recommended_action,
            operator_command=_refresh_operator_command(stale_after_seconds),
        )

    def _require_release_evidence_read(
        self,
        organization_id: UUID,
        principal: Principal,
    ) -> None:
        if not principal.has("admin:release_evidence:read"):
            raise PermissionDeniedError(
                "You do not have permission to read release evidence reports."
            )
        self._assert_same_organization(organization_id, principal)

    @staticmethod
    def _assert_same_organization(organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot access another organization's records.")

    def _require_release_evidence_repository(self) -> ReleaseEvidenceReportRepository:
        if self._release_evidence_reports is None:
            raise DomainValidationError("Release evidence reporting is not configured.")
        return self._release_evidence_reports

    def _require_release_evidence_gateway(self) -> ReleaseEvidenceGateway:
        if self._release_evidence_gateway is None:
            raise DomainValidationError("Release evidence retrieval is not configured.")
        return self._release_evidence_gateway

    def _require_release_evidence_config(self) -> ReleaseEvidenceRetrievalConfig:
        if self._release_evidence_config is None:
            raise DomainValidationError("Release evidence retrieval is not configured.")
        return self._release_evidence_config


def _clean_filter(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _first_or_none(reports: list[ReleaseEvidenceReport]) -> ReleaseEvidenceReport | None:
    return reports[0] if reports else None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _age_seconds(created_at: datetime, now: datetime) -> int:
    age = now - _ensure_utc(created_at)
    return max(int(age.total_seconds()), 0)


def _release_evidence_stale_reasons(
    *,
    latest_report: ReleaseEvidenceReport | None,
    last_successful_report: ReleaseEvidenceReport | None,
    last_success_age_seconds: int | None,
    stale_after_seconds: int,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if latest_report is None:
        reasons.append("no_reports")
    if last_successful_report is None:
        reasons.append("no_successful_report")
    elif (
        last_success_age_seconds is not None
        and last_success_age_seconds > stale_after_seconds
    ):
        reasons.append("last_success_older_than_threshold")
    if latest_report is not None and latest_report.status != "passed":
        reasons.append("latest_report_failed")
    return tuple(reasons)


def _refresh_status_label(
    *,
    latest_report: ReleaseEvidenceReport | None,
    stale: bool,
    stale_reasons: tuple[str, ...],
) -> str:
    if latest_report is None:
        return "missing"
    if stale:
        return "stale"
    if "latest_report_failed" in stale_reasons:
        return "attention"
    return "fresh"


def _refresh_operator_command(stale_after_seconds: int) -> str:
    return (
        "PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py "
        "--base-url http://127.0.0.1:8001 --once "
        f"--stale-after-seconds {stale_after_seconds}"
    )


def _retrieve_release_evidence_report(
    *,
    organization_id: UUID,
    requested_by_user_id: str,
    gateway: ReleaseEvidenceGateway,
    config: ReleaseEvidenceRetrievalConfig,
) -> ReleaseEvidenceReport:
    run = gateway.latest_successful_run()
    manifest = gateway.download_release_manifest(run)
    summary = summarize_release_manifest(manifest)
    expected_branch = config.branch if config.provider == "github_actions" else None
    comparison = compare_release_manifest_to_contract(
        manifest,
        required_artifacts=RELEASE_EVIDENCE_REQUIRED_ARTIFACTS,
        required_quality_gates=RELEASE_EVIDENCE_REQUIRED_QUALITY_GATES,
        expected_branch=expected_branch,
    )
    status = "passed" if comparison.passed else "failed"
    comparison_payload = comparison.as_dict()
    summary_payload = summary.as_dict()
    report_payload = _release_evidence_payload(
        config=config,
        status=status,
        run=run,
        manifest_summary=summary_payload,
        comparison=comparison_payload,
    )
    return ReleaseEvidenceReport(
        id=uuid4(),
        organization_id=organization_id,
        requested_by_user_id=requested_by_user_id,
        provider=config.provider,
        status=status,
        repository=config.repository,
        branch=config.branch,
        workflow=config.workflow,
        artifact_name=config.artifact_name,
        run_id=str(run.id),
        run_url=run.html_url,
        manifest_git_sha=summary.git_sha,
        manifest_git_branch=summary.git_branch,
        ci_run_url=summary.ci_run_url,
        artifact_count=len(summary.artifact_names),
        quality_gate_count=len(summary.quality_gate_names),
        missing_artifacts=comparison.missing_artifacts,
        missing_quality_gates=comparison.missing_quality_gates,
        comparison=comparison_payload,
        manifest_summary=summary_payload,
        report=report_payload,
        error_message=None,
        created_at=datetime.now(UTC),
    )


def _failed_release_evidence_report(
    *,
    organization_id: UUID,
    requested_by_user_id: str,
    config: ReleaseEvidenceRetrievalConfig,
    error_message: str,
) -> ReleaseEvidenceReport:
    comparison_payload: dict[str, object] = {
        "passed": False,
        "error": error_message,
    }
    report_payload = _release_evidence_payload(
        config=config,
        status="failed",
        run=None,
        manifest_summary={},
        comparison=comparison_payload,
        error_message=error_message,
    )
    return ReleaseEvidenceReport(
        id=uuid4(),
        organization_id=organization_id,
        requested_by_user_id=requested_by_user_id,
        provider=config.provider,
        status="failed",
        repository=config.repository,
        branch=config.branch,
        workflow=config.workflow,
        artifact_name=config.artifact_name,
        run_id=None,
        run_url=None,
        manifest_git_sha=None,
        manifest_git_branch=None,
        ci_run_url=None,
        artifact_count=0,
        quality_gate_count=0,
        missing_artifacts=(),
        missing_quality_gates=(),
        comparison=comparison_payload,
        manifest_summary={},
        report=report_payload,
        error_message=error_message,
        created_at=datetime.now(UTC),
    )


def _release_evidence_payload(
    *,
    config: ReleaseEvidenceRetrievalConfig,
    status: str,
    run: ReleaseEvidenceRun | None,
    manifest_summary: dict[str, object],
    comparison: dict[str, object],
    error_message: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION,
        "status": status,
        "provider": config.provider,
        "source": {
            "repository": config.repository,
            "branch": config.branch,
            "workflow": config.workflow,
            "artifact_name": config.artifact_name,
        },
        "run": _run_payload(run) if run else None,
        "manifest_summary": manifest_summary,
        "comparison": comparison,
    }
    if error_message:
        payload["error"] = error_message
    return payload


def _run_payload(run: ReleaseEvidenceRun) -> dict[str, object]:
    return {
        "id": run.id,
        "head_sha": run.head_sha,
        "branch": run.branch,
        "status": run.status,
        "conclusion": run.conclusion,
        "html_url": run.html_url,
    }
