# ForgeML Screenshot Catalog

Deterministic reviewer screenshots are captured by:

```bash
make demo-screenshots
```

The Playwright flow uses stateful API mocks and writes screenshots under
`frontend/test-results`. The catalog below maps each screenshot to the platform
capability it demonstrates.

| Screenshot | Route | Reviewer Signal |
| --- | --- | --- |
| `01-dashboard.png` | `/` | Platform overview, health posture, active projects, and operational summaries. |
| `02-projects.png` | `/projects` | Multi-project control plane and project context selection. |
| `03-examples.png` | `/examples` | Three independent ML workloads without hardcoded platform assumptions. |
| `04-training-runs.png` | `/training-runs` | Training-run lifecycle, metrics, parameters, status changes, and execution logs. |
| `05-models.png` | `/models` | Registry promotion, model version lineage, and approval workflow. |
| `06-deployments.png` | `/deployments` | Deployment revisions, health checks, canary promotion, and rollback readiness. |
| `07-inference.png` | `/inference` | Endpoint creation, prediction probes, request logs, and metric snapshots. |
| `08-monitoring.png` | `/monitoring` | Latency percentiles, error breakdowns, drift trends, training failures, and retraining activity. |
| `09-release-evidence.png` | `/release-evidence` | Release manifest artifacts, quality gates, live retrieval, API drilldown, reviewer commands, CI provenance, and screenshot evidence. |
| `10-operational-audit.png` | `/operational-audit` | Unified audit timeline for release evidence, deployment, retraining, security, and registry events. |

## Capture Contract

The screenshot flow must:

- Sign in with the seeded admin account.
- Select a project before mutating project-scoped state.
- Prepare a realistic training, registry, deployment, inference, and monitoring
  path before screenshots are captured.
- Navigate to each screenshot route explicitly.
- Assert the final URL and page heading before each screenshot.

The flow is validated in CI as part of `npm --prefix frontend run e2e` and is
referenced by the portfolio readiness, release evidence UX, and operational
audit UX contracts.
