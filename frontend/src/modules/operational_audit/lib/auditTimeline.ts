import type { AuditLogEntry } from "../../settings/api/auditLog";
import type { ReleaseEvidenceAuditEvent } from "../data/releaseEvidenceAuditEvents";

export type AuditFamily =
  | "release_evidence"
  | "deployment"
  | "retraining"
  | "security"
  | "training"
  | "registry"
  | "dataset"
  | "monitoring"
  | "platform";

export type AuditSeverity = "info" | "success" | "warning" | "danger";

export type AuditTimelineSource = "api" | "release_evidence";

export type AuditTimelineEvent = {
  id: string;
  family: AuditFamily;
  source: AuditTimelineSource;
  createdAt: string;
  action: string;
  title: string;
  summary: string;
  actor: string;
  resource: string;
  resourceType: string;
  resourceId: string;
  route: string;
  severity: AuditSeverity;
  metadata: Record<string, unknown>;
};

export type AuditFamilyFilter = AuditFamily | "all";

export type AuditFamilyStat = {
  family: AuditFamily;
  count: number;
};

export function buildOperationalAuditTimeline(
  auditEntries: AuditLogEntry[],
  releaseEvidenceEvents: ReleaseEvidenceAuditEvent[],
): AuditTimelineEvent[] {
  return [
    ...releaseEvidenceEvents.map(releaseEvidenceEventToTimeline),
    ...auditEntries.map(auditLogEntryToTimeline),
  ].sort(compareTimelineEvents);
}

export function filterAuditTimeline(
  events: AuditTimelineEvent[],
  family: AuditFamilyFilter,
): AuditTimelineEvent[] {
  if (family === "all") {
    return events;
  }
  return events.filter((event) => event.family === family);
}

export function buildAuditFamilyStats(
  events: AuditTimelineEvent[],
): AuditFamilyStat[] {
  const counts = events.reduce<Record<AuditFamily, number>>(
    (accumulator, event) => ({
      ...accumulator,
      [event.family]: accumulator[event.family] + 1,
    }),
    {
      release_evidence: 0,
      deployment: 0,
      retraining: 0,
      security: 0,
      training: 0,
      registry: 0,
      dataset: 0,
      monitoring: 0,
      platform: 0,
    },
  );

  return auditFamilyOrder
    .map((family) => ({ family, count: counts[family] }))
    .filter((stat) => stat.count > 0);
}

export function auditFamilyLabel(family: AuditFamilyFilter): string {
  if (family === "all") {
    return "All";
  }
  return family
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatAuditAction(action: string): string {
  return action
    .split(".")
    .map((segment) =>
      segment
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" "),
    )
    .join(" - ");
}

function releaseEvidenceEventToTimeline(
  event: ReleaseEvidenceAuditEvent,
): AuditTimelineEvent {
  return {
    id: event.id,
    family: "release_evidence",
    source: "release_evidence",
    createdAt: event.createdAt,
    action: event.action,
    title: event.title,
    summary: event.summary,
    actor: `${event.actorType}:${event.actorId}`,
    resource: `${event.resourceType}:${event.resourceId}`,
    resourceType: event.resourceType,
    resourceId: event.resourceId,
    route: "/release-evidence",
    severity: "success",
    metadata: event.metadata,
  };
}

function auditLogEntryToTimeline(entry: AuditLogEntry): AuditTimelineEvent {
  const family = classifyAuditFamily(entry);
  return {
    id: entry.id,
    family,
    source: "api",
    createdAt: entry.created_at,
    action: entry.action,
    title: formatAuditAction(entry.action),
    summary: buildAuditSummary(entry),
    actor: `${entry.actor_type}:${entry.actor_id}`,
    resource: `${entry.resource_type}:${entry.resource_id}`,
    resourceType: entry.resource_type,
    resourceId: entry.resource_id,
    route: routeForAuditFamily(family, entry),
    severity: severityForAuditEntry(entry, family),
    metadata: entry.metadata,
  };
}

