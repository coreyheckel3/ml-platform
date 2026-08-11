# ForgeML

ForgeML is a modular monolith machine learning platform for dataset management, feature pipelines, experiment tracking, model registry workflows, deployments, inference monitoring, drift detection, and retraining.

The project is intentionally structured like an internal ML platform control plane: clean module boundaries, ports and adapters, explicit infrastructure contracts, tested domain logic, and production-oriented operations from the first sprint.

## Current Implementation State

Implemented foundation:

- FastAPI backend package with modular architecture boundaries.
- Authentication application service with secure password hashing, signed JWT-compatible access tokens, and revocable refresh-token rotation.
- Project application service with RBAC checks and slug policy.
- Dataset registry with dataset CRUD, immutable version records, upload instructions, schema inference, validation runs, and SQLAlchemy persistence.
- Feature store metadata with feature sets, definitions, pipeline registration, lineage, materialization records, and orchestration adapter boundary.
- Experiment tracking with experiment groups, linked run records, parameters, metrics, evaluation reports, and artifact metadata.
- Training run workflow lifecycle with orchestration adapter boundary, dataset or feature-set lineage, result recording, cancellation, and experiment-run synchronization.
- Model registry with registered models, validated and idempotent promotion from succeeded training execution manifests, signatures, metrics, approval workflow, and lineage.
- Deployments with approved-model-version gating, immutable revisions, canary traffic allocation, canary simulation, runtime health probes, rollback draining, events, and serving orchestrator boundary.
- Inference endpoints with current-traffic revision resolution, deployment-revision attribution, request logs, deterministic runtime adapter, prediction response contracts, endpoint health probes, and metric snapshots.
- Monitoring read APIs for project inference summaries, latency percentiles, endpoint error breakdowns, drift trends, training failures, retraining activity, and active alert counts.
- Administration audit log read and write paths with organization-scoped RBAC filtering, auth/project lifecycle instrumentation, ML operations instrumentation, and SQLAlchemy persistence.
- Alerting with rule definitions, threshold evaluation over inference snapshots, deduplicated alert events, acknowledgement, and resolution.
- Drift detection with reference profiles, production-window reports over inference request logs, feature-level drift scores, and analyzer adapter boundary.
- Automatic retraining with deployment-scoped policies, drift and alert trigger evaluation, cooldowns, daily run limits, approval gates, idempotent source handling, and Training module handoff.
- Example project manifests for Movie Recommendation, Semantic Search, and Fraud Detection, including fixture datasets, evaluation reports, SDK validation, and idempotent bootstrap automation through public APIs.
- Deterministic local example training jobs that generate versioned model and evaluation artifacts for the three reference workloads.
- Training execution runner contract with local example execution, generated artifact metadata, linked experiment-run updates, and an opt-in adapter selector for demo workloads.
- Production hardening with secure response headers, configurable API rate limiting, structured request logs, dependency readiness probes, production runtime config guardrails, Prometheus metrics for throttling, production-readiness CI checks, checked OpenAPI, Problem Details error contracts, Alembic migration topology contracts, SQLAlchemy schema metadata contracts, API authorization, permission catalog, runtime config policy, observability contracts, monitoring dashboard contracts, deployment runtime contracts, release-candidate smoke contracts, release manifest provenance, CI release evidence publishing, release manifest verification, frontend production dependency auditing, frontend bundle budgets, browser E2E lifecycle coverage, runbooks, threat model, backup and restore scripts, and k6 smoke load tests.
- SQLAlchemy 2.x repository implementations for auth, administration, projects, datasets, feature store, experiments, training runs, model registry, deployments, inference, monitoring, alerting, drift detection, and retraining.
- Alembic migrations for organization, user, refresh session, project, audit, outbox, dataset registry, feature store, experiments, training run, model registry, deployment, inference, alerting, drift detection, and retraining tables.
- React/Vite frontend shell with a first-party browser router, route-level code splitting, SaaS-style navigation, core pages, login and session management, project context operations, account and security settings, audit operations console, dataset ingestion operations, feature store operations, experiment operations, training run operations, registry promotion workbench, model approval actions, deployment release console, inference endpoint operations, monitoring operations drilldowns, alert operations workflows, drift operations workflows, and retraining operations workflows.
- Example Projects page showing cross-workload lifecycle coverage without coupling core platform modules to example names.
- Docker Compose infrastructure for local platform services.
- Docker Compose full profile with Prometheus and Grafana provisioning.
- GitHub Actions CI for backend, frontend, Docker, Terraform validation, and production-readiness checks.
- Architecture documentation in `outputs/forgeml/docs`.

## Local Development

Install backend dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Install frontend dependencies:

```bash
npm --prefix frontend install
```

Run tests:

```bash
make test
```

Run browser E2E lifecycle coverage:

```bash
npm --prefix frontend run e2e
```

Run production-readiness checks:

```bash
make production-readiness
```

Run the non-mutating release smoke against a seeded local API:

```bash
PYTHONPATH=. .venv/bin/python scripts/ops/release_smoke.py --base-url http://127.0.0.1:8001
```

Build a release provenance manifest:

```bash
PYTHONPATH=. .venv/bin/python scripts/ops/build_release_manifest.py --output /tmp/forgeml-release-manifest.json
```

Verify a release provenance manifest:

```bash
PYTHONPATH=. .venv/bin/python scripts/ops/verify_release_manifest.py --manifest /tmp/forgeml-release-manifest.json --require-ci-evidence
```

Verify the checked database migration contract:

```bash
PYTHONPATH=backend/src:. .venv/bin/python scripts/ci/check_alembic_migration_contract.py
```

Verify the checked SQLAlchemy schema contract:

```bash
PYTHONPATH=backend/src:. .venv/bin/python scripts/ci/check_sqlalchemy_schema_contract.py
```

Run backend:

```bash
make backend-dev
```

Seed the local admin account:

```bash
PYTHONPATH=backend/src .venv/bin/python scripts/dev/seed_backend.py
```

Run frontend:

```bash
make frontend-dev
```

The seeded local console account is `admin@forgeml.dev` with password `forgeml-local-admin`.

Bootstrap reference projects into a running local API:

```bash
PYTHONPATH=. .venv/bin/python scripts/examples/bootstrap_examples.py
```

The bootstrapper queues training runs through the API, executes the local example trainer outside the request path, and records generated metrics plus artifact metadata back into ForgeML.

Run deterministic local example training:

```bash
PYTHONPATH=. .venv/bin/python scripts/examples/run_local_training.py
```

Run one local worker polling cycle for an organization:

```bash
PYTHONPATH=. .venv/bin/python scripts/workers/run_training_worker.py --organization-id <organization-id>
```

## Architecture

Start with [the architecture index](outputs/forgeml/docs/index.md).
Operational runbooks live under [docs/runbooks](docs/runbooks).
