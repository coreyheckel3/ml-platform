# Testing Strategy

ForgeML should treat tests as part of the architecture. No production code should be merged without appropriate tests for its layer and risk.

## Test Pyramid

```mermaid
flowchart TB
  E2E["Playwright E2E Tests"]
  Contract["Contract and API Tests"]
  Integration["Integration Tests"]
  Unit["Unit Tests"]
  Static["Static Checks"]

  E2E --> Contract
  Contract --> Integration
  Integration --> Unit
  Unit --> Static
```

## Backend Tests

### Unit Tests

Scope:

- Domain entities
- Value objects
- Policies
- Application services with mocked repositories
- Authorization decisions
- RBAC role matrix behavior
- Audit metadata redaction
- Schema compatibility checks
- Drift threshold logic

Rules:

- No network calls.
- No database dependency.
- Fast enough to run on every save.

### Integration Tests

Scope:

- SQLAlchemy repositories
- Multi-tenant repository isolation
- Alembic migrations
- Postgres constraints
- Redis rate limiting
- Object storage adapter
- MLflow adapter
- Airflow adapter contract boundaries

Rules:

- Use ephemeral infrastructure in CI.
- Reset database state per test or test class.
- Prefer real Postgres over SQLite for repository tests.

### API Tests

Scope:

- FastAPI routes
- Request and response validation
- Auth enforcement
- Rate-limit partitioning
- Error shapes
- Idempotency behavior
- Pagination

Rules:

- Exercise the API through HTTP clients.
- Assert permission boundaries.
- Assert trace IDs and stable error format.

## Frontend Tests

### Unit and Component Tests

Scope:

- Shared UI components
- Route guards
- Query hooks
- Form validation
- Table filtering and sorting
- State transitions

### Playwright E2E Tests

Critical flows:

- Login
- Create project
- Register dataset
- Finalize dataset version
- View validation result
- Launch training run
- Compare experiment runs
- Register and approve model
- Start canary rollout
- Roll back deployment
- View monitoring and alerts

Implementation guidance:

- Use network-level ForgeML API mocks for frontend CI so browser workflows stay deterministic and do not require Postgres, Redis, or object storage.
- Keep mocks stateful across pages so training success can feed model promotion, model approval can feed deployment, and inference snapshots can feed monitoring.
- Reserve live full-stack browser smoke tests for local operator validation and release-candidate environments.

## ML Workflow Tests

ML workflows need tests beyond ordinary application checks:

| Test Type | Purpose |
| --- | --- |
| Data validation tests | Ensure schema, nulls, ranges, and categorical constraints are enforced |
| Training smoke tests | Confirm each algorithm runner can train on a tiny fixture |
| Evaluation tests | Confirm metric calculations and report generation |
| Reproducibility tests | Confirm seeds and config produce stable expected behavior on fixture data |
| Model signature tests | Confirm inference contract matches registered signature |
| Drift tests | Confirm statistical tests trigger only when thresholds are crossed |

## Contract Tests

Contract tests should protect boundaries:

- Backend OpenAPI contract consumed by frontend.
- Problem Details API error envelope contract consumed by frontend and SDK clients.
- Alembic migration topology contract for base revision, head revision, parent links, and reversible migration hooks.
- SQLAlchemy schema metadata contract for registered tables, column shape, keys, constraints, and foreign-key index coverage.
- Runtime configuration policy contract enforced before production-like API startup.
- Security hardening contract for organization isolation, RBAC matrix, rate-limit partitioning, audit metadata redaction, and secrets/runtime guardrail evidence.
- Structured request logging contract with sensitive query-parameter redaction.
- Monitoring dashboard contract for project operations overview, inference errors, latency percentiles, drift trends, training failures, retraining activity, and frontend section coverage.
- Release smoke operations contract for the live API surfaces required during release-candidate validation.
- Release manifest operations contract for release artifact hashes, image targets, evidence types, and quality gates.
- Release evidence workflow contract for CI manifest publication behavior.
- Release manifest verification contract for artifact integrity and evidence linkage.
- MLflow tracking contract for adapter boundaries, REST endpoints, lineage tags, artifact-reference logging, and best-effort failure semantics.
- Airflow orchestration contract for gateway boundaries, REST DAG-run operations, training DAG conf payloads, state mapping, and polling API coverage.
- Deployment runtime contract for serving gateway boundaries, traffic semantics, rollback draining, revision routing, and health-probe API coverage.
- Inference runtime request/response schema.
- Event payload schemas under `contracts/events`.

