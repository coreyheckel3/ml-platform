# Sprint Breakdown

Each sprint should produce working software. Sprints are written as two-week increments, but scope can be resized while preserving the order.

## Sprint 0: Architecture, Standards, and Tooling

Goal: Establish the project foundation before product implementation.

Deliverables:

- Architecture documentation accepted
- Repository initialized
- Backend and frontend toolchains configured
- Formatting and linting configured
- Pytest and Playwright harnesses configured
- GitHub Actions baseline
- Docker Compose baseline for local infrastructure

Acceptance criteria:

- `make test` or equivalent runs backend unit tests.
- Frontend unit test command runs.
- CI runs lint, formatting checks, and tests.
- Local infrastructure health checks pass.

## Sprint 1: Auth, RBAC, and Project Shell

Goal: Users can authenticate and manage projects inside the web app.

Deliverables:

- JWT login and refresh
- Password hashing
- RBAC permission model
- Project CRUD
- Audit logging for auth and project actions
- React app shell with navigation
- Dashboard overview backed by real API health and project status data

Acceptance criteria:

- Unauthorized users cannot access project APIs.
- Users only see projects they are allowed to access.
- API tests cover login, refresh, and project CRUD.
- Playwright smoke test logs in and opens the Projects page.

## Sprint 2: Dataset Registry

Goal: Users can register datasets and upload immutable versions.

Deliverables:

- Dataset CRUD
- Dataset version lifecycle
- Signed upload URL abstraction
- Object storage adapter
- Dataset UI
- Dataset version details page

Acceptance criteria:

- Dataset versions are immutable after finalization.
- Duplicate content hashes are detected.
- Upload finalization is idempotent.
- Integration tests run against Postgres and local object storage.

## Sprint 3: Schema Validation and Profiling

Goal: Dataset versions can be validated and profiled through asynchronous workflows.

Deliverables:

- Schema inference
- Schema validation rules
- Dataset validation runs
- Profile report storage
- Airflow validation DAG adapter
- Validation and profile UI

Acceptance criteria:

- Invalid schemas produce actionable validation errors.
- Validation status updates are visible in the UI.
- Failed validation is auditable and retryable.
- Unit tests cover schema compatibility policies.

## Sprint 4: Feature Store Metadata

Goal: Users can define feature sets and register feature pipelines.

Deliverables:

- Feature set CRUD
- Feature definitions
- Pipeline registration
- Feature lineage model
- Feature Store UI

Acceptance criteria:

- Feature names are unique within a feature set.
- Feature types are validated.
- Feature lineage can be queried.
- API tests cover feature set and feature definition lifecycle.

## Sprint 5: Feature Materialization

Goal: Users can trigger feature materialization workflows and inspect outputs.

Deliverables:

- Materialization records
- Airflow materialization workflow
- Offline feature URI tracking
- Materialization status UI
- Failure handling and retry

Acceptance criteria:

- Materialization requests are idempotent.
- Failed workflows are visible with error summaries.
- Materialized versions are immutable.
- Integration tests cover workflow dispatch and completion callback.

## Sprint 6: Experiments and Training

Goal: Users can launch training runs and track experiment runs.

Deliverables:

- Experiments
- Training job lifecycle
- MLflow tracking adapter
- Training runner abstraction
- Evaluation report records
- Experiments and Training Runs pages

Acceptance criteria:

- Training jobs never execute inside API request handlers.
- Training jobs produce metrics and artifacts.
- Runs can be compared by metric.
- Contract tests validate MLflow adapter behavior.

## Sprint 7: Model Registry and Approval

Goal: Users can register, inspect, and approve model versions.

Deliverables:

- Registered models
- Model versions
- Model signatures
- Model lineage
- Approval requests
- Registry UI

Acceptance criteria:

- Only approved roles can approve model versions.
- Model versions are immutable.
- A model version links back to dataset, features, training run, and artifacts.
- API tests cover approval and rejection.

## Sprint 8: Deployment and Inference

Goal: Users can deploy approved models and perform online inference.

Deliverables:

