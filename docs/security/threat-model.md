# ForgeML Threat Model

ForgeML is a modular monolith ML platform that stores control-plane metadata, model governance records, deployment configuration, and inference logs. The first production hardening scope focuses on the API, database, object storage, CI/CD, and observability surfaces.

## Assets

- User identities, password hashes, JWTs, roles, and permissions
- Dataset metadata, schema history, validation reports, and object URIs
- Feature definitions, lineage, and materialization records
- Experiment metrics, training run metadata, and artifact URIs
- Model versions, signatures, approvals, and lineage
- Deployment revisions, runtime configuration, inference request logs, and monitoring snapshots
- Drift reports, alert events, and retraining policies

## Trust Boundaries

- Browser to FastAPI API
- API to PostgreSQL
- API to Redis
- API to object storage
- API to orchestration systems such as Airflow and MLflow
- CI/CD runners to container registry and cloud infrastructure
- Operators to Terraform and production runtime

## Primary Risks and Controls

| Risk | Control |
| --- | --- |
| Credential disclosure | Environment-based secrets, production startup guardrails for non-default JWT secrets, no secret values in repository, rotation runbooks |
| Broken object-level authorization | RBAC checks in application services, project-scoped repositories, organization-isolation tests, a CI-gated API authorization contract, a checked permission catalog, and a security hardening contract |
| Unauthenticated API exposure | Public route allowlist generated from FastAPI route dependencies and checked in CI |
| Request floods | Configurable rate limiting with metrics, retry headers, and client/path partitioning tests |
| Browser exploitation | Secure response headers, strict CORS origins, disabled production API docs, and CI-gated runtime config policy |
| Serving unhealthy instances | Dependency-aware readiness probes for PostgreSQL and Redis with sanitized failure responses |
| Sensitive data in logs | Structured request logs avoid bodies, redact sensitive query parameters before emission, and sanitize audit metadata before persistence |
| Sensitive data in API errors | Problem Details handlers omit raw validation input and use a generic internal-error message |
| Unsafe model promotion | Training execution manifest validation, idempotent registry promotion, and approval gates before deployment revisions |
| Data/schema corruption | Immutable dataset versions, validation runs, backups before migration |
| Inference drift | Drift profiles, drift reports, alerting, and retraining policies |
| Supply-chain compromise | CI lint/test/build gates, production dependency audit gates, reduced frontend runtime dependency surface, and pinned runtime images where practical |

## Sprint 57 Security Evidence

Sprint 57 makes the highest-risk multi-tenant controls release-gated:

- Repository isolation tests seed two organizations in one database and verify project, dataset, training-run, and audit-log reads stay inside the caller organization.
- RBAC matrix tests prove role presets allow expected workflows and deny high-risk privileges such as audit reads, model review, deployment rollback, and retraining approval.
- Rate-limit tests verify the fixed-window limiter partitions budget by caller and route.
- Audit sanitization tests verify metadata keys containing credential, token, password, authorization, secret, JWT, refresh-token, or API-key markers are redacted recursively.
- `contracts/security/security-hardening.v1.json` records these controls for CI, production-readiness, and release manifest evidence.

## Open Production Reviews

- External penetration test before public internet exposure
- Cloud IAM policy review before Terraform apply in shared AWS accounts
- Secret rotation drill before storing regulated data
- Load test above smoke scale before onboarding high-volume inference traffic