MLflow integration tests cover the pure record builder, in-memory sync adapter,
HTTP REST request sequence, missing-experiment creation path, training service
sync reports, and sync-failure preservation of training terminal status.

Airflow orchestration tests cover local fallback status reporting, DAG trigger
payloads, deterministic DAG run ids, REST trigger/poll/cancel calls, external
state mapping, and API serialization of orchestration polling results.

Deployment runtime tests cover serving traffic planning, deployment service
canary and rollback behavior, runtime health probes, inference endpoint
revision resolution, API serialization, checked OpenAPI coverage, and CI
contract wiring.

Monitoring dashboard tests cover project operations aggregation, API
serialization, frontend rendering of inference, drift, training, and retraining
panels, checked OpenAPI coverage, and CI contract wiring.

## Release Smoke Tests

Release smoke tests should run after local seeding and against staging release candidates:

- Use `scripts/ops/release_smoke.py` for live API validation.
- Keep the smoke runner non-mutating so it can be repeated safely.
- Emit and archive the JSON report as release evidence.
- Cover health, auth, project context, datasets, feature store, experiments, training, training logs, registry, deployment, inference, monitoring, alerts, drift, and retraining.
- Keep CI focused on the checked operations contract; run live smoke in local operator validation and release-candidate environments.

## Release Manifest Tests

Release manifest tests should protect provenance and evidence quality:

- Hash every required checked contract and deployment artifact with SHA-256.
- Record source revision, branch, and worktree cleanliness.
- Capture Docker image targets and image digests when a promotion workflow provides them.
- Ingest release smoke JSON evidence when it is available.
- Keep the manifest contract checked in CI and production-readiness.

## Release Evidence Workflow Tests

Release evidence workflow tests should ensure CI does not silently stop publishing
release evidence:

- Require the release evidence job to depend on backend, frontend, Docker, and production-readiness jobs.
- Require manifest generation from `scripts/ops/build_release_manifest.py`.
- Require artifact upload through `actions/upload-artifact`.
- Fail when the manifest artifact path is missing.
- Keep workflow publication behavior captured in a checked operations contract.

## Release Manifest Verification Tests

Release manifest verification tests should prove release evidence can be checked
after it is created:

- Verify schema version, release metadata, source revision metadata, artifact hashes, Dockerfile hashes, quality gates, and CI evidence linkage.
- Fail when an artifact hash is tampered with.
- Fail when required quality gates are missing from the manifest.

## Demo Readiness Tests

Demo readiness tests should keep the reviewer path executable:

- Unit test the demo stack command plan without starting Docker or servers.
- Unit test seeded data refresh report generation with the API bootstrap boundary faked.
- Verify the checked demo readiness contract matches the command, runbook, screenshot, and architecture assets.
- Capture deterministic Playwright screenshots against stateful API mocks for reviewer-facing console surfaces.
- Include demo readiness in production-readiness and release manifest evidence.

## Artifact Manifest Tests

Artifact manifest tests protect object-store metadata and lineage:

- Validate deterministic dataset and model artifact manifest serialization.
- Verify manifest payload SHA-256 checksums after storage writes.
- Reject tampered payloads through checksum validation.
- Round-trip `artifact_manifest_uri` and `artifact_manifest_hash` through dataset and model repositories.
- Keep the artifact manifest contract checked in backend CI, release provenance, and production-readiness.
- Optionally require Docker image digests for promotion workflows that publish immutable images.
- Keep verifier behavior captured in a checked operations contract.

## CI Gates

Every pull request should run:

- Backend formatting check
- Backend lint
- Backend type check where configured
- Backend unit tests
- Backend integration tests
- API tests
- Alembic migration contract check
- SQLAlchemy schema contract check
- Frontend formatting check
- Frontend lint
- Frontend type check
- Frontend unit tests
- Playwright lifecycle E2E test
- Docker build
- Terraform format and validate when infra changes

## Coverage Expectations

Coverage should be risk-based:

| Area | Expectation |
| --- | --- |
| Domain policies | High unit coverage |
| Application services | High use-case coverage |
| Repositories | Integration coverage for each query path |
| API routes | Route, auth, validation, and error coverage |
| UI critical flows | Playwright coverage |
| ML runners | Smoke and reproducibility coverage |

## Test Data Strategy

- Use small deterministic fixtures.
- Keep large sample datasets out of git.
- Use generated synthetic data for fraud and recommendation tests.
- Use tiny embedded corpora for semantic search tests.
- Store golden reports only when they are stable and useful.
