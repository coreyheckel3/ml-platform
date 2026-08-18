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

export type LiveReleaseEvidenceRetrieval = {
  provider: string;
  branch: string;
  workflow: string;
  artifactName: string;
  adapter: string;
  status: string;
  comparisonSignals: string[];
  operatorCommand: string;
};

export type ScheduledReleaseEvidenceRefresh = {
  staleAfterSeconds: number;
  refreshIntervalSeconds: number;
  operatorCommand: string;
  cronCommand: string;
};

export const releaseEvidenceSummary = {
  artifactCount: 39,
  qualityGateCount: 28,
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
    name: "External Training Package Contract",
    kind: "Integration contract",
    path: "contracts/training/external-package-runner.v1.json",
    signal:
      "Covers allowlisted external package execution, training profile defaults, metric import, and artifact checksums.",
  },
  {
    name: "Release Manifest Contract",
    kind: "Operations contract",
    path: "contracts/ops/release-manifest.v1.json",
    signal: "Defines release artifacts, image targets, and provenance metadata.",
  },
  {
    name: "Operational Audit UX Contract",
    kind: "Operations contract",
    path: "contracts/ops/operational-audit-ux.v1.json",
    signal: "Verifies the operator audit timeline, route linkage, screenshots, and CI gate.",
  },
  {
    name: "Release Evidence Retrieval Contract",
    kind: "Operations contract",
    path: "contracts/ops/release-evidence-retrieval.v1.json",
    signal:
      "Verifies live GitHub Actions artifact retrieval, manifest extraction, and comparison checks.",
  },
  {
    name: "Release Evidence Drilldown API Contract",
    kind: "Operations contract",
    path: "contracts/ops/release-evidence-drilldown-api.v1.json",
    signal:
      "Verifies persisted retrieval reports, admin RBAC, audit events, and frontend drilldown behavior.",
  },
  {
    name: "Release Evidence Scheduled Refresh Contract",
    kind: "Operations contract",
    path: "contracts/ops/release-evidence-scheduled-refresh.v1.json",
    signal:
      "Verifies stale evidence summaries, scheduled refresh automation, operator commands, and UI status indicators.",
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
    name: "external_training_package_contract",
    owner: "Platform",
    signal:
      "External package profiles, worker execution, artifact import, and UI wiring stay enforced in CI.",
  },
  {
    name: "release_manifest_verifier_contract",
    owner: "Operations",
    signal: "Manifest verification can enforce checksums and CI evidence.",
  },
  {
    name: "operational_audit_ux_contract",
    owner: "Operations",
    signal: "Operational audit route and timeline coverage stay enforced in CI.",
  },
  {
    name: "release_evidence_retrieval_contract",
    owner: "Operations",
    signal:
      "GitHub Actions artifact retrieval and manifest comparison stay enforced in CI.",
  },
  {
    name: "release_evidence_drilldown_api_contract",
    owner: "Operations",
    signal:
      "Admin API retrieval, report persistence, audit logging, and drilldown UI stay enforced in CI.",
  },
  {
    name: "release_evidence_scheduled_refresh_contract",
    owner: "Operations",
    signal:
      "Stale evidence status, last-success summaries, scheduler CLI behavior, and UI indicators stay enforced in CI.",
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
    signal:
      "Release artifacts, quality gates, live evidence retrieval, reviewer commands, and CI provenance.",
  },
  {
    fileName: "10-operational-audit.png",
    route: "/operational-audit",
    signal: "Operational timeline for release evidence, deployments, retraining, and security events.",
  },
];

export const liveReleaseEvidenceRetrieval: LiveReleaseEvidenceRetrieval = {
  provider: "GitHub Actions",
  branch: "main",
  workflow: "ci.yml",
  artifactName: "forgeml-release-manifest",
  adapter: "GitHubActionsReleaseEvidenceGateway",
  status: "contract checked",
  comparisonSignals: [
    "manifest_schema_version",
    "main_branch_source",
    "required_artifact_coverage",
    "required_quality_gate_coverage",
    "ci_run_url_present",
  ],
  operatorCommand:
    "PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py --repo coreyheckel3/ml-platform --branch main --workflow ci.yml --artifact-name forgeml-release-manifest",
};

export const scheduledReleaseEvidenceRefresh: ScheduledReleaseEvidenceRefresh = {
  staleAfterSeconds: 86_400,
  refreshIntervalSeconds: 3_600,
  operatorCommand:
    "PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --base-url http://127.0.0.1:8001 --once --stale-after-seconds 86400",
  cronCommand:
    "*/30 * * * * cd /path/to/ml-platform && PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --base-url http://127.0.0.1:8001 --stale-after-seconds 86400",
};

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
    label: "Retrieve live release evidence",
    command: liveReleaseEvidenceRetrieval.operatorCommand,
    signal:
      "Fetches the latest successful main-branch release manifest artifact and compares it with the release contract.",
  },
  {
    label: "Refresh stale release evidence",
    command: scheduledReleaseEvidenceRefresh.operatorCommand,
    signal:
      "Checks the persisted last-success report and retrieves new evidence only when the platform marks it stale.",
  },
  {
    label: "Capture demo screenshots",
    command: "make demo-screenshots",
    signal: "Generates reviewer screenshots through Playwright against mocked APIs.",
  },
];
