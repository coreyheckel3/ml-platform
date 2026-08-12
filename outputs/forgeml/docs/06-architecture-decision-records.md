# Architecture Decision Records

These ADRs are proposed. Major decisions should be confirmed before implementation starts.

## ADR-001: Use a Modular Monolith

Status: Proposed

Decision: Build ForgeML as a modular monolith instead of starting with microservices.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Modular monolith | Faster delivery, simpler local development, easier transactions, lower operational burden | Requires discipline to maintain boundaries |
| Microservices | Independent scaling and deployment per service | High operational complexity, distributed transactions, slower early product iteration |
| Single-layer monolith | Fastest initial coding | Becomes difficult to test, reason about, and extract |

Recommendation: Use a modular monolith.

Justification: ForgeML needs a broad product surface before service boundaries are empirically obvious. A modular monolith gives the team clean architecture and extraction paths without prematurely paying the cost of distributed systems.

## ADR-002: Enforce Clean Architecture with Ports and Adapters

Status: Proposed

Decision: Each backend module should use API, application, domain, repository interface, and infrastructure layers.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Ports and adapters | Testable, replaceable infrastructure, clear domain ownership | More files and conventions |
| Active record style | Quick CRUD implementation | Couples business rules to persistence |
| Service-only modules | Simple initially | Domain logic tends to sprawl |

Recommendation: Use clean architecture with ports and adapters.

Justification: ML platforms integrate many external systems. Keeping MLflow, Airflow, Redis, Postgres, S3, and cloud APIs behind interfaces is essential for testability and future replacement.

## ADR-003: Use PostgreSQL, Redis, and Object Storage

Status: Proposed

Decision: Store metadata in PostgreSQL, ephemeral coordination in Redis, and large immutable data/artifacts in S3-compatible object storage.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| PostgreSQL plus Redis plus S3 | Proven, scalable, operationally familiar | Requires multiple local services |
| PostgreSQL only | Simpler local setup | Poor fit for large artifacts and ephemeral counters |
| Document database | Flexible schemas | Weaker relational integrity for lineage and approvals |

Recommendation: Use PostgreSQL, Redis, and object storage.

Justification: This split matches the access patterns of ML platforms: relational metadata, large artifacts, and short-lived operational state.

## ADR-004: Use Airflow for Workflow Orchestration

Status: Proposed

Decision: Use Airflow for long-running ML workflows rather than implementing a custom orchestrator.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Airflow | Mature scheduling, retries, backfills, operational UI | Requires DAG discipline and deployment management |
| Celery-only workers | Simpler for short jobs | Weak DAG semantics and backfills |
| Custom orchestrator | Full product control | High risk and large implementation cost |

Recommendation: Use Airflow behind a ForgeML orchestration interface.

Justification: Dataset validation, feature materialization, training, evaluation, drift checks, and retraining all need workflow semantics. Airflow provides those primitives while ForgeML keeps its own product language.

## ADR-005: Integrate MLflow Behind ForgeML Interfaces

Status: Proposed

Decision: Use MLflow for experiment tracking and model artifact interoperability, but expose ForgeML-owned abstractions to the rest of the codebase.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| MLflow adapter | Mature tracking, model packaging, ecosystem familiarity | Requires mapping MLflow concepts to ForgeML concepts |
| Build tracking from scratch | Total control | Reinvents substantial commodity infrastructure |
| Direct MLflow dependency everywhere | Fast initially | Leaks vendor-specific concepts across the platform |

Recommendation: Use MLflow through adapter interfaces.

Justification: This gives portfolio-grade realism while maintaining architectural independence.

## ADR-006: Use JWT Authentication with RBAC

Status: Proposed

Decision: Use JWT access tokens, refresh tokens, service accounts, API keys, and role-based access control.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| JWT plus RBAC | Works for web, APIs, CI automation, and service accounts | Requires careful token revocation and permission checks |
| Session cookies only | Simple browser auth | Less convenient for SDK and automation clients |
| External IdP only | Enterprise-ready | Adds setup friction for a portfolio project |

