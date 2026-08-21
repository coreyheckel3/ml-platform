# Production Readiness Runbook

This runbook defines the release gate for ForgeML changes promoted beyond local development.

## Release Gate

Run these checks before a staging or production deployment:

```bash
python scripts/ci/production_readiness.py
python scripts/ci/check_alembic_migration_contract.py
python scripts/ci/check_sqlalchemy_schema_contract.py
python scripts/ci/generate_openapi_contract.py --check
python scripts/ci/check_problem_details_contract.py
python scripts/ci/check_api_authorization_contract.py
python scripts/ci/check_permission_catalog.py
python scripts/ci/check_runtime_config_policy.py
python scripts/ci/check_request_logging_contract.py
python scripts/ci/check_external_training_package_contract.py
python scripts/ci/check_release_smoke_contract.py
python scripts/ci/check_release_manifest_contract.py
python scripts/ci/check_release_evidence_workflow.py
python scripts/ci/check_release_evidence_ux_contract.py
python scripts/ci/check_release_evidence_retrieval_contract.py
python scripts/ci/check_release_evidence_drilldown_api_contract.py
python scripts/ci/check_release_evidence_scheduled_refresh_contract.py
python scripts/ci/check_release_evidence_notifications_contract.py
python scripts/ci/check_operational_audit_ux_contract.py
python scripts/ci/check_release_manifest_verifier_contract.py
python scripts/ci/check_demo_readiness_contract.py
python scripts/ci/check_ci_runtime_contract.py
python scripts/ci/check_portfolio_readiness_contract.py
python -m pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend audit --omit=dev
npm --prefix frontend run test -- --run
npm --prefix frontend run e2e
npm --prefix frontend run build
python scripts/ci/check_frontend_bundle_budget.py
docker compose -f infra/compose/docker-compose.yml --profile full config
```

Against a seeded local or staging API, run the non-mutating release smoke:

```bash
PYTHONPATH=. python scripts/ops/release_smoke.py --base-url http://127.0.0.1:8001
```

Build the release provenance manifest after the smoke result and CI run are available:

```bash
PYTHONPATH=. python scripts/ops/build_release_manifest.py --output /tmp/forgeml-release-manifest.json --ci-run-url "$CI_RUN_URL" --release-smoke-result "$RELEASE_SMOKE_RESULT_JSON"
```

Verify the manifest before promotion:

```bash
PYTHONPATH=. python scripts/ops/verify_release_manifest.py --manifest /tmp/forgeml-release-manifest.json --require-ci-evidence
```

Retrieve the latest successful main-branch release manifest artifact from GitHub Actions and compare it with the release contract:

```bash
PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py --repo coreyheckel3/ml-platform --branch main --workflow ci.yml --artifact-name forgeml-release-manifest
```

Run the scheduled refresh command from cron or an operator shell to retrieve new release evidence only when the platform marks the persisted last-success report stale:

```bash
PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --base-url http://127.0.0.1:8001 --once --stale-after-seconds 86400
```

Generate a cron entry for the same automation:

```bash
PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --print-cron --base-url http://127.0.0.1:8001 --stale-after-seconds 86400
```

Configure release evidence failure notifications before enabling a staging or
production scheduler:

```bash
export FORGEML_RELEASE_EVIDENCE_NOTIFICATIONS_ENABLED=true
export FORGEML_RELEASE_EVIDENCE_NOTIFICATION_CHANNEL=webhook
export FORGEML_RELEASE_EVIDENCE_NOTIFICATION_WEBHOOK_URL=https://hooks.example.com/forgeml-release-evidence
export FORGEML_RELEASE_EVIDENCE_NOTIFICATION_ESCALATION_WINDOW_SECONDS=1800
```

Failed release evidence writes one delivery audit record with action
`release_evidence.notification_delivered`,
`release_evidence.notification_failed`, or
`release_evidence.notification_skipped`. If delivery fails, run the
notification policy escalation command from the Release Evidence page and
review the newest `release_evidence.retrieve_failed` report before promotion.

