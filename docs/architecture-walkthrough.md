# ForgeML Architecture Walkthrough

This walkthrough is designed for a technical reviewer who wants to understand
how ForgeML is structured and why it resembles an internal ML platform instead
of a single-model application.

## System Shape

ForgeML starts as a modular monolith. The backend is one FastAPI deployable, but
the code is split by product capability so modules can be extracted later
without rewriting the domain model:

- Authentication
- Projects
- Datasets
- Feature Store
- Experiments
- Training
- Model Registry
- Deployments
- Inference
- Monitoring
- Alerting
- Drift Detection
- Retraining
- Administration

Each module keeps API routes, application services, domain objects, repository
interfaces, and SQLAlchemy repository implementations separate. The application
layer depends on interfaces; infrastructure adapters satisfy those interfaces.

## Control-Plane Lifecycle

The demo lifecycle follows the same path an ML engineer would use:

1. Create or select a project.
2. Register a dataset and immutable dataset version.
3. Validate schema metadata.
4. Define feature-store metadata and pipelines.
5. Create an experiment and training run.
6. Execute or record training results with versioned artifact metadata.
7. Promote the succeeded run into a registered model version.
8. Request and approve the model version.
9. Create a deployment revision and mark it healthy.
10. Route inference traffic to the healthy revision.
11. Capture inference metrics and request logs.
12. Evaluate alert, drift, and retraining policies from production signals.

This flow is exercised through API tests, Playwright browser coverage, release
smoke checks, and the demo seed refresh command.

## Data And Artifact Boundaries

PostgreSQL owns control-plane metadata: organizations, users, projects,
datasets, features, experiments, training runs, model versions, deployments,
inference logs, monitoring snapshots, alerts, drift reports, retraining policies,
and audit records.

Artifact metadata is represented through explicit manifests with SHA-256
checksums. The platform stores manifest URIs and hashes on dataset and model
version records so object storage can evolve from local/MinIO to S3-compatible
production storage without changing module-level contracts.

## Execution Boundaries

Training, MLflow, Airflow, artifact storage, and serving runtime integrations
sit behind adapter boundaries:

- Training jobs can run through the local example runner or orchestration adapters.
- External ML packages can run through named training profiles. The local
  `conversational-movie-recommender` profile executes its package CLI through
  the training worker, imports `evaluation.json` metrics, and records model
  artifacts in the standard ForgeML training execution manifest.
- MLflow sync is isolated behind a tracking gateway.
- Airflow orchestration is isolated behind a workflow gateway with local fallback.
- Deployment serving semantics are isolated behind a serving runtime gateway.
- Inference uses a routed runtime adapter boundary. Generic models keep the
  deterministic local runtime, while deployment revisions that declare the
  `conversational-movie-recommender` adapter call the external package over its
  `/api/recommend` and `/health` HTTP contract.
- Monitoring dashboards consume platform APIs rather than direct database reads.

These seams keep the modular monolith practical today while protecting future
service extraction paths.

## Security Model

The security model is organization-scoped by default. Users carry permissions,
repository queries are tenant-aware, and every protected route depends on the
authenticated principal. Role presets are defined in a permission catalog and
tested as a matrix.

Audit metadata is sanitized recursively before persistence, rate limits are
partitioned by client and path, and production-like runtime configuration is
checked at startup to reject unsafe defaults.

## Observability And Release Evidence

ForgeML exposes health probes, readiness probes, Prometheus metrics, structured
request logs, Grafana dashboard provisioning, release smoke checks, release
manifest generation, manifest verification, and GitHub Actions release evidence.

The CI pipeline runs backend tests, frontend tests, Playwright E2E, Docker
builds, production-readiness checks, and contract checks for API, database,
security, observability, artifacts, orchestration, deployment runtime, release,
and demo readiness.

## Demo Entry Points

Use `make demo-stack` to launch the local demo path. Use `make demo-refresh` to
refresh seeded examples against an already-running API. Use `make
demo-screenshots` to capture deterministic reviewer screenshots.

The demo readiness contract is checked by
`python scripts/ci/check_demo_readiness_contract.py`, and the runbook lives at
`docs/runbooks/demo-readiness.md`.
