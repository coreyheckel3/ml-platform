from pydantic import BaseModel, Field


class AuditLogEntryResponse(BaseModel):
    id: str
    organization_id: str | None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    next_cursor: str | None = None