- Deployment targets
- Deployment revisions
- Inference runtime contract
- Canary rollout records
- Health checks
- Rollback workflow
- Deployment UI

Acceptance criteria:

- Unapproved models cannot be deployed.
- Canary rollout can be promoted or rolled back.
- Inference responses include model and revision metadata.
- Latency, error count, and prediction count metrics are emitted.

## Sprint 9: Monitoring and Alerting

Goal: Users can monitor deployments and configure alerts.

Deliverables:

- Monitoring summary APIs
- Prometheus metric integration
- Alert rules
- Alert events
- Alert acknowledgement and resolution
- Monitoring and Alerts UI

Acceptance criteria:

- Alerts can trigger from inference error rate and latency thresholds.
- Alert state transitions are audited.
- Dashboards show training time, prediction count, inference errors, and pipeline failures.
- Tests cover alert rule evaluation.

## Sprint 10: Drift Detection and Retraining

Goal: Users can detect drift and trigger retraining workflows.

Deliverables:

- Drift profiles
- Drift report workflows
- Drift summary UI
- Retraining policies
- Manual retraining trigger
- Automated retraining trigger from drift or alert signal
- Approval gates, cooldowns, daily limits, and idempotent trigger handling

Acceptance criteria:

- Drift reports compare reference and production windows.
- Drift and alert signals can trigger retraining policies.
- Retraining runs link to the resulting training run.
- Tests cover drift thresholds and retraining policy guards.

## Sprint 11: Example Projects

Goal: Demonstrate platform flexibility with three independent project templates.

Deliverables:

- Movie Recommendation example
- Semantic Search example
- Fraud Detection example
- Example data ingestion scripts
- Example training configs
- Example evaluation reports
- SDK manifest validation
- Idempotent bootstrap through public APIs
- Example Projects dashboard page

Acceptance criteria:

- Examples use public platform APIs and SDKs only.
- No core platform module branches on example project names.
- Each example can be run locally.
- Documentation explains the full path from dataset to deployment.

Implemented scope:

- Versioned manifests and fixture datasets live under `examples/projects`.
- `ml.libraries.forgeml_sdk.examples` validates the manifest contract.
- `scripts/examples/bootstrap_examples.py` creates or reuses project, dataset, feature, experiment, training, registry, deployment, inference, drift, alert, and retraining records through API calls.
- The React app exposes `/examples` as an operational catalog of the three reference workloads.
- Unit tests cover manifest integrity, bootstrap metadata helpers, SDK HTTP behavior, and module catalog coverage.

## Sprint 12: Production Readiness

Goal: Harden ForgeML as a portfolio-grade internal platform.

Deliverables:

- Terraform staging environment
- Deployment pipeline
- Load tests
- Security tests
- Threat model
- Runbooks
- Backup and restore validation
- Observability dashboards

Acceptance criteria:

- CI blocks on lint, formatting, unit tests, integration tests, API tests, frontend tests, and Docker build.
- Staging deploy runs from GitHub Actions through OIDC.
- Runbooks cover failed training, failed deployment, high inference error rate, and database restore.
- Load test results are documented.

Implemented scope:

- FastAPI now applies secure response headers and configurable fixed-window rate limiting.
- Prometheus exposes route request, latency, and rate-limit metrics.
- Docker Compose `full` profile provisions Prometheus and Grafana with a ForgeML platform dashboard.
- Staging Terraform is variable-driven and validated by the Terraform workflow matrix.
- CI includes a production-readiness job that validates runbooks, load tests, observability assets, and source hygiene.
- k6 smoke load test covers readiness, metrics, authentication rejection, latency, and error-rate gates.
- Backup and restore scripts support Compose-managed PostgreSQL.
- Runbooks and threat model live under `docs/runbooks` and `docs/security`.

## Sprint 13: Demo Hardening and Real ML Execution

Goal: Make the reference workloads executable as deterministic local ML jobs with artifacts that mirror platform registry contracts.

Deliverables:

- Local trainer for Movie Recommendation
- Local trainer for Semantic Search
- Local trainer for Fraud Detection
- Combined training orchestrator
- Versioned model artifacts
- Evaluation artifacts
- CI smoke execution
- Unit tests for artifact contracts