Recommendation: Use JWT plus RBAC internally, with an interface that can later integrate SSO.

Justification: ForgeML needs secure defaults and automation support without requiring enterprise identity infrastructure on day one.

## ADR-007: Use AWS EKS for Production Runtime

Status: Proposed

Decision: Target AWS EKS for production deployment while using Docker Compose for local development.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| EKS | Strong fit for Airflow, inference, autoscaling, GPU jobs, ecosystem tools | Higher operational complexity |
| ECS Fargate | Simpler managed containers | Less flexible for ML orchestration and future GPU/runtime patterns |
| Single EC2 host | Easy demo deployment | Not credible for scalable platform architecture |

Recommendation: Use EKS for production.

Justification: An internal ML platform will eventually need heterogeneous workloads, autoscaling, isolated runtimes, and strong deployment primitives. EKS is the better long-term foundation.

## ADR-008: Use Terraform Modules per Infrastructure Boundary

Status: Proposed

Decision: Manage cloud infrastructure with Terraform modules for network, EKS, RDS, Redis, S3, ECR, IAM, observability, secrets, and CI OIDC.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Terraform modules | Reusable, reviewable, environment-aware | Requires module discipline |
| Ad hoc Terraform | Quick early setup | Drifts quickly and is hard to review |
| ClickOps | Fast demos | Not repeatable or production-worthy |

Recommendation: Use explicit Terraform modules.

Justification: Infrastructure should be versioned, reviewable, and repeatable across dev, staging, and production.

## ADR-009: Use OpenTelemetry, Prometheus, and Grafana

Status: Proposed

Decision: Instrument the platform with OpenTelemetry, expose Prometheus metrics, and use Grafana dashboards.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| OpenTelemetry plus Prometheus plus Grafana | Open standards, broad ecosystem, good local and cloud story | Requires metric naming discipline |
| CloudWatch only | Native AWS integration | Less portable and weaker local development parity |
| Logs only | Easy to start | Insufficient for SLOs and drift monitoring |

Recommendation: Use OpenTelemetry, Prometheus, and Grafana.

Justification: ML platforms need metrics, logs, and traces across APIs, workflows, training, and inference. Open standards keep the architecture portable.

## ADR-010: Keep Example Projects Outside Core Platform Logic

Status: Proposed

Decision: Implement Movie Recommendation, Semantic Search, and Fraud Detection as examples that use public ForgeML interfaces.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Examples outside core | Demonstrates extensibility and prevents platform coupling | Requires slightly more setup |
| Hardcoded examples in product modules | Fast demos | Misrepresents platform architecture |
| Separate repositories | Clean isolation | More operational overhead for early development |

Recommendation: Keep examples in `ml/examples` and require them to use public APIs or SDKs.

Justification: The platform should prove that it generalizes beyond the examples.

## ADR-011: Use Canary Deployment and Explicit Rollback Records

Status: Proposed

Decision: Model deployment should create immutable deployment revisions and support canary rollout, promotion, and rollback.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Canary revisions | Safer production changes, auditability, realistic platform behavior | More workflow complexity |
| Immediate full rollout | Simple | Riskier and less credible for production ML |
| Manual replacement only | Easy to implement | Weak operational story |

Recommendation: Use deployment revisions with canary and rollback from the first deployment milestone.

Justification: Model deployment is a high-risk workflow. Safe rollout mechanisms are core platform capability, not polish.

## ADR-012: Use an Outbox for Domain Events

Status: Proposed

Decision: Persist domain events to an outbox table inside the same transaction as aggregate changes.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Transactional outbox | Reliable event publication, future broker migration | Requires dispatcher implementation |
| In-process events only | Simple | Events can be lost on process failure |
| External broker from day one | Scalable | Adds operational complexity before needed |

Recommendation: Use a transactional outbox.

Justification: ForgeML needs reliable workflow triggers and auditability without starting as a distributed system.

