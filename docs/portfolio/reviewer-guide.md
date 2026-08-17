# ForgeML Reviewer Guide

ForgeML is an end-to-end ML platform control plane, not a single-model demo. It
models the lifecycle an internal ML platform would support for many teams:
dataset registration, feature metadata, experiments, training execution, model
registry governance, deployment revisions, online inference, monitoring, drift
detection, alerting, retraining, and release evidence.

## How To Evaluate The Project

Start with the architecture walkthrough:

```bash
open docs/architecture-walkthrough.md
```

Then run the core validation gates:

```bash
make test
make production-readiness
npm --prefix frontend run e2e
```

For a live product walkthrough, run:

```bash
make demo-stack
```

Use `admin@forgeml.dev` and `forgeml-local-admin` to sign in locally.

## What To Look For

### Platform Scope

ForgeML spans the full platform lifecycle:

- Dataset upload and immutable version metadata
- Schema validation and dataset profiling records
- Feature-set, feature-definition, and pipeline lineage metadata
- Experiment groups, training runs, metrics, params, and artifacts
- Model promotion, approval, signatures, lineage, and registry workflows
- Deployment revisions, canary traffic, health probes, rollback, and serving
  runtime boundaries
- Inference endpoints, request logs, monitoring snapshots, latency percentiles,
  errors, drift signals, alerts, and retraining activity
- Release governance through checked contracts, release manifests, verification,
  CI evidence, and production-readiness gates

### Architecture Signals

The backend is a modular monolith with explicit service extraction paths. Each
major capability keeps API, application, domain, infrastructure, repository
interfaces, repository implementations, and tests separate.

External systems sit behind adapter boundaries:

- Object storage uses artifact manifest contracts and checksums.
- MLflow integration uses a tracking gateway.
- Airflow orchestration uses a workflow gateway with local fallback.
- Serving uses a runtime gateway for endpoint revision resolution, canary
  simulation, rollback, and probes.

### Production Engineering Signals

The project favors verifiable engineering behavior over static claims:

- CI runs backend tests, frontend tests, Playwright E2E, Docker builds,
  production-readiness checks, and contract gates.
- Release manifests include hashes for contracts, runbooks, Dockerfiles, and
  required quality gates.
- Production-readiness validates security, observability, deployment runtime,
  monitoring, demo readiness, CI runtime, and portfolio readiness.
- GitHub Actions publishes release evidence on main-branch pushes.
- Live release evidence retrieval can fetch the latest main-branch manifest
  artifact from GitHub Actions and compare it with checked-in contracts.

## Suggested Walkthrough Narrative

1. Frame ForgeML as a platform control plane for multiple ML projects.
2. Open the dashboard and explain that the frontend is a real operations console.
3. Select a project and walk through datasets, features, experiments, and
   training runs.
4. Promote a succeeded training run to a registered model version.
5. Approve, deploy, probe inference, and show monitoring snapshots.
6. Explain how drift and alerts can hand off to retraining policies.
7. Close with the release-governance loop: contracts, release manifest,
   verification, Docker, CI evidence, the Release Evidence page, and the
   Operational Audit timeline.

## Reviewer Commands

```bash
PYTHONPATH=. .venv/bin/python scripts/ci/check_portfolio_readiness_contract.py
PYTHONPATH=. .venv/bin/python scripts/ci/check_release_evidence_ux_contract.py
PYTHONPATH=. .venv/bin/python scripts/ci/check_release_evidence_retrieval_contract.py
PYTHONPATH=. .venv/bin/python scripts/ci/check_release_evidence_drilldown_api_contract.py
PYTHONPATH=. .venv/bin/python scripts/ci/check_operational_audit_ux_contract.py
PYTHONPATH=. .venv/bin/python scripts/ci/production_readiness.py
PYTHONPATH=. .venv/bin/python scripts/ops/build_release_manifest.py --output /tmp/forgeml-release-manifest.json
PYTHONPATH=. .venv/bin/python scripts/ops/verify_release_manifest.py --manifest /tmp/forgeml-release-manifest.json
PYTHONPATH=backend/src:. .venv/bin/python scripts/ops/retrieve_release_evidence.py --repo coreyheckel3/ml-platform --branch main --workflow ci.yml --artifact-name forgeml-release-manifest
```
