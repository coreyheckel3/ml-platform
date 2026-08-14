import { describe, expect, it } from "vitest";

import type { AuditLogEntry } from "../../settings/api/auditLog";
import { releaseEvidenceAuditEvents } from "../data/releaseEvidenceAuditEvents";
import {
  auditFamilyLabel,
  buildAuditFamilyStats,
  buildOperationalAuditTimeline,
  filterAuditTimeline,
  formatAuditAction,
} from "./auditTimeline";

describe("auditTimeline", () => {
  it("merges release evidence and API audit events into a sorted timeline", () => {
    const timeline = buildOperationalAuditTimeline(
      [
        auditEntry({
          id: "audit-deployment",
          action: "deployments.rollback",
          resourceType: "deployment",
          resourceId: "deployment-1",
          createdAt: "2026-08-13T18:00:00Z",
        }),
        auditEntry({
          id: "audit-login",
          action: "auth.login",
          resourceType: "user",
          resourceId: "user-1",
          createdAt: "2026-08-13T18:05:00Z",
        }),
      ],
      releaseEvidenceAuditEvents,
    );

    expect(timeline[0]).toMatchObject({
      id: "release-evidence-manifest-published",
      family: "release_evidence",
      route: "/release-evidence",
      severity: "success",
    });
    expect(timeline.find((event) => event.id === "audit-deployment")).toMatchObject({
      family: "deployment",
      route: "/deployments",
      severity: "warning",
    });
    expect(timeline.find((event) => event.id === "audit-login")).toMatchObject({
      family: "security",
      route: "/settings",
      severity: "warning",
    });
  });

  it("filters by audit family and computes visible counts", () => {
    const timeline = buildOperationalAuditTimeline(
      [
        auditEntry({
          id: "audit-retraining",
          action: "retraining_runs.trigger",
          resourceType: "retraining_run",
          resourceId: "retraining-run-1",
        }),
        auditEntry({
          id: "audit-model",
          action: "model_versions.review",
          resourceType: "model_version",
          resourceId: "model-version-1",
        }),
      ],
      releaseEvidenceAuditEvents,
    );

    expect(filterAuditTimeline(timeline, "retraining")).toHaveLength(1);
    expect(filterAuditTimeline(timeline, "all")).toHaveLength(5);
    expect(buildAuditFamilyStats(timeline)).toEqual([
      { family: "release_evidence", count: 3 },
      { family: "retraining", count: 1 },
      { family: "registry", count: 1 },
    ]);
  });

  it("formats audit labels for operator-facing UI", () => {
    expect(formatAuditAction("release_evidence.manifest_published")).toBe(
      "Release Evidence - Manifest Published",
    );
    expect(auditFamilyLabel("release_evidence")).toBe("Release Evidence");
    expect(auditFamilyLabel("all")).toBe("All");
  });
});

function auditEntry({
  id,
  action,
  resourceType,
  resourceId,
  createdAt = "2026-08-13T17:00:00Z",
}: {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  createdAt?: string;
}): AuditLogEntry {
  return {
    id,
    organization_id: "org-1",
    actor_type: "user",
    actor_id: "user-1",
    action,
    resource_type: resourceType,
    resource_id: resourceId,
    metadata: { project_id: "project-1" },
    created_at: createdAt,
  };
}
