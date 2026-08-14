# CI/CD Strategy

ForgeML should use GitHub Actions for validation, image builds, infrastructure plans, and controlled deployments.

## CI Principles

- Every pull request runs the same quality gates.
- Build artifacts are immutable.
- Images are promoted by digest.
- Infrastructure plans are reviewed before apply.
- Production deployment requires manual approval.
- Secrets are accessed through GitHub OIDC and cloud IAM, not static long-lived credentials.

## Pull Request Workflow

Required checks:

| Check | Scope |
| --- | --- |
| Backend format | Python formatting |
| Backend lint | Python lint rules |
| Backend tests | Unit, integration, API |
| Frontend format | TypeScript and CSS formatting |
| Frontend lint | React and TypeScript lint rules |
| Frontend tests | Unit and component tests |
| Playwright E2E | Browser lifecycle flow with stateful ForgeML API mocks |
| Docker build | API, frontend, worker, Airflow, training, inference images |
| Terraform validate | Changed Terraform modules and environments |
| Security scan | Dependencies and container images |
| Alembic migration contract | Migration graph topology, single head, parent links, and rollback hooks |
| SQLAlchemy schema contract | Registered metadata, required tables, columns, keys, indexes, and constraints |
| Problem Details contract | API error envelope fields, handlers, and sanitized validation details |
| Runtime config policy | Production-like settings guardrails and contract freshness |
| Request logging contract | Structured HTTP log event fields and redaction policy |
| Security hardening contract | Organization isolation, RBAC matrix, rate-limit partitioning, audit redaction, and secrets/runtime evidence |
| Release smoke contract | Required live API smoke stages, read-only posture, and operator command |
| Release manifest contract | Required artifact hashes, image targets, evidence types, and quality gates |
| Artifact manifest contract | Dataset/model artifact manifest shape, storage boundary, checksums, and lineage producers |
| MLflow tracking contract | Tracking adapter boundary, REST sync endpoints, lineage tags, and sync failure semantics |
| Airflow orchestration contract | Workflow gateway boundary, training DAG-run payload, status mapping, and polling API |
| Deployment runtime contract | Serving runtime gateway boundary, traffic semantics, rollback draining, revision routing, and health probes |
| Monitoring dashboard contract | Project operations overview, signal families, frontend dashboard sections, and test coverage |
| Release evidence workflow | Manifest generation and artifact upload after required release gates |
| Release evidence UX contract | Frontend evidence route, reviewer commands, screenshot catalog, and product-surface coverage |
| Release manifest verifier | Artifact integrity, Dockerfile integrity, quality gates, and CI evidence linkage |
| Demo readiness contract | One-command demo stack, seeded refresh, screenshot capture, runbook, and architecture walkthrough |
| CI runtime contract | Current GitHub Actions runtime pins and retired action major detection |
| Portfolio readiness contract | Reviewer guide, resume bullets, evidence map, architecture diagrams, and screenshot catalog |
| Production readiness | Runbook, observability, load-test, Compose, and staging Terraform checks |

## Main Branch Workflow

After merge:

1. Build versioned Docker images.
2. Push images to ECR.
3. Generate OpenAPI contract artifact.
4. Validate artifact manifest storage, MLflow tracking, Airflow orchestration, deployment runtime, monitoring dashboard, security hardening, release evidence UX, demo readiness, CI runtime, and portfolio readiness contracts.
5. Run database migration dry-run against staging clone where available.
6. Deploy to staging.
7. Run release smoke, API smoke tests, and k6 smoke load tests against staging.
8. Build, verify, and publish the release manifest artifact with contract hashes, image targets, CI evidence, and smoke evidence.

## Production Deployment Workflow

Production deployment should require:

- Successful staging deployment.
- Passing smoke tests.
- Passing production-readiness checks.
- Reviewed Terraform plan when infrastructure changes are included.
- Manual approval.
- Rollback instructions attached to the deployment record.

## Database Migrations

Migration policy:

- Migrations run before application rollout only when backward compatible.
- Breaking schema changes use expand-and-contract.
- Long-running backfills run as separate jobs.
- Production migration failure triggers rollback runbook.

## Docker Build Workflow

Each image build should:

- Use dependency lock files.
- Cache dependencies safely.
- Add image labels.
- Generate a software bill of materials where tooling is available.
- Run vulnerability scans.
- Push only on trusted branches.

## Release Artifacts

Each release should publish:

- Git SHA
- Image digests
- OpenAPI schema
- Problem Details API error contract
- Security contracts for API authorization, permissions, security hardening, and runtime config policy
- Observability contracts for structured request logging
- Monitoring dashboard contract for project operations overview and frontend signal coverage
- Operations contracts for release smoke validation, release manifest provenance, CI evidence publication, release evidence UX, manifest verification, demo readiness, CI runtime pins, and portfolio readiness
- Portfolio review assets covering reviewer guide, resume bullets, evidence map, architecture diagrams, and screenshot catalog
- Runtime contracts for deployment serving, traffic allocation, rollback, revision routing, and health probes
- CI release manifest artifact from the successful main-branch workflow run
- Release manifest verification report showing artifact hashes and CI evidence linkage are valid
- Alembic migration topology contract, SQLAlchemy schema contract, and head revision
- Terraform plan artifact when applicable
- Test summary
- Deployment environment

## Branch and Environment Policy

| Branch/Event | Action |
| --- | --- |
| Pull request | Validate only |
| Merge to main | Build and deploy staging |
| Tag or approved manual dispatch | Deploy production |
| Infrastructure PR | Terraform plan |
| Approved infrastructure workflow | Terraform apply |
