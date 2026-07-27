from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.administration.infrastructure.sqlalchemy_models import AuditLogModel
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
)
from forgeml.modules.administration.repositories.interfaces import AuditLogFilters
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
