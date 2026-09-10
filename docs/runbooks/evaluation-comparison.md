# Evaluation Comparison Runbook

Sprint 75 adds a first-class Evaluation surface for experiment reviewers and ML
engineering leads. The page turns existing experiment, training, model registry,
approval, artifact, and lineage records into one reviewer-ready comparison.

## Surface

- Frontend route: `/evaluation`
- Backend route: `GET /api/v1/projects/{project_id}/evaluation/comparison`
- Required permission: `evaluation:read`
- Contract: `contracts/ops/evaluation-comparison.v1.json`
- Screenshot: `14-evaluation.png`

The comparison is intentionally read-only. It derives rankings and evidence from
existing project-scoped records and does not create model versions, approvals, or
training runs.

## Review Path

1. Start the demo stack with `make demo-stack`.
2. Sign in as `admin@forgeml.dev`.
3. Select a seeded project such as Fraud Detection.
4. Open Evaluation from the main navigation.
5. Confirm Run Leaderboard ranks candidates by the selected primary metric.
6. Confirm Metric Slices expose best, baseline, and delta values.
7. Confirm Model Card Evidence shows metrics, signatures, artifact manifests,
   lineage, and risk flags.
8. Confirm Approval Checklist calls out metrics, reports, lineage, artifact
   manifests, model signatures, and reviewer approval.
9. Confirm Evaluation Narrative summarizes the recommended candidate for review.

## Quality Gate

Run the Sprint 75 contract locally:

```bash
make evaluation-comparison
```

Regenerate the checked contract after an intentional evaluation surface change:

```bash
PYTHONPATH=. python scripts/ci/check_evaluation_comparison_contract.py --write
```

The contract verifies backend clean-architecture layers, RBAC, API routing,
frontend navigation, deterministic Playwright coverage, release evidence, docs,
and the screenshot catalog.
