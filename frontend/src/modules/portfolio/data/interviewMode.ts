export type InterviewEvidence = {
  label: string;
  path: string;
  kind: "code" | "contract" | "test" | "doc" | "route";
};

export type InterviewClaim = {
  id: string;
  title: string;
  summary: string;
  proof: string;
  route: string;
  roleSignals: string[];
  evidence: InterviewEvidence[];
};

export type ArchitectureWalkthroughStep = {
  stage: string;
  moduleBoundary: string;
  staffSignal: string;
  extractionPath: string;
  evidencePath: string;
};

export type EvidenceExplanation = {
  title: string;
  whyItMatters: string;
  reviewerMove: string;
  evidencePath: string;
};

export type ValidationPath = {
  label: string;
  command: string;
  expectedSignal: string;
  route: string;
};

export type InterviewQuestion = {
  question: string;
  answerAnchor: string;
  evidenceRoute: string;
};

export const interviewClaims: InterviewClaim[] = [
  {
    id: "multi-project-control-plane",
    title: "Multi-project ML platform control plane",
    summary:
      "ForgeML models datasets, features, experiments, training runs, registry approvals, deployments, inference, monitoring, drift, alerts, retraining, and release evidence across independent ML projects.",
    proof:
      "The platform supports Movie Recommendation, Semantic Search, and Fraud Detection through shared APIs and seeded manifests, not project-specific branches.",
    route: "/examples",
    roleSignals: ["ML Engineer", "MLOps Engineer", "AI Platform Engineer"],
    evidence: [
      {
        label: "Example project manifests",
        path: "examples/projects",
        kind: "code",
      },
      {
        label: "Bootstrap through public APIs",
        path: "scripts/examples/bootstrap_examples.py",
        kind: "code",
      },
      {
        label: "Example catalog route",
        path: "/examples",
        kind: "route",
      },
    ],
  },
  {
    id: "modular-monolith",
    title: "Modular monolith with extractable boundaries",
    summary:
      "Each backend capability keeps API, application, domain, infrastructure, repositories, dependency wiring, and tests separate while sharing one deployable control plane.",
    proof:
      "The architecture favors module boundaries before distributed runtime cost, which keeps local development simple while preserving a path to extraction.",
    route: "/projects",
    roleSignals: ["Software Architect", "Backend / Platform Engineer"],
    evidence: [
      {
        label: "Module source tree",
        path: "backend/src/forgeml/modules",
        kind: "code",
      },
      {
        label: "Architecture walkthrough",
        path: "docs/architecture-walkthrough.md",
        kind: "doc",
      },
      {
        label: "System architecture",
        path: "outputs/forgeml/docs/01-system-architecture.md",
        kind: "doc",
      },
    ],
  },
  {
    id: "worker-training-lifecycle",
    title: "Worker-backed queued training lifecycle",
    summary:
      "Training runs move through queued, leased, running, succeeded, failed, and dead-letter states through a worker boundary instead of running inside API handlers.",
    proof:
      "The Training Runs page exposes lifecycle progress, elapsed time, worker logs, orchestration status, metrics, parameters, and artifact lineage.",
    route: "/training-runs",
    roleSignals: ["MLOps Engineer", "Distributed Systems"],
    evidence: [
      {
        label: "Training worker",
        path: "scripts/workers/run_training_worker.py",
        kind: "code",
      },
      {
        label: "Training run API tests",
        path: "backend/tests/api/test_training_runs_api.py",
        kind: "test",
      },
      {
        label: "Training run UI",
        path: "frontend/src/modules/training_runs/pages/TrainingRunsPage.tsx",
        kind: "code",
      },
    ],
  },
  {
    id: "external-adapter",
    title: "External recommender adapter without platform coupling",
    summary:
      "The conversational-movie-recommender integration sits behind named training and serving profiles so a local ML package can be exercised without hardcoding it into core platform workflows.",
    proof:
      "The adapter imports metrics and artifacts, records checksums, serves normalized recommendation traces, and keeps model-specific behavior behind profile contracts.",
    route: "/training-runs",
    roleSignals: ["ML Engineer", "AI Platform Engineer"],
    evidence: [
      {
        label: "External package adapter",
        path: "backend/src/forgeml/modules/training/infrastructure/external_package.py",
        kind: "code",
      },
      {
        label: "Adapter contract",
        path: "contracts/training/external-package-runner.v1.json",
        kind: "contract",
      },
      {
        label: "Serving runtime",
        path: "backend/src/forgeml/platform/serving/runtime.py",
        kind: "code",
      },
    ],
  },
  {
    id: "adaptive-operations-loop",
    title: "Observability, drift, alerts, and retraining loop",
    summary:
      "Monitoring, alerting, drift detection, and retraining are modeled as one operations loop with linked status reconciliation and live run observability.",
    proof:
      "A reviewer can move from inference snapshots to drift reports, alert events, retraining policy evaluations, and the resulting training run logs.",
    route: "/monitoring",
    roleSignals: ["MLOps Engineer", "Production ML"],
    evidence: [
      {
        label: "Monitoring dashboard contract",
        path: "contracts/observability/monitoring-dashboard.v1.json",
        kind: "contract",
      },
      {
        label: "Retraining UI",
        path: "frontend/src/modules/retraining/pages/RetrainingPage.tsx",
        kind: "code",
      },
      {
        label: "Drift detection API tests",
        path: "backend/tests/api/test_drift_detection_api.py",
        kind: "test",
      },
    ],
  },
  {
    id: "release-governance",
    title: "Release-governance loop with audit evidence",
    summary:
      "Release manifests, contract gates, CI artifacts, live evidence retrieval, scheduled refresh, notifications, and operational audit events make the project reviewer-verifiable.",
    proof:
      "The release-governance loop turns claims into checksums, quality gates, browser screenshots, GitHub Actions evidence, and an auditable timeline.",
    route: "/release-evidence",
    roleSignals: ["Staff Engineering", "DevOps", "Platform Reliability"],
    evidence: [
      {
        label: "Release manifest builder",
        path: "scripts/ops/build_release_manifest.py",
        kind: "code",
      },
      {
        label: "Portfolio readiness contract",
        path: "contracts/ops/portfolio-readiness.v1.json",
        kind: "contract",
      },
      {
        label: "Operational audit route",
        path: "/operational-audit",
        kind: "route",
      },
    ],
  },
];

