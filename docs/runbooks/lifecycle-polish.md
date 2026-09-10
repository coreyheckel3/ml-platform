# Lifecycle Polish Runbook

Sprint 74 adds a first-class Lifecycle surface for project reviewers and ML
operators. The page turns cross-module evidence into one readiness map so a
project can be inspected from dataset registration through retraining without
jumping blindly across product pages.

## Surface

- Frontend route: `/lifecycle`
- Backend route: `GET /api/v1/projects/{project_id}/lifecycle/summary`
- Required permission: `lifecycle:read`
- Contract: `contracts/ops/lifecycle-polish.v1.json`
- Screenshot: `13-lifecycle.png`

The summary is intentionally read-only. It derives readiness from existing
project-scoped records across datasets, feature store, experiments, training,
model registry, deployment, inference, monitoring, drift detection, and
retraining.

## Review Path

1. Start the demo stack with `make demo-stack`.
2. Sign in as `admin@forgeml.dev`.
3. Select a seeded project such as Fraud Detection.
4. Open Lifecycle from the main navigation.
5. Confirm End-to-End Lifecycle Readiness, Stage Readiness, Recommended
   Actions, Project Signals, and Dependency Map are populated.
6. Use the Open links in Stage Readiness to drill into the contributing product
   routes.

## Quality Gate

Run the Sprint 74 contract locally:

```bash
make lifecycle-polish
```

Regenerate the checked contract after an intentional lifecycle surface change:

```bash
PYTHONPATH=. python scripts/ci/check_lifecycle_polish_contract.py --write
```

The contract verifies backend clean-architecture layers, RBAC, API routing,
frontend navigation, deterministic Playwright coverage, release evidence, docs,
and the screenshot catalog.
