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

## External Movie Recommender Training

ForgeML can execute the local `conversational-movie-recommender` package through
the Training Runs page and background worker. The default profile points at
`$HOME/Documents/GitHub/conversational-movie-recommender`; override it with
`FORGEML_EXTERNAL_TRAINING_MOVIE_RECOMMENDER_REPO_ROOT` when the repository
lives somewhere else.

To run the adapter live:

1. Start the demo stack.
2. Open Training Runs.
3. Click `Use profile` on `Conversational Movie Recommender`.
4. Start the training run.
5. Run one worker polling cycle:

```bash
PYTHONPATH=backend/src:. .venv/bin/python scripts/workers/run_training_worker.py --organization-id <organization-id> --worker-id external-package-worker --max-runs 1
```

The worker invokes `movie-rec-build --write-metrics`, imports
`evaluation.json`, records model artifacts with checksums, and appends execution
logs to the training run.

## External Movie Recommender Serving

ForgeML can route inference traffic to the local movie recommender service after
an external movie recommender run is promoted and deployed.

Start the recommender service in the external repository:

```bash
cd ~/Documents/GitHub/conversational-movie-recommender
MOVIE_REC_AGENT=langgraph MOVIE_REC_LLM_PROVIDER=ollama MOVIE_REC_LLM_MODEL=llama3.2:3b PYTHONPATH=src .venv/bin/python -m movie_recommender.api --model-dir models/sample --port 8000
```

Then in ForgeML:

1. Open Models and promote the succeeded `movie-rec-svd` or
   `movie-rec-two-tower` run. The UI defaults the model format to `joblib` and
   stamps `conversational-movie-recommender` into the model signature.
2. Request and approve the model version.
3. Open Deployments, click `Movie adapter` in the revision form, and create the
   revision.
4. Probe the revision health.
5. Open Inference, click `Movie request`, and probe the endpoint.

The prediction log stores normalized recommendations, the recommender answer,
parsed query, adapter trace, model version, model format, and model artifact URI.

## Screenshot Capture

Generate reviewer-ready screenshots against deterministic browser API mocks:

```bash
make demo-screenshots
```

Playwright writes the screenshots under `frontend/test-results`. The captured
screens cover Dashboard, Projects, Example Projects, Training Runs, Models,
Deployments, Inference, and Monitoring.

For reviewer packaging, use the portfolio screenshot catalog at
`docs/portfolio/screenshot-catalog.md`.

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
