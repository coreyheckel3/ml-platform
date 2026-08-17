from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.administration.domain.entities import (
    AuditLogEvent,
    ReleaseEvidenceReport,
)
from forgeml.modules.administration.infrastructure.sqlalchemy_models import AuditLogModel
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyReleaseEvidenceReportRepository,
)
from forgeml.modules.administration.repositories.interfaces import (
    AuditLogFilters,
    ReleaseEvidenceReportFilters,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import OrganizationModel
from forgeml.platform.database.base import Base


def test_audit_log_repository_filters_org_entries_newest_first() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    other_organization_id = uuid4()
    now = datetime.now(UTC)

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            OrganizationModel(
                id=other_organization_id,
                name="Other",
                slug="other",
            )
        )
        session.add_all(
            [
                audit_entry(
                    organization_id,
                    "projects.create",
                    "project",
                    "project-1",
                    now - timedelta(minutes=5),
                ),
                audit_entry(
                    organization_id,
                    "model_versions.review",
                    "model_version",
                    "model-version-1",
                    now,
                ),
                audit_entry(
                    other_organization_id,
                    "model_versions.review",
                    "model_version",
                    "model-version-other",
                    now + timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyAuditLogRepository(session)

        entries = repository.list_entries(
            organization_id,
            filters=AuditLogFilters(action="model_versions.review"),
            limit=10,
        )

    assert [entry.resource_id for entry in entries] == ["model-version-1"]
    assert entries[0].metadata == {"decision": "approved"}
    assert entries[0].created_at.tzinfo is not None


def test_audit_log_repository_records_append_only_event() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    actor_id = uuid4()
    project_id = uuid4()

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        repository = SqlAlchemyAuditLogRepository(session)

        created = repository.record(
            AuditLogEvent(
                organization_id=organization_id,
                actor_type="user",
                actor_id=str(actor_id),
                action="projects.create",
                resource_type="project",
                resource_id=str(project_id),
                metadata={"slug": "fraud-detection-platform", "name": "Fraud Detection Platform"},
            )
        )
        session.commit()

    assert created.organization_id == organization_id
    assert created.action == "projects.create"
    assert created.metadata["slug"] == "fraud-detection-platform"
    assert created.created_at.tzinfo is not None

    with Session(engine) as session:
        repository = SqlAlchemyAuditLogRepository(session)

        entries = repository.list_entries(
            organization_id,
            filters=AuditLogFilters(resource_type="project"),
            limit=10,
        )

    assert [entry.id for entry in entries] == [created.id]
    assert entries[0].actor_id == str(actor_id)
    assert entries[0].resource_id == str(project_id)


def test_release_evidence_report_repository_filters_org_reports_newest_first() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    other_organization_id = uuid4()
    now = datetime.now(UTC)

    with Session(engine) as session:
        session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
        session.add(
            OrganizationModel(
                id=other_organization_id,
                name="Other",
                slug="other",
            )
        )
        repository = SqlAlchemyReleaseEvidenceReportRepository(session)
        older_failed = release_evidence_report(
            organization_id,
            status="failed",
            created_at=now - timedelta(minutes=10),
        )
        newest_passed = release_evidence_report(
            organization_id,
            status="passed",
            created_at=now,
        )
        other_org = release_evidence_report(
            other_organization_id,
            status="passed",
            created_at=now + timedelta(minutes=1),
        )
        repository.save(older_failed)
        repository.save(newest_passed)
        repository.save(other_org)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyReleaseEvidenceReportRepository(session)

        reports = repository.list_reports(
            organization_id,
            filters=ReleaseEvidenceReportFilters(status="passed"),
            limit=10,
        )
        found = repository.get_report(organization_id, newest_passed.id)
        cross_org = repository.get_report(other_organization_id, newest_passed.id)

    assert [report.id for report in reports] == [newest_passed.id]
    assert found is not None
    assert found.comparison == {"passed": True}
    assert found.manifest_summary["artifact_names"] == ["openapi_contract"]
    assert found.created_at.tzinfo is not None
    assert cross_org is None


def audit_entry(
    organization_id,
    action: str,
    resource_type: str,
    resource_id: str,
    created_at: datetime,
) -> AuditLogModel:
    return AuditLogModel(
        id=uuid4(),
        organization_id=organization_id,
        actor_type="user",
        actor_id="user-1",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json={"decision": "approved"} if resource_type == "model_version" else {},
        created_at=created_at,
    )


def release_evidence_report(
    organization_id,
    *,
    status: str,
    created_at: datetime,
) -> ReleaseEvidenceReport:
    return ReleaseEvidenceReport(
        id=uuid4(),
        organization_id=organization_id,
        requested_by_user_id="user-1",
        provider="github_actions",
        status=status,
        repository="coreyheckel3/ml-platform",
        branch="main",
        workflow="ci.yml",
        artifact_name="forgeml-release-manifest",
        run_id="12345",
        run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        manifest_git_sha="a" * 40,
        manifest_git_branch="main",
        ci_run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
        artifact_count=1,
        quality_gate_count=1,
        missing_artifacts=(),
        missing_quality_gates=(),
        comparison={"passed": status == "passed"},
        manifest_summary={"artifact_names": ["openapi_contract"]},
        report={"schema_version": "forgeml.release_evidence_retrieval.v1"},
        error_message=None if status == "passed" else "missing release evidence",
        created_at=created_at,
    )
