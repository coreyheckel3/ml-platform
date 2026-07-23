# Production Readiness Runbook

This runbook defines the release gate for ForgeML changes promoted beyond local development.

## Release Gate

Run these checks before a staging or production deployment:

```bash
python scripts/ci/production_readiness.py
python -m pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend run test -- --run
npm --prefix frontend run build
docker compose -f infra/compose/docker-compose.yml --profile full config
```

For staging, also run the k6 smoke load profile:

```bash
k6 run -e FORGEML_BASE_URL=https://staging-api.forgeml.example load/k6/api_smoke.js
```

## Required Evidence

- CI run URL for backend, frontend, Docker, and production-readiness checks
- Alembic head revision included in the deployment artifact
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
