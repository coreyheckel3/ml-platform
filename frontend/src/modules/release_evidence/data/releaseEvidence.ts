export type EvidenceArtifact = {
  name: string;
  kind: string;
  path: string;
  signal: string;
};

export type EvidenceGate = {
  name: string;
  owner: "Backend" | "Frontend" | "Platform" | "Security" | "Operations";
  signal: string;
};

export type ScreenshotEvidence = {
  fileName: string;
  route: string;
  signal: string;
};

export type ReviewerCommand = {
  label: string;
  command: string;
  signal: string;
};

export const releaseEvidenceSummary = {
  artifactCount: 34,
  qualityGateCount: 23,
  imageTargetCount: 5,
  ciArtifactName: "forgeml-release-manifest",
  manifestPath: "dist/release/forgeml-release-manifest.json",
  workflowJob: "release-evidence",
};

export const releaseArtifacts: EvidenceArtifact[] = [
  {
    name: "OpenAPI Contract",
    kind: "API contract",
    path: "contracts/openapi/forgeml.v1.openapi.json",
    signal: "Locks public FastAPI surface area for clients and SDKs.",
  },
  {
    name: "Security Hardening Contract",
    kind: "Security contract",
    path: "contracts/security/security-hardening.v1.json",
    signal: "Captures RBAC, tenancy, audit, rate limiting, and secure defaults.",
  },
  {
    name: "Monitoring Dashboard Contract",
    kind: "Observability contract",
    path: "contracts/observability/monitoring-dashboard.v1.json",
    signal: "Verifies latency, errors, drift, training failure, and retraining views.",
  },
  {
    name: "Deployment Runtime Contract",
    kind: "Runtime contract",
    path: "contracts/runtime/deployment-serving.v1.json",
    signal: "Covers revision resolution, canary traffic, rollback, and probes.",
  },
  {
    name: "Release Manifest Contract",
    kind: "Operations contract",
    path: "contracts/ops/release-manifest.v1.json",
    signal: "Defines release artifacts, image targets, and provenance metadata.",
  },
  {
    name: "Portfolio Readiness Contract",
    kind: "Operations contract",
    path: "contracts/ops/portfolio-readiness.v1.json",
    signal: "Keeps reviewer assets, screenshots, and resume evidence under CI.",
  },
];

export const qualityGates: EvidenceGate[] = [
  {
    name: "backend_lint",
    owner: "Backend",
    signal: "Ruff checks backend, ML examples, workers, and CI scripts.",
  },
  {
    name: "backend_tests",
    owner: "Backend",
    signal: "Pytest covers unit, integration, and API behavior.",
  },
  {
    name: "frontend_tests",
    owner: "Frontend",
    signal: "Vitest validates route, module, and interaction contracts.",
  },
  {
    name: "frontend_e2e",
    owner: "Frontend",
    signal: "Playwright validates lifecycle and screenshot flows.",
  },
  {
    name: "docker_build",
    owner: "Platform",
    signal: "Backend and frontend container images build from checked-in Dockerfiles.",
  },
  {
    name: "production_readiness",
    owner: "Operations",
    signal: "Repository-wide contract scan blocks missing production assets.",
  },
  {
    name: "security_hardening_contract",
    owner: "Security",
    signal: "Security controls and tests remain wired into CI and release evidence.",
  },
  {
    name: "release_manifest_verifier_contract",
    owner: "Operations",
    signal: "Manifest verification can enforce checksums and CI evidence.",
  },
];

export const screenshotEvidence: ScreenshotEvidence[] = [
  {
    fileName: "01-dashboard.png",
    route: "/",
    signal: "Control-plane overview, platform health, and operational posture.",
  },
  {
    fileName: "04-training-runs.png",
    route: "/training-runs",
    signal: "Training lifecycle, metrics, parameters, events, and execution logs.",
  },
  {
    fileName: "06-deployments.png",
    route: "/deployments",
    signal: "Deployment revisions, health checks, canary promotion, and rollback.",
  },
  {
    fileName: "08-monitoring.png",
    route: "/monitoring",
    signal: "Latency percentiles, error trends, drift, failures, and retraining.",
  },
  {
    fileName: "09-release-evidence.png",
    route: "/release-evidence",
    signal: "Release artifacts, quality gates, reviewer commands, and CI provenance.",
  },
];

export const reviewerCommands: ReviewerCommand[] = [
  {
    label: "Run production readiness",
    command: "make production-readiness",
    signal: "Executes the aggregate repository readiness gate locally.",
  },
  {
    label: "Build release manifest",
    command:
      "PYTHONPATH=. python scripts/ops/build_release_manifest.py --output dist/release/forgeml-release-manifest.json",
    signal: "Creates the same manifest shape published by main-branch CI.",
  },
  {
    label: "Verify release manifest",
    command:
      "PYTHONPATH=. python scripts/ops/verify_release_manifest.py --manifest dist/release/forgeml-release-manifest.json --require-ci-evidence",
    signal: "Validates checksums, required gates, image targets, and CI metadata.",
  },
  {
    label: "Capture demo screenshots",
    command: "make demo-screenshots",
    signal: "Generates reviewer screenshots through Playwright against mocked APIs.",
  },
];