export const architectureWalkthroughSteps: ArchitectureWalkthroughStep[] = [
  {
    stage: "1. Control plane",
    moduleBoundary: "FastAPI routes, application services, domain entities, repositories",
    staffSignal: "Clear ownership boundaries before service extraction.",
    extractionPath:
      "Projects, datasets, registry, deployment, and monitoring modules can move behind service APIs later.",
    evidencePath: "backend/src/forgeml/modules",
  },
  {
    stage: "2. ML execution",
    moduleBoundary: "Training runner, external package profiles, artifact manifests, MLflow gateway",
    staffSignal: "Training execution is asynchronous, observable, and adapter-backed.",
    extractionPath: "Workers, MLflow tracking, and artifact storage can scale independently.",
    evidencePath: "contracts/training/external-package-runner.v1.json",
  },
  {
    stage: "3. Serving runtime",
    moduleBoundary: "Deployment revision resolver, serving gateway, inference logs, health probes",
    staffSignal: "Canary, rollback, and external serving behavior are separated from product APIs.",
    extractionPath: "Inference runtime can become a dedicated model-serving service.",
    evidencePath: "contracts/runtime/deployment-serving.v1.json",
  },
  {
    stage: "4. Governance plane",
    moduleBoundary: "Security contracts, release manifests, evidence retrieval, audit timeline",
    staffSignal: "Operational proof is generated by CI and visible in the product.",
    extractionPath: "Release evidence, audit log, and notification delivery can move to platform governance services.",
    evidencePath: "contracts/ops/portfolio-interview-mode.v1.json",
  },
];

