from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from forgeml.modules.administration.domain.entities import AuditLogEntry, AuditLogEvent
from forgeml.modules.administration.infrastructure.sqlalchemy_models import AuditLogModel
from forgeml.modules.administration.repositories.interfaces import AuditLogFilters


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


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
