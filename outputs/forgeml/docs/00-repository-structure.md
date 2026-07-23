# Repository Structure

ForgeML should use a monorepo with explicit boundaries between the backend control plane, frontend application, infrastructure, examples, and operational documentation.

## Proposed Layout

```text
forgeml/
  README.md
  LICENSE
  Makefile
  pyproject.toml
  package.json
  .env.example
  .gitignore
  .github/
    workflows/
      ci.yml
      docker-build.yml
      terraform-plan.yml
      terraform-apply.yml
  docs/
    architecture/
    adr/
    api/
    operations/
    runbooks/
  backend/
    alembic.ini
    alembic/
      versions/
    src/
      forgeml/
        main.py
        config.py
        platform/
          api/
          application/
          domain/
          infrastructure/
          observability/
          security/
          database/
          messaging/
        modules/
          auth/
          projects/
          datasets/
          feature_store/
          training/
          experiments/
          model_registry/
          deployments/
          inference/
          monitoring/
          alerting/
          drift_detection/
          administration/
    tests/
      unit/
      integration/
      api/
      contract/
  frontend/
    index.html
    vite.config.ts
    tailwind.config.ts
    src/
      app/
      routes/
      shared/
      modules/
        dashboard/
        projects/
        datasets/
        experiments/
        training_runs/
        models/
        deployments/
        monitoring/
        alerts/
        settings/
      test/
    tests/
      unit/
      e2e/
  pipelines/
    airflow/
      dags/
      plugins/
      operators/
      sensors/
      tests/
  ml/
    libraries/
      forgeml_sdk/
      feature_pipelines/
      training/
      evaluation/
      inference/
    examples/
      movie_recommendation/
      semantic_search/
      fraud_detection/
  infra/
    terraform/
      environments/
        dev/
        staging/
        prod/
      modules/
        network/
        eks/
        rds/
        redis/
        s3/
        ecr/
        iam/
        observability/
        secrets/
        ci_oidc/
    docker/
      backend.Dockerfile
      frontend.Dockerfile
      airflow.Dockerfile
      training.Dockerfile
      inference.Dockerfile
    compose/
      docker-compose.yml
      docker-compose.observability.yml
  scripts/
    dev/
    ci/
    migrations/
    seed/
  contracts/
    openapi/
    events/
  benchmarks/
  security/
    threat-model.md
    dependency-policy.md
```

## Backend Module Shape

Every backend module should follow the same internal structure:

```text
modules/<module_name>/
  api/
    routes.py
    schemas.py
  application/
    commands.py
    queries.py
    services.py
    dto.py
  domain/
    entities.py
    value_objects.py
    events.py
    policies.py
    errors.py
  repositories/
    interfaces.py
  infrastructure/
    sqlalchemy_models.py
    sqlalchemy_repositories.py
    external_clients.py
  di.py
  tests/
    unit/
    integration/
    api/
```

## Dependency Rules

Dependencies flow inward:

1. `api` depends on `application`.
2. `application` depends on `domain` and repository interfaces.
3. `domain` has no dependency on FastAPI, SQLAlchemy, Redis, MLflow, Airflow, or cloud SDKs.
4. `infrastructure` implements interfaces defined by the module.
5. Cross-module calls go through application services or published domain events, not direct database access.

## Frontend Module Shape

Frontend modules should be organized by product area:

```text
frontend/src/modules/<area>/
  api/
  components/
  hooks/
  pages/
  routes.tsx
  types.ts
  __tests__/
```

Shared UI components belong in `frontend/src/shared/ui`. Cross-cutting client concerns such as TanStack Query configuration, auth state, route guards, telemetry, and error boundaries belong in `frontend/src/app`.

## Example Projects

The example projects must be isolated under `ml/examples`. They should consume ForgeML through public SDKs, APIs, and pipeline contracts. The platform must not contain conditionals or schemas that assume movie recommendation, semantic search, or fraud detection specifically.

## Extraction Readiness

Modules most likely to become independent services later:

| Candidate | Reason |
| --- | --- |
| Inference | Independent scale profile and latency SLOs. |
| Training | Heavy compute, GPU scheduling, separate worker pools. |
| Monitoring | High-cardinality metrics, streaming, retention policies. |
| Feature Store | Online/offline consistency and serving latency requirements. |
| Model Registry | Approval workflows and cross-environment promotion. |

Extraction should require replacing in-process adapters with network adapters, not rewriting domain logic.

