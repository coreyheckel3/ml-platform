export type ReleaseEvidenceAuditEvent = {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  actorType: "ci" | "system";
  actorId: string;
  createdAt: string;
  title: string;
  summary: string;
  metadata: Record<string, unknown>;
};

export const releaseEvidenceAuditEvents: ReleaseEvidenceAuditEvent[] = [
  {
    id: "release-evidence-manifest-published",
    action: "release_evidence.manifest_published",
    resourceType: "release_manifest",
    resourceId: "forgeml-release-manifest",
    actorType: "ci",
    actorId: "github-actions",
    createdAt: "2026-08-13T20:00:00Z",
    title: "Release manifest published",
    summary:
      "Main-branch CI produced the release manifest artifact with checksums, image targets, and provenance metadata.",
    metadata: {
      artifact: "forgeml-release-manifest",
      manifest_path: "dist/release/forgeml-release-manifest.json",
      workflow_job: "release-evidence",
    },
  },
  {
    id: "release-evidence-verifier-required",
    action: "release_evidence.verifier_required",
    resourceType: "quality_gate",
    resourceId: "release_manifest_verifier_contract",
    actorType: "system",
    actorId: "production-readiness",
    createdAt: "2026-08-13T19:45:00Z",
    title: "Manifest verifier enforced",
    summary:
      "Release verification requires artifact checksum validation, quality gate coverage, and CI evidence linkage.",
    metadata: {
      contract: "contracts/ops/release-manifest-verification.v1.json",
      command: "PYTHONPATH=. python scripts/ops/verify_release_manifest.py",
      gate: "release_manifest_verifier_contract",
    },
  },
  {
    id: "release-evidence-screenshots-captured",
    action: "release_evidence.screenshots_captured",
    resourceType: "portfolio_screenshot",
    resourceId: "09-release-evidence.png",
    actorType: "ci",
    actorId: "playwright",
    createdAt: "2026-08-13T19:30:00Z",
    title: "Reviewer screenshot evidence captured",
    summary:
      "Demo screenshots include release evidence, monitoring, deployment, inference, model registry, and training flows.",
    metadata: {
      screenshot: "09-release-evidence.png",
      route: "/release-evidence",
      command: "make demo-screenshots",
    },
  },
];
