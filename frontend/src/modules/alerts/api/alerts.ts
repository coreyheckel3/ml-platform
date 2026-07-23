import { apiGet, apiPost } from "../../../shared/api/client";

export type AlertRule = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string;
  severity: string;
  metric: string;
  operator: string;
  threshold: number;
  window_seconds: number;
  enabled: boolean;
  created_by: string;
};

export type AlertEvent = {
  id: string;
  organization_id: string;
  project_id: string;
  alert_rule_id: string;
  endpoint_id: string | null;
  severity: string;
  status: string;
  message: string;
  observed_value: number;
  threshold: number;
  metadata: Record<string, unknown>;
  acknowledged_by: string | null;
  resolved_by: string | null;
};

export type AlertEvaluation = {
  rule_id: string;
  endpoint_id: string;
  triggered: boolean;
  observed_value: number;
  event: AlertEvent | null;
};

export type CreateAlertRulePayload = {
  name: string;
  description: string;
  severity: string;
  metric: string;
  operator: string;
  threshold: number;
  window_seconds: number;
  enabled: boolean;
};

export type AlertRuleListResponse = {
  items: AlertRule[];
  next_cursor: string | null;
};

export type AlertEventListResponse = {
  items: AlertEvent[];
  next_cursor: string | null;
};

export function listAlertRules(
  projectId: string,
  token: string,
): Promise<AlertRuleListResponse> {
  return apiGet<AlertRuleListResponse>(
    `/api/v1/projects/${projectId}/alert-rules`,
    {
      token,
    },
  );
}

export function createAlertRule(
  projectId: string,
  payload: CreateAlertRulePayload,
  token: string,
): Promise<AlertRule> {
  return apiPost<CreateAlertRulePayload, AlertRule>(
    `/api/v1/projects/${projectId}/alert-rules`,
    payload,
    { token },
  );
}

export function listAlertEvents(
  projectId: string,
  token: string,
): Promise<AlertEventListResponse> {
  return apiGet<AlertEventListResponse>(
    `/api/v1/projects/${projectId}/alert-events`,
    {
      token,
    },
  );
}

export function evaluateAlertRule(
  ruleId: string,
  endpointId: string,
  token: string,
): Promise<AlertEvaluation> {
  return apiPost<{ endpoint_id: string }, AlertEvaluation>(
    `/api/v1/alert-rules/${ruleId}/evaluate`,
    { endpoint_id: endpointId },
    { token },
  );
}

export function acknowledgeAlertEvent(
  eventId: string,
  token: string,
): Promise<AlertEvent> {
  return apiPost<Record<string, never>, AlertEvent>(
    `/api/v1/alert-events/${eventId}/acknowledge`,
    {},
    { token },
  );
}

export function resolveAlertEvent(
  eventId: string,
  token: string,
): Promise<AlertEvent> {
  return apiPost<Record<string, never>, AlertEvent>(
    `/api/v1/alert-events/${eventId}/resolve`,
    {},
    { token },
  );
}