export const evidenceExplanations: EvidenceExplanation[] = [
  {
    title: "What proves this is not a toy project",
    whyItMatters:
      "Portfolio claims map to source files, API tests, e2e flows, contracts, release manifests, and GitHub Actions jobs.",
    reviewerMove:
      "Open the Portfolio page first, then use Release Evidence to inspect the CI-backed quality gates.",
    evidencePath: "docs/portfolio/evidence-map.md",
  },
  {
    title: "Where the ML engineering depth shows up",
    whyItMatters:
      "Training execution, artifact manifests, external adapters, model registry approval, and serving traces model production ML workflows.",
    reviewerMove:
      "Start at Training Runs, promote a model, create a deployment revision, then probe Inference.",
    evidencePath: "frontend/tests/e2e/platform-lifecycle.spec.ts",
  },
  {
    title: "Where the MLOps maturity shows up",
    whyItMatters:
      "Retries, leases, worker heartbeats, orchestration adapters, release gates, drift reports, alerts, and retraining policies form an operations loop.",
    reviewerMove:
      "Open Monitoring, Drift, Retraining, Release Evidence, and Operational Audit in that order.",
    evidencePath: "docs/runbooks/demo-readiness.md",
  },
  {
    title: "How to explain the architecture tradeoff",
    whyItMatters:
      "A modular monolith avoids early distributed-system cost while using adapters and contracts where future service boundaries matter.",
    reviewerMove:
      "Walk through the architecture stages and point to the repository modules and contracts beside each one.",
    evidencePath: "docs/architecture-walkthrough.md",
  },
];

export const validationPaths: ValidationPath[] = [
  {
    label: "Fresh reviewer environment",
    command: "make demo-stack-fresh",
    expectedSignal:
      "Repo-scoped reset, seeded data refresh, release manifest generation, and release evidence refresh are ready.",
    route: "/portfolio",
  },
  {
    label: "Browser interview walkthrough",
    command: "make demo-walkthrough",
    expectedSignal:
      "Playwright validates Portfolio Interview Mode, lifecycle pages, Release Evidence, and Operational Audit.",
    route: "/portfolio",
  },
  {
    label: "Deterministic screenshot package",
    command: "make demo-screenshots",
    expectedSignal:
      "Reviewer screenshots include 11-portfolio-interview-mode.png plus lifecycle and governance views.",
    route: "/portfolio",
  },
  {
    label: "Production readiness gate",
    command: "make production-readiness",
    expectedSignal:
      "Repository-wide checks enforce security, observability, demo readiness, release evidence, and portfolio contracts.",
    route: "/release-evidence",
  },
  {
    label: "Interview mode contract",
    command: "PYTHONPATH=. python scripts/ci/check_portfolio_interview_mode_contract.py",
    expectedSignal:
      "portfolio_interview_mode_contract proves the route, docs, screenshots, e2e flow, and CI wiring stay aligned.",
    route: "/portfolio",
  },
];

export const interviewQuestions: InterviewQuestion[] = [
  {
    question: "How did you avoid over-engineering with microservices?",
    answerAnchor:
      "Start with the modular monolith, then explain adapters, repository interfaces, and contract gates as extraction points.",
    evidenceRoute: "/portfolio",
  },
  {
    question: "Where is the production ML behavior?",
    answerAnchor:
      "Show queued training, worker execution, artifact manifests, MLflow/Airflow boundaries, registry approval, and serving health probes.",
    evidenceRoute: "/training-runs",
  },
  {
    question: "How would this support another model team?",
    answerAnchor:
      "Point to examples, project scoping, shared APIs, external package profiles, and absence of hardcoded project branches.",
    evidenceRoute: "/examples",
  },
  {
    question: "How do you know a release is safe?",
    answerAnchor:
      "Use release manifests, verification, GitHub Actions evidence retrieval, notification audit records, and production-readiness gates.",
    evidenceRoute: "/release-evidence",
  },
  {
    question: "What would you scale next?",
    answerAnchor:
      "Move workers, serving runtime, artifact storage, and governance components behind independently scalable service boundaries.",
    evidenceRoute: "/operational-audit",
  },
];
