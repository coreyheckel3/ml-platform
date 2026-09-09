from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.administration.infrastructure.sqlalchemy_models import (
    AuditLogModel,
    ReleaseEvidenceReportModel,
)
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAdminControlPlaneRepository,
)
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.platform.database.base import Base


def test_admin_control_plane_repository_loads_org_scoped_snapshot() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    organization_id = uuid4()
    other_organization_id = uuid4()
    user_id = uuid4()
    now = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)

    with Session(engine) as session:
        session.add(
            OrganizationModel(
                id=organization_id,
                name="ForgeML Local",
                slug="forgeml-local",
                status="active",
                created_at=now,
            )
        )
        session.add(
            OrganizationModel(
                id=other_organization_id,
                name="Other",
                slug="other",
                status="active",
                created_at=now,
            )
        )
        session.add(
            UserModel(
                id=user_id,
                organization_id=organization_id,
                email="admin@forgeml.dev",
                display_name="Platform Admin",
                password_hash="hashed-password",
                status="active",
                permissions_csv="*",
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserModel(
                id=uuid4(),
                organization_id=other_organization_id,
                email="other@forgeml.dev",
                display_name="Other Admin",
                password_hash="hashed-password",
                status="active",
                permissions_csv="*",
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ProjectModel(
                id=uuid4(),
                organization_id=organization_id,
                name="Fraud Detection",
                slug="fraud-detection",
                description="Fraud risk models.",
                status="active",
                owner_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AuditLogModel(
                id=uuid4(),
                organization_id=organization_id,
                actor_type="user",
                actor_id=str(user_id),
                action="admin.controls.read",
                resource_type="organization",
                resource_id=str(organization_id),
                metadata_json={"route": "/admin/controls"},
                created_at=now,
            )
        )
        session.add(release_evidence_report_model(organization_id, now))
        session.add(release_evidence_report_model(other_organization_id, now))
        session.commit()

    with Session(engine) as session:
        snapshot = SqlAlchemyAdminControlPlaneRepository(session).load_snapshot(
            organization_id
        )

    assert snapshot.organization is not None
    assert snapshot.organization.slug == "forgeml-local"
    assert [user.email for user in snapshot.users] == ["admin@forgeml.dev"]
    assert snapshot.users[0].permissions == ("*",)
    assert snapshot.users[0].last_login_at is not None
    assert snapshot.users[0].last_login_at.tzinfo is not None
    assert snapshot.project_count == 1
    assert snapshot.audit_event_count == 1
    assert snapshot.release_evidence_report_count == 1


def release_evidence_report_model(
    organization_id,
    created_at: datetime,
) -> ReleaseEvidenceReportModel:
    return ReleaseEvidenceReportModel(
        id=uuid4(),
        organization_id=organization_id,
        requested_by_user_id="user-1",
        provider="github_actions",
        status="passed",
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
        missing_artifacts_json=[],
        missing_quality_gates_json=[],
        comparison_json={"passed": True},
        manifest_summary_json={"artifact_names": ["openapi_contract"]},
        report_json={"schema_version": "forgeml.release_evidence_retrieval.v1"},
        error_message=None,
        created_at=created_at,
    )