Acceptance criteria:

- All three examples can be trained from one command.
- Each trainer writes a versioned `model.json` artifact and `evaluation.json` report.
- The combined manifest records every executed workload and artifact path.
- CI runs an example training smoke job without external ML services.
- Production-readiness checks validate the example training contract.

Implemented scope:

- `scripts/examples/run_local_training.py` executes all examples or a selected subset by slug.
- Fraud Detection trains a deterministic logistic scoring baseline with engineered transaction features.
- Movie Recommendation trains an aggregate ranking baseline with user and movie profiles.
- Semantic Search builds a TF-IDF cosine retrieval index over the fixture corpus.
- Unit tests verify artifact schema versions, objective metrics, and orchestrator output.
- CI linting now covers `ml` example code and runs a local example training smoke command.

## Sprint 14: Training Execution Layer

Goal: Move from standalone example scripts toward a platform execution contract that workers can use to run jobs and persist generated artifacts.

Deliverables:

- Training runner port
- Training execution result contract
- Artifact metadata contract
- Local example runner adapter
- Worker-oriented execution method
- Bootstrap integration with generated metrics
- Production-readiness execution checks

Acceptance criteria:

- Training execution is modeled behind a runner interface.
- Queued runs can transition through running to terminal status through the application layer.
- Generated metrics update the linked experiment run and training run.
- Evaluation reports include a versioned execution manifest with artifact metadata.
- Example execution requires an explicit adapter selector and does not infer workload from generic algorithms alone.
- Bootstrap uses generated local artifacts instead of static report values for new example training runs.

Implemented scope:

- `TrainingJobRunner` and `TrainingExecutionResult` define the execution boundary.
- `TrainingRunService.execute_training_run` is available for worker processes and records running and terminal events.
- `LocalExampleTrainingRunner` executes the three deterministic reference workloads when `forgeml.example_project_slug` selects a supported adapter.
- Bootstrap now starts training through public APIs, runs the matching local trainer, and records generated metrics plus artifact metadata.
- Backend Docker images include the `ml` package on `PYTHONPATH` so local example execution is available in demo containers.
- Unit tests cover service execution transitions, local runner behavior, bootstrap metadata, and readiness contracts.

## Sprint 15: Training Worker Polling

Goal: Add a local worker loop that discovers queued training runs, claims supported work, executes through the runner contract, and records terminal results.

Deliverables:

- Runnable training run query
- Training run claim operation
- Worker batch execution command
- Worker execution summary contract
- Local worker CLI
- SQLAlchemy claim integration tests
- Readiness checks for worker wiring

Acceptance criteria:

- Workers scan requested and queued runs within an organization.
- Unsupported queued runs are skipped instead of being misrouted.
- Supported runs are claimed before execution and cannot be claimed twice.
- Running events record the worker id.
- Worker summaries report scanned, executed, succeeded, failed, skipped, and executed run ids.
- The local worker CLI can run a single polling cycle from the command line.

Implemented scope:

- `TrainingRunRepository` now exposes runnable listing and claim operations.
- `SqlAlchemyTrainingRunRepository` implements queue discovery and row-level claim semantics.
- `TrainingRunService.execute_next_training_runs` processes supported queued work through the configured runner.
- `scripts/workers/run_training_worker.py` runs one local worker polling cycle for an organization.
- Unit and integration tests cover worker summaries, queue skipping, claiming, and terminal persistence.

## Sprint 16: Model Promotion Pipeline

Goal: Promote completed training results into the registry through a validated, idempotent application workflow.

Deliverables:

- Promotion command in the model registry application layer
- Training execution manifest validation
- Model artifact URI extraction
- Idempotent training-run to version mapping
- Public promotion API endpoint
- SDK and bootstrap integration
- Promotion metrics
- Projects page create action

Acceptance criteria:

