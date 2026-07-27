import { apiGet } from "../../../shared/api/client";

export type AuditLogEntry = {
  id: string;
  organization_id: string | null;
  actor_type: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AuditLogListResponse = {
  items: AuditLogEntry[];
  next_cursor: string | null;
};

export type AuditLogFilters = {
  actorType?: string;
  action?: string;
  resourceType?: string;
  limit?: number;
};

export function listAuditLog(
  token: string,
  filters: AuditLogFilters = {},
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams();
  if (filters.actorType) {
    params.set("actor_type", filters.actorType);
  }
  if (filters.action) {
    params.set("action", filters.action);
  }
  if (filters.resourceType) {
    params.set("resource_type", filters.resourceType);
  }
  params.set("limit", String(filters.limit ?? 50));

  return apiGet<AuditLogListResponse>(`/api/v1/admin/audit-log?${params.toString()}`, {
    token,
  });
}
