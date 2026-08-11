# Observability Contracts

Observability contracts capture platform telemetry schemas that should stay stable
across API, infrastructure, and dashboard changes.

## Request Log Event

`request-log-event.v1.json` records the required structured HTTP request log fields,
HTTP subfields, and redaction markers.

## Monitoring Dashboard

`monitoring-dashboard.v1.json` records the project operations overview API,
dashboard signal families, frontend sections, and quality gates for Monitoring
Dashboards v2.

Regenerate after an intentional request logging schema change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_request_logging_contract.py --write
```

Regenerate after an intentional monitoring dashboard contract change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_monitoring_dashboard_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_request_logging_contract.py
PYTHONPATH=backend/src:. python scripts/ci/check_monitoring_dashboard_contract.py
```
