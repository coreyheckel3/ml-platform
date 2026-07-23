# ForgeML

ForgeML is a modular monolith machine learning platform for dataset management, feature pipelines, experiment tracking, model registry workflows, deployments, inference monitoring, drift detection, and retraining.

The project is intentionally structured like an internal ML platform control plane: clean module boundaries, ports and adapters, explicit infrastructure contracts, tested domain logic, and production-oriented operations from the first sprint.

## Current Implementation State

Implemented foundation:

- FastAPI backend package with modular architecture boundaries.
- Authentication application service with secure password hashing and signed JWT-compatible tokens.
- Project application service with RBAC checks and slug policy.
- Dataset registry with dataset CRUD, immutable version records, upload instructions, schema inference, validation runs, and SQLAlchemy persistence.
- Feature store metadata with feature sets, definitions, pipeline registration, lineage, materialization records, and orchestration adapter boundary.
- Experiment tracking with experiment groups, linked run records, parameters, metrics, evaluation reports, and artifact metadata.
- Training run workflow lifecycle with orchestration adapter boundary, dataset or feature-set lineage, result recording, cancellation, and experiment-run synchronization.
- Model registry with registered models, versioning from succeeded training runs, signatures, metrics, approval workflow, and lineage.
- Deployments with approved-model-version gating, immutable revisions, canary traffic allocation, health checks, rollback, events, and serving orchestrator boundary.
- Inference endpoints with deployment-revision attribution, request logs, deterministic runtime adapter, prediction response contracts, and metric snapshots.
- Monitoring read APIs for project inference summaries, endpoint latency, prediction counts, error rates, and active alert counts.
- Alerting with rule definitions, threshold evaluation over inference snapshots, deduplicated alert events, acknowledgement, and resolution.
- Drift detection with reference profiles, production-window reports over inference request logs, feature-level drift scores, and analyzer adapter boundary.
- Automatic retraining with deployment-scoped policies, drift and alert trigger evaluation, cooldowns, daily run limits, approval gates, idempotent source handling, and Training module handoff.
- Example project manifests for Movie Recommendation, Semantic Search, and Fraud Detection, including fixture datasets, evaluation reports, SDK validation, and idempotent bootstrap automation through public APIs.
- SQLAlchemy 2.x repository implementations for auth, projects, datasets, feature store, experiments, training runs, model registry, deployments, inference, monitoring, alerting, drift detection, and retraining.
- Alembic migrations for organization, user, project, audit, outbox, dataset registry, feature store, experiments, training run, model registry, deployment, inference, alerting, drift detection, and retraining tables.
- React/Vite frontend shell with SaaS-style navigation and core pages.
- Example Projects page showing cross-workload lifecycle coverage without coupling core platform modules to example names.
- Docker Compose infrastructure for local platform services.
- GitHub Actions CI skeleton.
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

Run backend:

```bash
make backend-dev
```

Run frontend:

```bash
make frontend-dev
```

Bootstrap reference projects into a running local API:

```bash
PYTHONPATH=. .venv/bin/python scripts/examples/bootstrap_examples.py
```

## Architecture

Start with [the architecture index](outputs/forgeml/docs/index.md).