## ADR-013: Enforce Production Runtime Configuration Guardrails at Startup

Status: Accepted

Decision: Validate production-like runtime settings during FastAPI app creation and fail fast when unsafe local defaults are present.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Startup validation plus CI contract | Catches unsafe deploys before the API accepts traffic, documents policy, and prevents contract drift | Requires explicit production settings for staging and production |
| CI-only policy check | Easy to review and does not affect runtime boot | Can be bypassed by manual or external deployments |
| Deployment checklist only | Low implementation cost | Relies on humans to remember security-critical settings |

Recommendation: Use startup validation backed by a checked-in runtime config policy contract.

Justification: Secrets, docs exposure, CORS, rate limiting, and backing service endpoints are security boundaries. A platform used by many ML engineers should fail closed in production-like environments while preserving fast local development.

## ADR-014: Use Dependency-Aware Readiness for Traffic Admission

Status: Accepted

Decision: Make `/health/ready` execute typed dependency probes when readiness checks are enabled and return `503` when any required control-plane dependency is unavailable.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Dependency-aware readiness | Prevents unhealthy instances from receiving traffic and exposes probe metrics | Requires local opt-out for tests and lightweight demos |
| Static readiness | Simple and always fast | Marks broken instances ready even when PostgreSQL or Redis is unavailable |
| External-only health checks | Keeps app code small | Loses application-specific dependency context and sanitized failure semantics |

Recommendation: Use app-level readiness probes for PostgreSQL and Redis, with production config policy requiring them in production-like environments.

Justification: ForgeML is a control-plane-heavy platform. Routing traffic to an API that cannot reach metadata storage or cache infrastructure creates noisy failures across every ML workflow, so readiness should be a first-class platform contract.

## ADR-015: Emit Contracted Structured Request Logs

Status: Accepted

Decision: Emit JSON-compatible HTTP request log events from the API middleware and gate the event shape with a checked observability contract.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Contracted structured request logs | Searchable, traceable, dashboard-ready, and stable for downstream tooling | Requires schema discipline and redaction tests |
| Free-form access logs | Easy to emit | Hard to query consistently and easy to leak unsafe values |
| External proxy logs only | Low app complexity | Misses application route names, trace IDs, and platform-specific redaction policy |

Recommendation: Use application-emitted request logs with a versioned event schema and CI contract.

Justification: Internal ML platforms need operational forensics across APIs, workers, deployments, and model workflows. A stable request log schema gives engineers traceability without coupling log consumers to incidental framework output.

## ADR-016: Normalize API Errors with Problem Details

Status: Accepted

Decision: Normalize domain errors, request validation errors, HTTP exceptions, and unexpected exceptions into a versioned Problem Details envelope with trace IDs and sanitized details.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Contracted Problem Details envelope | Stable for frontend, SDKs, automation, and incident triage | Requires handler and contract maintenance |
| Framework-default errors | Minimal implementation | Shape varies by exception type and can expose raw validation input |
| Per-module error shapes | Local flexibility | Hard for clients to parse and hard to govern |

Recommendation: Use one API-wide Problem Details envelope backed by a checked contract.

Justification: ML platform clients need reliable failure semantics for automation, notebooks, SDKs, and UI workflows. A consistent trace-linked error envelope improves debugging while keeping sensitive input out of responses.

## ADR-017: Govern Schema Evolution with an Alembic Topology Contract

Status: Accepted

Decision: Publish a versioned Alembic migration contract and gate CI plus production-readiness on migration graph validity and contract freshness.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Checked Alembic topology contract | Makes schema lineage reviewable, catches duplicate heads early, and documents release state | Requires regeneration for intentional migration changes |
| Rely on Alembic at deploy time | Uses existing migration tooling | Finds graph mistakes late, often during release pressure |
| Manual migration checklist | Easy to start | Inconsistent and hard to audit across many contributors |

Recommendation: Use a checked migration topology contract generated from Alembic files.