function classifyAuditFamily(entry: AuditLogEntry): AuditFamily {
  const action = entry.action;
  const resourceType = entry.resource_type;

  if (action.startsWith("release_evidence.")) {
    return "release_evidence";
  }
  if (action.startsWith("deployments.") || resourceType.startsWith("deployment")) {
    return "deployment";
  }
  if (action.startsWith("retraining_runs.") || resourceType === "retraining_run") {
    return "retraining";
  }
  if (
    action.startsWith("auth.") ||
    action.startsWith("admin.") ||
    resourceType === "user" ||
    resourceType === "session"
  ) {
    return "security";
  }
  if (action.startsWith("training_runs.") || resourceType === "training_run") {
    return "training";
  }
  if (
    action.startsWith("model_versions.") ||
    action.startsWith("models.") ||
    resourceType === "model" ||
    resourceType === "registered_model" ||
    resourceType === "model_version"
  ) {
    return "registry";
  }
  if (
    action.startsWith("datasets.") ||
    action.startsWith("dataset_versions.") ||
    action.startsWith("feature_sets.") ||
    resourceType === "dataset" ||
    resourceType === "dataset_version" ||
    resourceType === "feature_set"
  ) {
    return "dataset";
  }
  if (
    action.startsWith("alert_events.") ||
    action.startsWith("monitoring.") ||
    action.startsWith("inference.") ||
    resourceType === "alert_event" ||
    resourceType === "inference_endpoint"
  ) {
    return "monitoring";
  }
  return "platform";
}

function buildAuditSummary(entry: AuditLogEntry): string {
  const projectId = stringMetadataValue(entry.metadata.project_id);
  const scope = projectId ? ` for ${projectId}` : "";
  const actor = `${entry.actor_type}:${entry.actor_id}`;
  return `${actor} recorded ${formatAuditAction(entry.action)} on ${entry.resource_type}:${entry.resource_id}${scope}.`;
}

function routeForAuditFamily(family: AuditFamily, entry: AuditLogEntry): string {
  if (family === "release_evidence") {
    return "/release-evidence";
  }
  if (family === "deployment") {
    return "/deployments";
  }
  if (family === "retraining") {
    return "/retraining";
  }
  if (family === "security") {
    return "/settings";
  }
  if (family === "training") {
    return "/training-runs";
  }
  if (family === "registry") {
    return "/models";
  }
  if (family === "dataset") {
    return entry.resource_type === "feature_set" ? "/feature-store" : "/datasets";
  }
  if (family === "monitoring") {
    return entry.resource_type === "alert_event" ? "/alerts" : "/monitoring";
  }
  return "/settings";
}

function severityForAuditEntry(
  entry: AuditLogEntry,
  family: AuditFamily,
): AuditSeverity {
  if (
    entry.action.includes("failed") ||
    entry.action.includes("error") ||
    entry.action.includes("rejected")
  ) {
    return "danger";
  }
  if (
    entry.action.includes("rollback") ||
    entry.action.includes("trigger") ||
    entry.action.includes("canary") ||
    family === "security"
  ) {
    return "warning";
  }
  if (
    entry.action.includes("approved") ||
    entry.action.includes("review") ||
    entry.action.includes("succeeded") ||
    entry.action.includes("promote") ||
    entry.action.includes("traffic")
  ) {
    return "success";
  }
  return "info";
}

function stringMetadataValue(value: unknown): string {
  return typeof value === "string" && value.trim() ? value : "";
}

function compareTimelineEvents(left: AuditTimelineEvent, right: AuditTimelineEvent): number {
  return Date.parse(right.createdAt) - Date.parse(left.createdAt);
}

const auditFamilyOrder: AuditFamily[] = [
  "release_evidence",
  "deployment",
  "retraining",
  "security",
  "training",
  "registry",
  "dataset",
  "monitoring",
  "platform",
];
