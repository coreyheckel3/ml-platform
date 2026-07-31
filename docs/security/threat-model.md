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
| Broken object-level authorization | RBAC checks in application services, project-scoped repositories, a CI-gated API authorization contract, and a checked permission catalog |
| Unauthenticated API exposure | Public route allowlist generated from FastAPI route dependencies and checked in CI |
| Request floods | Configurable rate limiting with metrics and retry headers |
| Browser exploitation | Secure response headers, strict CORS origins, disabled production API docs, and CI-gated runtime config policy |
| Unsafe model promotion | Training execution manifest validation, idempotent registry promotion, and approval gates before deployment revisions |
| Data/schema corruption | Immutable dataset versions, validation runs, backups before migration |
| Inference drift | Drift profiles, drift reports, alerting, and retraining policies |
| Supply-chain compromise | CI lint/test/build gates, production dependency audit gates, reduced frontend runtime dependency surface, and pinned runtime images where practical |

## Open Production Reviews

- External penetration test before public internet exposure
- Cloud IAM policy review before Terraform apply in shared AWS accounts
- Secret rotation drill before storing regulated data
- Load test above smoke scale before onboarding high-volume inference traffic