Justification: ForgeML's modules share a PostgreSQL control plane, so schema drift can break authentication, datasets, training, registry, deployment, inference, and retraining workflows at once. A deterministic contract catches unsafe migration graph changes in review and gives release operators an explicit schema artifact.

## ADR-018: Publish SQLAlchemy Metadata as a Schema Contract

Status: Accepted

Decision: Generate a deterministic SQLAlchemy schema contract from `Base.metadata` and gate CI plus production-readiness on contract freshness and metadata invariants.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Checked SQLAlchemy metadata contract | Catches unregistered tables, column drift, missing indexes, and review-time schema changes | Requires regeneration for intentional ORM changes |
| Alembic topology only | Confirms migration graph health | Does not prove application metadata is complete |
| Runtime database inspection only | Verifies deployed database state | Too late for pull-request review and requires infrastructure |

Recommendation: Use a checked SQLAlchemy metadata contract alongside the Alembic migration topology contract.

Justification: Alembic governs how schema changes are applied, while SQLAlchemy metadata governs what the application believes exists. ForgeML needs both contracts because a modular monolith can otherwise ship with valid migrations but incomplete application metadata registration or under-indexed query paths.

## ADR-019: Use Stateful Browser API Mocks for Control-Plane E2E Coverage

Status: Accepted

Decision: Run Playwright against the Vite app with network-level ForgeML API mocks that preserve lifecycle state across pages.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Stateful browser API mocks | Fast, deterministic, catches real route/form/API-contract drift in the UI | Does not prove deployed backend infrastructure is reachable |
| Full-stack E2E for every frontend CI run | Highest fidelity for integrated services | Slower, more fragile, and duplicates backend API/integration coverage |
| Component tests only | Fast and already deterministic | Misses shell navigation, route state, local storage context, and cross-page workflows |

Recommendation: Use stateful browser API mocks for frontend CI, then reserve full-stack smoke tests for release candidates and local operator validation.

Justification: ForgeML's UI is a control plane over many backend modules. Browser-level coverage should prove an engineer can move through the lifecycle, while backend API tests continue to prove persistence and domain behavior. This split keeps feedback fast without reducing architectural confidence.

## ADR-020: Release Candidate Smoke Governance

Status: Accepted

Decision: Maintain a non-mutating release smoke runner plus a versioned operations contract that is checked in CI and production-readiness.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Contracted live smoke runner | Gives operators real API evidence, stays repeatable, and avoids data mutation in shared environments | Requires a seeded user and at least one project context |
| Mandatory full-stack browser smoke in every PR | Highest fidelity for UI plus API integration | Slower and more fragile than the existing mocked browser E2E gate |
| Manual checklist only | Flexible and easy to change | Hard to review, hard to automate, and likely to drift from the product surface |

Recommendation: Use a read-only API smoke harness for release-candidate and local operator validation, while CI gates the harness contract rather than standing up every dependency for each pull request.

Justification: ForgeML already has backend API tests and browser-level lifecycle coverage. The remaining gap is release evidence against a live target. A contracted smoke runner proves health, auth, project context, and ML platform control-plane surfaces without turning ordinary CI into an unreliable staging clone.

## ADR-021: Release Manifest Provenance

Status: Accepted

Decision: Build a versioned release manifest that records source revision, required contract hashes, Docker image targets, quality gates, and release evidence.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Versioned release manifest | Makes releases reviewable, reproducible, and easy to audit across contracts, images, and smoke evidence | Requires updating manifest contracts when release evidence changes |
| CI logs as release evidence | Already available from GitHub Actions | Hard to consume programmatically and incomplete without artifact hashes |
| Manual release notes only | Flexible for humans | Weak provenance and no deterministic connection to checked contracts |

Recommendation: Generate a JSON release manifest and gate the manifest contract in CI plus production-readiness.

Justification: ForgeML is accumulating production contracts across APIs, schemas, security, observability, and operations. A release manifest ties those contracts to a source revision and deployable image set, giving reviewers a compact evidence packet instead of scattered CI logs and ad hoc release notes.

