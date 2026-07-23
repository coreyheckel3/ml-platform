# Docker Strategy

ForgeML should use Docker for repeatable local development, CI validation, and production image builds. Local development should run through Docker Compose. Production should run the same application images in EKS.

## Image Inventory

| Image | Purpose |
| --- | --- |
| `forgeml-backend-api` | FastAPI control plane |
| `forgeml-backend-worker` | Short-running asynchronous control-plane work |
| `forgeml-frontend` | Vite-built React application served by static server or nginx |
| `forgeml-airflow` | Airflow with ForgeML DAGs, operators, and dependencies |
| `forgeml-training` | Base training image with PyTorch, XGBoost, LightGBM, scikit-learn |
| `forgeml-inference` | Model serving runtime |

## Build Principles

- Use multi-stage builds.
- Pin base image major/minor versions.
- Run containers as non-root users.
- Keep build dependencies out of runtime images.
- Use dependency lock files.
- Fail builds on known critical vulnerabilities where feasible.
- Emit image labels with git SHA, build time, and source repository.
- Keep training and inference images separate from the API image.

## Local Docker Compose

Local Compose should include:

- Backend API
- Frontend dev server
- Backend worker
- PostgreSQL
- Redis
- S3-compatible object storage such as MinIO
- MLflow tracking server
- Airflow webserver
- Airflow scheduler
- Airflow worker
- Prometheus
- Grafana

Compose profiles should allow developers to start only what they need:

| Profile | Services |
| --- | --- |
| `core` | API, frontend, Postgres, Redis, object storage |
| `ml` | MLflow, Airflow, training worker |
| `observability` | Prometheus, Grafana |
| `full` | All services |

## Runtime Configuration

Configuration should come from environment variables mapped into typed Pydantic settings.

Required categories:

- Database URL
- Redis URL
- Object storage endpoint and bucket names
- JWT keys
- MLflow tracking URI
- Airflow API endpoint
- Prometheus configuration
- Log level
- Environment name

## Image Promotion

Images should be built once and promoted across environments by digest:

1. CI builds image.
2. CI tags image with git SHA.
3. CI pushes to ECR.
4. Staging deploy references immutable digest.
5. Production deploy promotes the same digest after validation.

## Model Runtime Images

Model serving should avoid baking platform-specific assumptions into every model image. The inference runtime should:

- Load a model artifact by URI.
- Validate request payloads against a model signature.
- Emit standardized metrics.
- Return model version and deployment revision metadata.
- Support graceful shutdown.
- Expose `/health/live` and `/health/ready`.

## Docker Security

- Use non-root users.
- Avoid mounting the Docker socket.
- Do not place secrets in images.
- Scan images in CI.
- Keep runtime images minimal.
- Set resource limits in Compose and Kubernetes manifests where useful.

