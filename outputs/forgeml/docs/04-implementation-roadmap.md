# Implementation Roadmap

The roadmap favors foundations first, then progressively larger vertical slices. Each phase should leave the platform in a working state and should include tests, documentation updates, and operational checks.

## Phase 0: Architecture and Foundation

Outcome: A production-shaped repository with documentation, standards, build tooling, local infrastructure, CI, and initial module skeletons.

Scope:

- Architecture documentation
- Repository conventions
- Backend project setup
- Frontend project setup
- Docker Compose baseline
- PostgreSQL, Redis, MLflow, Airflow local services
- Alembic baseline migration
- CI workflow skeleton
- Linting and formatting
- Test harnesses

## Phase 1: Identity, Projects, and Platform Shell

Outcome: Authenticated users can log in, view the SaaS shell, create projects, and navigate project-scoped pages.

Scope:

- JWT authentication
- Password hashing
- Refresh tokens
- RBAC primitives
- Project CRUD
- Audit logging
- React shell, navigation, route guards
- TanStack Query API client
- API, unit, integration, and Playwright smoke tests

## Phase 2: Dataset Registry and Versioning

Outcome: Users can create datasets, upload versions through signed URLs, validate schemas, and view dataset profiles.

Scope:

- Dataset metadata
- Dataset versioning
- Object storage adapter
- Schema inference and validation
- Validation workflow submission
- Dataset profile summaries
- Dataset UI pages
- API and integration tests for upload/finalization flows

## Phase 3: Feature Store Metadata and Materialization

Outcome: Users can define feature sets, register feature pipelines, and trigger materialization workflows.

Scope:

- Feature set CRUD
- Feature definitions
- Pipeline registration
- Airflow materialization adapter
- Feature lineage
- Materialization status tracking
- Feature store UI
- Tests for domain policies and workflow dispatch

## Phase 4: Experiments and Training

Outcome: Users can create experiments, launch training runs, track runs, compare metrics, and inspect artifacts.

Scope:

- Experiment abstraction
- MLflow tracking adapter
- Training job lifecycle
- Airflow training DAG integration
- PyTorch, XGBoost, LightGBM, and scikit-learn runner interfaces
- Evaluation reports
- Experiment comparison UI
- Training run UI
- Contract tests for MLflow adapter

## Phase 5: Model Registry and Approval

Outcome: Users can register model versions from training runs, inspect lineage, request approval, and approve or reject versions.

Scope:

- Registered models
- Model versions
- Validated promotion from training execution manifests
- Model signatures
- Metrics snapshots
- Approval workflow
- Lineage graph
- Registry UI
- Authorization tests for approval roles

## Phase 6: Deployment and Inference

Outcome: Approved model versions can be deployed behind inference endpoints with canary rollout, health checks, and rollback.

Scope:

- Deployment targets
- Deployment revisions
- Inference runtime contract
- Canary rollout records
- Rollback workflow
- Health checks
- Prediction request validation
- Deployment UI
- Latency and error metrics

## Phase 7: Monitoring, Alerts, and Drift Detection

Outcome: Users can monitor inference behavior, configure alert rules, run drift checks, and inspect reports.

Scope:

- Prometheus metric ingestion and dashboard metadata
- Alert rules and events
- Notification channels
- Drift profiles
- Drift report workflow
- Monitoring dashboard
- Alert center UI
- Tests for drift policies and alert state transitions

## Phase 8: Automated Retraining

Outcome: Drift or scheduled triggers can launch retraining workflows and connect results back to registry and deployment workflows.

Scope:

- Retraining policies
- Trigger evaluation
- Retraining run creation
- Approval gate before training launch
- Optional auto-deploy policy with strict guardrails
- Retraining UI and audit trail

## Phase 9: Example Projects

Outcome: The platform demonstrates three realistic ML workflows without hardcoded platform assumptions.

Example projects:

- Movie Recommendation
- Semantic Search
- Fraud Detection

Each example should include:

- Dataset manifest and local fixture data
- Feature definitions and pipeline registration metadata
- Training configuration and offline evaluation report
- Model registration and approval flow
- Deployment, inference, monitoring, drift, alert, and retraining configuration
- SDK-backed local bootstrap command
- Dashboard catalog entry and documentation

## Phase 10: Production Hardening

Outcome: ForgeML is credible as an internal platform prototype.

Scope:

- Load tests
- Security review
- Threat model review
- Backup and restore verification
- Rate limiting
- Secret rotation documentation
- Observability dashboards
- Runbooks
- Terraform staging environment
- End-to-end CI/CD

## Release Milestones

| Milestone | Name | User-Visible Capability |
| --- | --- | --- |
| M0 | Foundation | Local platform boots with health checks and CI. |
| M1 | Project Hub | Users authenticate and manage projects. |
| M2 | Dataset Control | Dataset upload, versioning, validation, profiling. |
| M3 | Training Loop | Experiments, training runs, metrics, artifacts. |
| M4 | Registry Gate | Model registration, lineage, approval workflow. |
| M5 | Production Loop | Deployment, inference, monitoring, rollback. |
| M6 | Adaptive ML | Drift detection and automated retraining. |
