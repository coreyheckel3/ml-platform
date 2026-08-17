# ForgeML Evidence Map

This map connects portfolio claims to implementation evidence. It is meant for
reviewers who want to verify that ForgeML is more than a UI mock or a single
training script.

| Claim | Evidence |
| --- | --- |
| Modular monolith with clean boundaries | `backend/src/forgeml/modules`, `outputs/forgeml/docs/01-system-architecture.md`, `docs/architecture-walkthrough.md` |
| Dataset versioning and validation | `backend/src/forgeml/modules/datasets`, `backend/tests/api/test_dataset_api.py`, `contracts/database/sqlalchemy-schema.v1.json` |
| Feature-store metadata and lineage | `backend/src/forgeml/modules/feature_store`, `frontend/src/modules/feature_store`, `backend/tests/api/test_feature_store_api.py` |
| Experiment and training lifecycle | `backend/src/forgeml/modules/experiments`, `backend/src/forgeml/modules/training`, `backend/tests/api/test_training_runs_api.py` |
| Worker-backed queued training execution | `scripts/workers/run_training_worker.py`, `backend/src/forgeml/modules/training/application/execution.py`, `backend/tests/unit/training` |
| Artifact storage abstraction | `backend/src/forgeml/platform/artifacts`, `contracts/artifacts/artifact-manifest.v1.json`, `scripts/ci/check_artifact_manifest_contract.py` |
| MLflow integration boundary | `backend/src/forgeml/platform/mlflow/tracking.py`, `contracts/mlflow/mlflow-tracking.v1.json`, `backend/tests/unit/ops/test_mlflow_tracking_contract.py` |
| Airflow orchestration boundary | `backend/src/forgeml/modules/training/infrastructure/orchestrator.py`, `contracts/orchestration/airflow-training.v1.json`, `pipelines/airflow/dags` |
| Model registry approval workflow | `backend/src/forgeml/modules/model_registry`, `frontend/src/modules/models`, `backend/tests/api/test_model_registry_api.py` |
| Deployment runtime hardening | `backend/src/forgeml/modules/deployments`, `backend/src/forgeml/platform/serving/runtime.py`, `contracts/runtime/deployment-serving.v1.json` |
| Inference request logging and monitoring | `backend/src/forgeml/modules/inference`, `backend/src/forgeml/modules/monitoring`, `contracts/observability/request-log-event.v1.json` |
| Drift detection and retraining handoff | `backend/src/forgeml/modules/drift_detection`, `backend/src/forgeml/modules/retraining`, `frontend/src/modules/retraining` |
| Tenant-aware security and RBAC | `contracts/security`, `backend/tests/integration/security/test_tenant_isolation.py`, `backend/tests/unit/security/test_rbac_matrix.py` |
| Production readiness and release governance | `scripts/ci/production_readiness.py`, `scripts/ops/build_release_manifest.py`, `scripts/ops/verify_release_manifest.py`, `contracts/ops` |
| Release evidence UX | `frontend/src/modules/release_evidence`, `contracts/ops/release-evidence-ux.v1.json`, `frontend/tests/e2e/demo-screenshots.spec.ts` |
| Live release evidence retrieval | `backend/src/forgeml/platform/release_evidence`, `scripts/ops/retrieve_release_evidence.py`, `contracts/ops/release-evidence-retrieval.v1.json` |
| Release evidence drilldown API | `backend/src/forgeml/modules/administration`, `frontend/src/modules/release_evidence/api`, `contracts/ops/release-evidence-drilldown-api.v1.json` |
| Operational audit UX | `frontend/src/modules/operational_audit`, `contracts/ops/operational-audit-ux.v1.json`, `frontend/tests/e2e/demo-screenshots.spec.ts` |
| Browser lifecycle coverage | `frontend/tests/e2e/platform-lifecycle.spec.ts`, `frontend/tests/e2e/demo-screenshots.spec.ts` |
| Reviewer-ready demo path | `docs/runbooks/demo-readiness.md`, `scripts/dev/demo_stack.py`, `scripts/dev/refresh_demo_data.py`, `contracts/ops/demo-readiness.v1.json` |
| Portfolio assets under contract | `docs/portfolio`, `contracts/ops/portfolio-readiness.v1.json`, `scripts/ci/check_portfolio_readiness_contract.py` |

## CI Evidence

The main CI workflow validates:

- Backend lint and tests
- Example training smoke execution
- Frontend lint, unit tests, Playwright E2E, production build, and bundle budget
- Docker image builds
- Production readiness
- API, database, security, observability, artifact, orchestration, deployment,
  release, release evidence UX, live release evidence retrieval, release
  evidence drilldown API, operational audit UX, demo, CI runtime, and portfolio
  readiness contracts
- Release manifest generation, verification, and artifact publication on
  main-branch pushes