- Only succeeded training runs can be promoted.
- Promotion requires the versioned training execution manifest persisted on the linked experiment run.
- The manifest must include a model artifact with a resolvable URI.
- Repeating the same promotion for a model and training run returns the existing version.
- Promoted versions retain metrics, signature, artifact URI, and lineage.
- Example bootstrap uses the promotion endpoint.
- The Projects page `New` action creates a project row instead of being inert.

Implemented scope:

- `ModelRegistryService.promote_training_run_to_model_version` validates training evidence before creating a candidate model version.
- `SqlAlchemyModelRegistryRepository` joins training runs to experiment reports to load promotion evidence.
- `/api/v1/models/{model_id}/versions/promote-training-run` exposes promotion through FastAPI.
- The ForgeML SDK and example bootstrapper now promote training runs through the public API.
- `forgeml_model_promotions_total` tracks successful and idempotent promotions.
- Frontend project creation is covered by Vitest and Playwright smoke coverage.

## Sprint 17: Registry Operations UI

Goal: Make model promotion and approval usable from the web interface.

Deliverables:

- Model registry mutation client methods
- Promotion workbench on the Models page
- Succeeded training-run picker
- Model format selection
- Editable model signature JSON
- Candidate approval request action
- Pending approval review actions
- Frontend regression tests

Acceptance criteria:

- The Models page loads registered models, selected model versions, and succeeded training runs for the selected project.
- Users can promote an unregistered succeeded training run into the selected model.
- The promotion request sends model format and signature metadata to the promotion API.
- Candidate versions can request approval.
- Pending versions can be approved or rejected.
- Registry queries refresh after promotion and review actions.
- Frontend tests cover the promotion and approval workflow.

Implemented scope:

- `frontend/src/modules/models/api/models.ts` now exposes promotion and approval mutation calls.
- `ModelsPage` includes a promotion workbench with model, training-run, format, and signature controls.
- Version rows expose request approval, approve, and reject actions based on status.
- React Query invalidation refreshes registry views after successful mutations.
- Vitest covers promotion request payloads and approval state transitions through mocked API calls.

## Sprint 18: Deployment Release Console

Goal: Make approved model versions releasable and operable from the Deployments page.

Deliverables:

- Deployment mutation client methods
- Deployment target creation form
- Release console for approved model versions
- Runtime config JSON editor
- Canary traffic input
- Revision health recording actions
- Traffic promotion and drain actions
- Rollback action for healthy revisions
- Deployment event history
- Frontend regression tests

Acceptance criteria:

- Users can create deployment targets for the selected project.
- The release console lists registered models and only approved versions as deployable candidates.
- Creating a revision sends model version, serving image, runtime config, and traffic percentage to the deployment API.
- Revision rows can record healthy, degraded, and unhealthy checks with latency and error-rate observations.
- Revision rows can move traffic to full allocation or drain traffic to zero.
- Healthy revisions expose rollback as an explicit action.
- Deployment queries, revision state, health state, and event history refresh after successful operations.
- Frontend tests cover revision creation, health recording, and traffic promotion through mocked API calls.

Implemented scope:

- `frontend/src/modules/deployments/api/deployments.ts` now exposes create target, create revision, traffic, health, rollback, and events calls.
- `DeploymentsPage` includes a release console backed by approved registry versions and existing deployment targets.
- Deployment target creation is available from the Deployment Targets panel.
- Rollout State rows expose health, traffic, and rollback controls while preserving immutable revision history.
- Deployment Events shows the selected target's rollout and health activity.
- Vitest covers the release workflow payloads and post-mutation state transitions.

## Sprint 19: Inference Endpoint Operations

Goal: Make healthy deployment revisions callable through managed inference endpoints and probeable from the web interface.

Deliverables:

- Inference mutation client methods
- Endpoint launchpad from servable deployment revisions
- Endpoint selection table
- Editable prediction probe payload
- Optional probe request id
- Request trace refresh after probes
- Metric snapshot recorder
- Snapshot cards with prediction, error, and latency summaries
- Frontend regression tests

Acceptance criteria:

