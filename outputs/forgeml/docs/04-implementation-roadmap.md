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

## Active Unified Sprint Track

The current delivery plan combines completed release-governance hardening with
the remaining product/runtime platform roadmap.

| Sprint | Theme | Delivery Intent |
| --- | --- | --- |
| 46 | Browser E2E Platform Flows | Prove the core ML lifecycle through the web UI with deterministic Playwright coverage. |
| 47 | Release Candidate Smoke Governance | Prove live API release readiness without mutating target environments. |
| 48 | Release Manifest Provenance | Generate auditable release manifests with source, contract, image, and smoke evidence. |
| 49 | CI Release Evidence Publication | Publish release manifests from successful main-branch CI runs. |
| 50 | Release Manifest Verification | Verify release manifests before artifact publication and promotion. |
| 51 | Background Worker / Job Queue Hardening | Completed: hardened queued jobs with retries, leases, dead-letter handling, heartbeats, and metrics. |
| 52 | Artifact Storage Abstraction | Completed: dataset and model versions now persist S3-compatible artifact manifest URIs, manifest hashes, checksum metadata, lineage, storage contracts, and CI gates. |
| 53 | MLflow Integration Layer | Completed: training runs now sync metrics, parameters, lineage tags, artifact references, and sync status reports through a configurable MLflow adapter boundary. |
| 54 | Airflow Orchestration Adapter | Completed: training launches can route through a configurable Airflow REST adapter with DAG run contracts, cancellation, status polling, local fallback, and CI gates. |
| 55 | Deployment Runtime Hardening | Completed: serving adapter boundary, revision resolution, canary simulation, rollback draining, runtime health probes, and CI contract gates. |
| 56 | Monitoring Dashboards v2 | Completed: operations overview API, latency percentiles, inference errors, drift trends, training failures, retraining activity, and dashboard contract gates. |
| 57 | Security and Multi-Tenant Hardening | Completed: organization isolation tests, RBAC matrix tests, rate-limit partitioning tests, audit metadata redaction, secrets/config docs, and security hardening contract gates. |
| 58 | Developer Experience / Demo Readiness | Completed: one-command demo stack, seeded data refresh, screenshot capture, architecture walkthrough, runbook, and demo readiness contract gates. |
| 59 | CI Runtime Maintenance | Completed: refreshed GitHub Actions runtime pins, added CI runtime contracts, and removed retired action major refs from release evidence. |
| 60 | Portfolio Polish / Reviewer Assets | Completed: reviewer guide, resume bullets, evidence map, architecture diagrams, screenshot catalog, portfolio readiness contract, CI wiring, and release evidence. |
| 61 | Release Artifact Download / Evidence UX | Completed: Release Evidence frontend module, route, navigation, reviewer commands, screenshot coverage, release evidence UX contract, CI wiring, production-readiness, and release manifest evidence. |
| 62 | Operational Audit UX v2 | Completed: Operational Audit frontend module, `/operational-audit` route, audit timeline adapter, release evidence annotations, admin audit API integration, screenshots, UX contract, CI wiring, production-readiness, and release manifest evidence. |
| 63 | Live Release Evidence Retrieval | Completed: GitHub Actions artifact gateway, local manifest fallback, retrieval report CLI, manifest comparison checks, Release Evidence UI status, CI contract, production-readiness, and release manifest evidence. |
| 64 | Release Evidence Drilldown API | Next: expose release evidence retrieval through an authenticated admin API with persisted retrieval reports, audit events, and frontend drilldowns. |