For staging, also run the k6 smoke load profile:

```bash
k6 run -e FORGEML_BASE_URL=https://staging-api.forgeml.example load/k6/api_smoke.js
```

## Required Evidence

- CI run URL for backend, frontend, Docker, and production-readiness checks
- Alembic migration contract result proving the release has one base, one head, and reversible migrations
- SQLAlchemy schema contract result proving registered metadata includes required tables and indexed foreign keys
- OpenAPI contract check result proving the checked-in schema matches the FastAPI app
- Problem Details contract result proving API errors include trace IDs and sanitized validation details
- API authorization contract result proving only allowlisted routes are public
- Permission catalog check result proving enforced permissions and role presets are cataloged
- Runtime config policy result proving production-like environments reject unsafe defaults
- Request logging contract result proving HTTP access logs include trace IDs and redaction policy
- External training package contract result proving reviewed ML repositories run through allowlisted profiles, worker execution, metric import, artifact checksums, and UI launch controls
- Release smoke contract result proving live operator checks cover health, auth, project context, datasets, features, experiments, training, training logs, registry, deployment, inference, monitoring, alerting, drift, and retraining surfaces
- Release smoke JSON result from the target environment showing all required stages passed
- Release manifest JSON result containing Git source provenance, SHA-256 file hashes, Docker image targets, required contracts, CI evidence, and smoke evidence
- Release manifest verification result proving artifact hashes, Dockerfile hashes, quality gates, and CI evidence linkage are valid
- CI release manifest artifact named `forgeml-release-manifest` attached to the successful main-branch workflow run
- Release evidence UX contract result proving `/release-evidence` exposes manifest artifacts, reviewer commands, quality gates, and screenshot evidence
- Release evidence retrieval contract result proving GitHub Actions artifact lookup, manifest archive extraction, main-branch comparison, and CI URL validation are checked
- Release evidence drilldown API contract result proving admin retrieval reports, RBAC, audit logging, persistence, and UI drilldown are checked
- Release evidence scheduled refresh contract result proving stale status, last-success summary, operator automation, and UI indicators are checked
- Release evidence notifications contract result proving failed evidence alerts, webhook delivery, delivery audit records, and escalation docs are checked
- Operational audit UX contract result proving `/operational-audit` links live audit events, release evidence annotations, screenshots, and route-level follow-up
- Demo readiness contract result proving local stack startup, seeded data refresh, screenshot capture, and architecture walkthrough assets are checked
- CI runtime contract result proving GitHub Actions runtime pins avoid retired action majors
- Portfolio readiness contract result proving reviewer guide, resume bullets, evidence map, architecture diagrams, and screenshot catalog assets are checked
- `/health/ready` result from the target environment showing database and Redis probes passing
- Frontend production `npm audit --omit=dev` result with zero high or critical findings
- Frontend Playwright E2E result proving login, project context, dataset validation, training, model approval, deployment, inference, monitoring, and alert evaluation workflows
- Frontend bundle-budget result showing all JavaScript chunks below 500 KB
- Alembic migration contract, SQLAlchemy schema contract, and head revision included in the deployment artifact
- Terraform plan reviewed for the target environment
- k6 summary showing p95 latency below 500 ms for smoke traffic
- Grafana dashboard screenshot or link showing API request rate, p95 latency, error rate, and rate-limited requests
- Backup created before any migration that changes persisted schema

## Rollback

1. Stop promotion traffic at the deployment layer.
2. Roll back to the previous healthy deployment revision in ForgeML.
3. If schema rollback is required, restore the latest verified database backup.
4. Record the incident in the deployment event timeline and link the CI run.

## Owners

- Platform Engineering owns deployment mechanics.
- ML Runtime owns model-serving health.
- Data Platform owns dataset and feature-store integrity.
- Security owns credential exposure and access-control incidents.