## ADR-022: Publish Release Evidence From CI

Status: Accepted

Decision: Add a main-branch CI job that builds the ForgeML release manifest after backend, frontend, Docker, and production-readiness gates pass, then uploads it as a workflow artifact.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| CI-published release manifest artifact | Gives every successful main run a durable evidence bundle tied to the workflow URL | Adds one workflow job and artifact retention dependency |
| Operator-only manifest generation | Flexible and works outside GitHub Actions | Easy to forget and harder to prove for portfolio review |
| Release notes without artifact upload | Human-readable | Weak evidence chain and no machine-readable provenance |

Recommendation: Publish the release manifest from CI and keep the workflow behavior under an operations contract.

Justification: ForgeML already generates the manifest locally. Publishing it from CI turns provenance into an automatic release artifact attached to the exact run that validated the platform, which is closer to how mature internal ML platforms handle promotion evidence.

## ADR-023: Verify Release Manifests Before Promotion

Status: Accepted

Decision: Maintain a release manifest verifier CLI and checked operations contract, and run the verifier inside the release-evidence CI job before artifact upload.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Contracted manifest verifier | Proves artifact hashes, Dockerfile hashes, quality gates, and CI evidence linkage from a downloaded manifest | Adds another release governance contract to maintain |
| Trust the manifest builder only | Simple and already automated | Does not catch artifact mutation, stale source checkout evidence, or invalid downloaded evidence |
| Manual review only | Familiar and flexible | Hard to repeat and weak for machine-readable release evidence |

Recommendation: Verify manifests with a deterministic CLI and gate verifier behavior in CI plus production-readiness.

Justification: Release provenance should not stop at generating JSON. Internal ML platforms need promotion evidence that can be rechecked by operators, auditors, and interview reviewers without trusting memory or screenshots. A verifier closes the loop between CI output and source-controlled contracts.

## ADR-024: Project Monitoring Operations Read Model

Status: Accepted

Decision: Expose a project-scoped monitoring operations API that aggregates
inference, drift, training failure, and retraining activity signals for the
dashboard.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Project operations read model | Gives the UI one stable operational contract and keeps aggregation close to repositories | Adds one purpose-built read path to maintain |
| Compose many existing endpoints in the frontend | Reuses current APIs directly | Pushes operational joins, loading states, and consistency concerns into browser code |
| Prometheus-only dashboard | Excellent for infrastructure metrics | Does not include product metadata such as projects, endpoints, drift reports, policies, and training run lineage |

Recommendation: Use a backend-owned project operations read model and keep
Prometheus as the source for low-level infrastructure and route metrics.

Justification: ML operators need a fast triage page that connects platform
metadata with runtime signals. Aggregating those signals behind
`monitoring:read` gives the dashboard a stable contract, makes tests more
deterministic, and preserves extraction paths for a future monitoring service.

## ADR-025: Security Hardening Contract

Status: Accepted

Decision: Maintain a versioned security hardening contract that ties
organization isolation tests, RBAC matrix tests, rate-limit behavior, audit
metadata redaction, and secrets/runtime guardrail evidence to CI and release
manifests.

Options considered:

| Option | Pros | Cons |
| --- | --- | --- |
| Security hardening contract | Makes high-risk controls reviewable and release-gated across tests, docs, and manifests | Requires updates when intentional control scope changes |
| Scattered security tests only | Simple to add incrementally | Hard for reviewers to know which controls are covered and easy to miss in release evidence |
| Documentation-only security checklist | Easy to read | Does not prove behavior or prevent drift |

Recommendation: Use a checked contract plus behavioral tests for tenant
isolation, RBAC, rate limiting, and audit redaction.

Justification: ForgeML is a multi-tenant ML platform prototype. Security claims
need evidence that can be reviewed in code and attached to release provenance,
especially for organization isolation and least-privilege role behavior.
