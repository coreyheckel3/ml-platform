from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from forgeml.modules.administration.api.schemas import (
    AuditLogEntryResponse,
    AuditLogListResponse,
)
from forgeml.modules.administration.application.services import (
    AdministrationService,
    ListAuditLogQuery,
)
from forgeml.modules.administration.domain.entities import AuditLogEntry
from forgeml.modules.administration.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAuditLogRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["administration"])


def get_administration_service(
    session: Session = Depends(get_db_session),
) -> AdministrationService:
    return AdministrationService(audit_log=SqlAlchemyAuditLogRepository(session))


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