- The Inference page loads deployment targets, selected deployment revisions, and project endpoints.
- Endpoint candidates are limited to active deployments with healthy or degraded revisions that have active traffic.
- Users can create an inference endpoint from a servable deployment revision.
- Endpoint creation sends deployment, revision, name, description, and route data to the public inference API.
- Users can probe a selected endpoint with editable JSON payloads.
- Successful probes refresh request logs and show prediction latency.
- Users can record aggregate metric snapshots with prediction count, error count, and latency percentiles.
- Snapshot and request queries refresh after successful operations.
- Frontend tests cover endpoint creation, probe payloads, and metric snapshot recording.

Implemented scope:

- `frontend/src/modules/inference/api/inference.ts` now exposes endpoint creation, prediction request ids, and metric snapshot recording.
- `InferencePage` includes an endpoint launchpad backed by deployment revision serving rules.
- Endpoint rows can be selected for probe, trace, and metric operations.
- The probe console accepts JSON payloads and surfaces mutation feedback.
- Metric snapshot recording is available from the Metric Snapshots panel.
- Vitest covers the end-to-end inference operations workflow through mocked API calls.

## Sprint 20: Monitoring Operations UI

Goal: Turn project monitoring into an endpoint-level triage surface with alert evaluation and production health context.

Deliverables:

- Alert evaluation client method
- Endpoint health table with selected endpoint state
- Endpoint drilldown panel
- Error-rate and p95 latency budget indicators
- Endpoint risk classification
- Endpoint-linked alert context
- Alert rule selector
- Manual alert evaluation action
- Operational focus panel for highest-risk endpoint
- Frontend regression tests

Acceptance criteria:

- The Monitoring page loads project summaries, endpoint summaries, alert rules, and alert events for the selected project.
- Endpoint rows expose prediction count, error rate, p50, p95, risk classification, and selection.
- The selected endpoint drilldown shows route, status, deployment revision, monitoring window, error budget, latency budget, and open alert count.
- Operators can evaluate a selected alert rule against the selected endpoint.
- Evaluation sends the selected endpoint id to the public alerting API.
- Evaluation feedback distinguishes triggered and clear outcomes.
- Alert events refresh after evaluation.
- The page highlights the highest-risk endpoint for operational focus.
- Frontend tests cover alert evaluation payloads and monitoring state rendering.

Implemented scope:

- `frontend/src/modules/alerts/api/alerts.ts` now exposes alert rule evaluation.
- `MonitoringPage` includes endpoint selection, risk badges, budget bars, drilldown metrics, and endpoint-linked alert context.
- Alert Evaluation lets operators select a rule and evaluate it against the selected endpoint.
- Operational Focus highlights the endpoint with the highest latency/error risk score.
- Vitest covers alert rule evaluation from monitoring with mocked monitoring and alerting APIs.

## Sprint 21: Alert Operations UI

Goal: Make alert rule creation and alert event lifecycle handling available from the Alerts page.

Deliverables:

- Alert rule creation client method
- Alert event acknowledgement client method
- Alert event resolution client method
- Alert rule creation form
- Rule metric, operator, threshold, window, severity, and enabled controls
- Alert event action controls
- Operation feedback for created, acknowledged, and resolved alerts
- Alert and monitoring query refresh after lifecycle changes
- Frontend regression tests

Acceptance criteria:

- Users can create alert rules for the selected project.
- Rule creation sends name, description, severity, metric, operator, threshold, window, and enabled state to the public alerting API.
- Open alert events can be acknowledged.
- Open or acknowledged alert events can be resolved.
- Resolved alert events do not expose lifecycle actions.
- Alert events refresh after acknowledge and resolve actions.
- Alert rules refresh after rule creation.
- Monitoring summary state is invalidated after incident lifecycle changes.
- Frontend tests cover rule creation, acknowledgement, and resolution payloads.

Implemented scope:

- `frontend/src/modules/alerts/api/alerts.ts` now exposes create, acknowledge, and resolve operations.
- `AlertsPage` includes a rule creation form with validated numeric threshold and window fields.
- Alert event cards expose acknowledgement and resolution actions based on event status.
- Page-level operation feedback reports rule creation and incident lifecycle results.
- Vitest covers rule creation plus alert acknowledgement and resolution through mocked API calls.
