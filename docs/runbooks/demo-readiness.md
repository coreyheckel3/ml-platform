# Demo Readiness Runbook

This runbook is the reviewer path for a local ForgeML demo. It is optimized for
portfolio reviews, interview walkthroughs, and contributor onboarding.

## One-Command Stack

From the repository root, start the managed local demo stack:

```bash
make demo-stack
```

The command starts PostgreSQL, Redis, and MinIO with Docker Compose, applies
Alembic migrations, seeds the local admin account, launches the FastAPI control
plane on `http://127.0.0.1:8001`, refreshes the example projects through public
ForgeML APIs, and launches the Vite console on `http://127.0.0.1:5173`.

Use these credentials:

```text
Email: admin@forgeml.dev
Password: forgeml-local-admin
```

The managed process writes `.forgeml/demo/demo-stack-summary.json` and keeps the
API and frontend running until the terminal receives `Ctrl+C`.

## Preflight Plan

Print the exact command plan without starting services:

```bash
make demo-stack-plan
```

Use this when a reviewer needs to inspect ports, artifact paths, or the API proxy
target before starting the stack.

## Seeded Data Refresh

When the backend is already running, refresh the example projects without
restarting the stack:

```bash
make demo-refresh
```

The refresh command writes `.forgeml/demo/demo-data-refresh.json` and
idempotently seeds:

- Movie Recommendation
- Semantic Search
- Fraud Detection

Each seeded project includes project metadata, dataset versions, feature-store
metadata, experiments, succeeded training runs, registered models, approved model
versions, deployments, inference endpoints, monitoring snapshots, alert
evaluation, drift reports, and retraining policy evaluation.

## Screenshot Capture

Generate reviewer-ready screenshots against deterministic browser API mocks:

```bash
make demo-screenshots
```

Playwright writes the screenshots under `frontend/test-results`. The captured
screens cover Dashboard, Projects, Example Projects, Training Runs, Models,
Deployments, Inference, and Monitoring.

## Manual Review Path

After `make demo-stack` finishes the seed refresh, open
`http://127.0.0.1:5173` and validate:

1. Sign in with the local admin account.
2. Open Projects and confirm the three example projects are present.
3. Open Datasets and confirm dataset versions are finalized and validated.
4. Open Training Runs and confirm seeded runs are succeeded with execution logs.
5. Open Models and confirm model versions are approved.
6. Open Deployments and confirm healthy revisions are receiving traffic.
7. Open Inference and run an endpoint probe.
8. Open Monitoring and confirm inference, drift, training, and retraining signals.
9. Open Alerts and confirm evaluated alert events are visible.
10. Open Retraining and confirm policy evaluations point back to the triggering drift or alert signal.

## Troubleshooting

If Docker is not running, start Docker Desktop and rerun `make demo-stack`.

If port `5173` is already in use, stop the existing Vite process or run:

```bash
PYTHONPATH=. .venv/bin/python scripts/dev/demo_stack.py --frontend-url http://127.0.0.1:5174
```

If port `8001` is already in use, stop the existing API process or run:

```bash
PYTHONPATH=. .venv/bin/python scripts/dev/demo_stack.py --api-url http://127.0.0.1:8002
```

If dependencies are missing, install them once:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
npm --prefix frontend install
```
