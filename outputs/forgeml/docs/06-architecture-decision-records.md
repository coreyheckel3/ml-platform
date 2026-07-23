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

