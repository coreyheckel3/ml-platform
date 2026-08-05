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

## Sprint 22: Drift Operations UI

Goal: Turn drift detection into an operator workflow for creating baselines, running reports, inspecting feature-level drift, and handing drift signals to retraining policies.

Deliverables:

- Drift profile creation client method
- Drift report execution client method
- Drift-triggered retraining evaluation client method
- Drift profile creation form with JSON baseline validation
- Endpoint and profile selection for report execution
- Drift threshold, report window, sample limit, and report URI controls
- Report selection and detail panel
- Feature-level drift analysis cards
- Retraining policy handoff from selected drift reports
- Frontend regression tests

Acceptance criteria:

- Users can create drift reference profiles for the selected project.
- Profile creation sends name, description, optional lineage ids, and baseline profile JSON to the public drift API.
- Users can run a drift report against a selected reference profile and inference endpoint.
- Report execution sends endpoint id, window, threshold, sample limit, and report URI to the public drift API.
- The page refreshes project drift reports after report execution.
- Selecting a report refreshes feature-level drift results.
- Operators can evaluate an active drift retraining policy for the selected report when the policy matches the report deployment.
- Retraining run state refreshes after handoff evaluation.
- Frontend tests cover profile creation, report execution, feature results, and retraining evaluation payloads.

Implemented scope:

- `frontend/src/modules/drift_detection/api/drift.ts` now exposes create profile and run report operations.
- `frontend/src/modules/retraining/api/retraining.ts` now exposes policy evaluation.
- `DriftDetectionPage` includes reference profile creation, report execution controls, endpoint context, report selection, report detail, feature drift cards, and drift-to-retraining handoff.
- JSON baseline input is parsed and validated before profile creation.
- Numeric report controls validate API bounds before execution.
- Vitest covers the full drift operations workflow with mocked drift, monitoring, and retraining APIs.

## Sprint 23: Retraining Operations UI

Goal: Make automatic retraining policy management and run approval workflows operable from the Retraining page.

Deliverables:

- Dataset version listing client method
- Retraining policy creation client method
- Manual retraining trigger client method
- Retraining run approval client method
- Retraining run rejection client method
- Policy creation form with deployment, experiment, dataset version, feature set, trigger, guardrail, and training template controls
- Manual trigger workflow for selected policies
- Retraining run table with lifecycle actions
- Selected policy and selected run detail panels
- Frontend regression tests

Acceptance criteria:

- Users can create retraining policies for the selected project.
- Policy creation sends deployment id, trigger config, training template, cooldown, daily run limit, approval requirement, and enabled state to the public retraining API.
- Training templates are built from explicit experiment, dataset version or feature set, algorithm, model type, objective metric, run prefix, and hyperparameter controls.
- Users can manually trigger a retraining run for the selected policy.
- Pending approval runs can be approved.
- Pending approval runs can be rejected.
- Retraining runs and training run state refresh after lifecycle actions.
- Frontend tests cover policy creation, manual trigger, approval, and rejection payloads.

Implemented scope:

- `frontend/src/modules/datasets/api/datasets.ts` now exposes dataset version listing.
- `frontend/src/modules/retraining/api/retraining.ts` now exposes policy creation, manual trigger, approval, and rejection operations.
- `RetrainingPage` includes policy creation, policy detail, manual trigger, run table lifecycle actions, and run detail views.
- Policy creation validates trigger thresholds, guardrail bounds, lineage source selection, and hyperparameter JSON before submitting.
- Vitest covers the complete retraining operations workflow with mocked retraining, deployment, experiment, dataset, and feature store APIs.

## Sprint 24: Training Runs Operations UI

Goal: Make manual training run submission, cancellation, terminal result recording, and event inspection operable from the Training Runs page.

Deliverables:

- Training run start client method
- Training run detail client method
- Training run event listing client method
- Training run cancellation client method
- Training result recording client method
- Run creation form with experiment, dataset version, feature set, algorithm, model type, objective, and hyperparameter controls
- Selected run detail panel
- Training event timeline
- Terminal result recording form
- Frontend regression tests

Acceptance criteria:

- Users can start training runs for the selected project.
- Run creation sends experiment id, run name, dataset version or feature set id, algorithm, model type, objective metric, and hyperparameters to the public training API.
- Users can cancel queued, requested, or running training runs.
- Users can record terminal training results with status, metrics, evaluation report, and error message.
- Selecting a run refreshes run detail and event history.
- Training run, experiment, and event state refresh after lifecycle actions.
- Frontend tests cover run creation, result recording, event loading, and cancellation payloads.

Implemented scope:

- `frontend/src/modules/training_runs/api/trainingRuns.ts` now exposes start, detail, result, cancel, and event operations.
- `TrainingRunsPage` includes run submission, dependency selection, queue lifecycle actions, detail view, result recording, and event history.
- Training run creation validates lineage source selection and hyperparameter JSON before submitting.
- Result recording validates metrics and evaluation report JSON before submitting.
- Vitest covers the full training run operations workflow with mocked training, experiment, dataset, and feature store APIs.

## Sprint 25: Experiments Operations UI

Goal: Turn experiment tracking into an operator workflow for creating experiment groups, launching experiment runs, recording metrics, attaching artifacts, and completing run reviews from the Experiments page.

Deliverables:

- Experiment creation client method
- Experiment run start client method
- Experiment metric logging client method
- Experiment artifact logging client method
- Experiment artifact listing client method
- Experiment run completion client method
- Experiment creation form
- Run creation form with dataset version or feature set lineage
- Selected run detail panel with parameters and evaluation report
- Metric logging, artifact logging, and completion workflows
- Run artifact browser
- Frontend regression tests

Acceptance criteria:

- Users can create experiments for the selected project.
- Experiment creation sends name and description to the public experiment API.
- Users can start runs under the selected experiment.
- Run creation sends run name, model type, artifact URI, parameters, and exactly one lineage source to the public experiment API.
- Users can log numeric metrics and evaluation report JSON for a selected run.
- Users can log artifact name, type, URI, and metadata for a selected run.
- Users can complete a running experiment run with a terminal status, metrics, evaluation report, and optional error message.
- Experiment, run, and artifact state refresh after lifecycle actions.
- Frontend tests cover experiment creation, run creation, metric logging, artifact logging, and completion payloads.

Implemented scope:

- `frontend/src/modules/experiments/api/experiments.ts` now exposes create, start, metric, artifact, artifact listing, and completion operations.
- `ExperimentsPage` includes experiment creation, run submission, dependency selection, run selection, detail inspection, metric logging, artifact logging, completion, and artifact browsing.
- Experiment run creation validates lineage source selection and parameter JSON before submitting.
- Tracking operations validate metric, evaluation report, and artifact metadata JSON before submitting.
- Vitest covers the complete experiment operations workflow with mocked experiment, dataset, and feature store APIs.

## Sprint 26: Datasets Operations UI

Goal: Turn dataset management into an ingestion workflow for creating datasets, preparing object storage uploads, finalizing immutable versions, inspecting schemas, and running validation checks from the Datasets page.

Deliverables:

- Dataset creation client method
- Dataset version upload-instruction client method
- Dataset version finalization client method
- Dataset schema read client method
- Dataset validation execution client method
- Dataset validation history client method
- Dataset creation form
- Dataset version upload request form
- Signed upload instruction panel
- Version finalization form with CSV sample or manual schema controls
- Schema inspection panel
- Validation run history panel
- Frontend regression tests

Acceptance criteria:

- Users can create datasets for the selected project.
- Dataset creation sends name, description, and source type to the public dataset API.
- Users can request upload instructions for a selected dataset.
- Version creation sends filename and content type to the public dataset API and surfaces signed upload metadata.
- Users can finalize pending versions with object URI, content hash, size, and either CSV sample or schema fields.
- Finalization refreshes dataset versions, schema, and validation history.
- Users can execute validation for a selected dataset version.
- Validation history refreshes after validation execution.
- Frontend tests cover dataset creation, version creation, finalization, schema display, and validation payloads.

Implemented scope:

- `frontend/src/modules/datasets/api/datasets.ts` now exposes create, version creation, finalization, schema read, validation execution, and validation history operations.
- `DatasetsPage` includes dataset creation, version creation, upload instruction display, selected version details, finalization controls, schema inspection, and validation history.
- Finalization validates size, optional row count, CSV sample text, and manual schema field JSON before submitting.
- Vitest covers the full dataset operations workflow with mocked dataset lifecycle APIs.

## Sprint 27: Feature Store Operations UI

Goal: Turn feature store metadata into an operator workflow for creating feature sets, registering feature definitions, registering transformation pipelines, triggering materializations, and inspecting lineage from the Feature Store page.

Deliverables:

- Feature set creation client method
- Feature definition registration client method
- Feature definition listing client method
- Feature pipeline registration client method
- Feature pipeline listing client method
- Feature materialization trigger client method
- Feature materialization listing client method
- Feature lineage listing client method
- Feature set creation form
- Feature definition JSON registration form
- Pipeline registration form with source dataset lineage
- Pipeline detail panel
- Materialization history panel
- Lineage browser
- Frontend regression tests

Acceptance criteria:

- Users can create feature sets for the selected project.
- Feature set creation sends name, description, and entity key to the public feature store API.
- Users can register feature definitions for the selected feature set.
- Feature definition registration sends name, dtype, description, nullability, and constraints to the public feature store API.
- Users can register transformation pipelines against the selected feature set.
- Pipeline registration sends name, optional source dataset, code reference, and optional cron schedule.
- Registering a source dataset refreshes feature lineage state.
- Users can trigger materialization for a selected pipeline.
- Materialization history refreshes after a trigger.
- Frontend tests cover feature set creation, definition registration, pipeline registration, lineage display, and materialization payloads.

Implemented scope:

- `frontend/src/modules/feature_store/api/featureStore.ts` now exposes create, definition, pipeline, materialization, and lineage operations.
- `FeatureStorePage` includes feature set creation, selected feature set state, definition registration, pipeline registration, pipeline detail, materialization triggering, materialization history, and lineage browsing.
- Definition registration validates JSON array shape before submitting.
- Pipeline registration validates name and code reference before submitting.
- Vitest covers the full feature store operations workflow with mocked feature store and dataset APIs.

## Sprint 28: Projects and Administration Operations UI

Goal: Turn project management and settings into operational control surfaces for selecting active workspace context and inspecting authenticated RBAC state.

Deliverables:

- Project inventory context selector
- API-backed project creation workflow
- Browser-local project creation fallback
- Selected project detail panel
- Local active project context persistence
- Current-user API client
- Account context settings panel
- Permission grouping view
- Local workspace context controls
- Security defaults panel
- Frontend regression tests

Acceptance criteria:

- Users can load projects from the public project API when a token is present.
- Users can create API-backed projects from the Projects page.
- Project creation sends name and description to the public project API.
- Users can create browser-scoped projects when running without a token.
- Selecting a project writes the active project id to local workspace context.
- Settings reads authenticated principal, organization, and permission grants from `/auth/me`.
- Settings groups RBAC permissions by module scope.
- Users can clear active project context from Settings without mutating server state.
- Frontend tests cover project creation, project context selection, account context loading, permission display, and project context clearing.

Implemented scope:

- `ProjectsPage` now includes project inventory, creation, active context selection, and selected project detail.
- `frontend/src/modules/auth/api/auth.ts` exposes the current-user client method.
- `SettingsPage` now includes account context, permission groups, local workspace state, and security defaults.
- Vitest covers browser-local and API-backed project workflows plus authenticated settings behavior.

## Sprint 29: Login and Session Management UI

Goal: Add a real browser authentication workflow so platform operators can exchange credentials for API tokens, inspect session state, and sign out from the console.

Deliverables:

- Login API client method
- Browser session storage abstraction
- Sign-in page with credential exchange form
- Redirect handling after successful login
- Access token expiry metadata
- Shell account summary from `/auth/me`
- Shell sign-out action
- Settings integration with centralized session storage keys
- Playwright route coverage
- Frontend regression tests

Acceptance criteria:

- Users can submit email and password to `/auth/login` from the web console.
- Successful login stores access token, refresh token, token type, and expiry metadata under stable ForgeML storage keys.
- Successful login redirects to the requested internal route or Projects by default.
- Failed login displays an error and leaves token storage empty.
- The shell displays the authenticated principal from `/auth/me` when a token is present.
- Signing out clears access token, refresh token, expiry metadata, and active project context.
- Settings reads token state through the centralized session store.
- Frontend tests cover login success, login failure, shell account loading, and sign-out cleanup.

Implemented scope:

- `LoginPage` provides credential exchange, redirect handling, token persistence, and session policy visibility.
- `sessionStore` centralizes auth and project-context browser storage keys.
- `Shell` now renders account-aware sign-in and sign-out controls backed by `/auth/me`.
- `SettingsPage` consumes the shared session storage contract.
- Vitest and Playwright cover the new authentication surface.

## Sprint 30: Refresh Token Rotation and Logout Revocation

Goal: Back the browser session lifecycle with revocable refresh-token state so access renewal, sign-out, and refresh-token replay handling are enforced by the backend.

Deliverables:

- Refresh-session domain entity
- Refresh-session repository interface
- SQLAlchemy refresh-session model and repository
- Alembic migration for `auth_refresh_sessions`
- Refresh-token hashing before persistence
- Login persistence for refresh sessions
- `/auth/refresh` token rotation endpoint
- `/auth/logout` refresh-session revocation endpoint
- Shell automatic refresh for near-expired access tokens
- Shell backend logout call
- Backend unit, API, and repository integration tests
- Frontend regression tests for refresh and logout

Acceptance criteria:

- Login stores only a hash of the issued refresh token.
- Refresh tokens include a unique session identifier.
- `/auth/refresh` validates the signed refresh token and stored session state.
- Refresh succeeds only for active, unexpired, unrecalled sessions.
- Refresh returns a new access token and a new refresh token.
- The previous refresh session is revoked and linked to its replacement.
- Reusing a revoked refresh token fails and revokes remaining active sessions for that user.
- `/auth/logout` revokes the submitted refresh session without exposing token state.
- The shell refreshes near-expired browser sessions through `/auth/refresh`.
- The shell calls `/auth/logout` before clearing local auth and project context.

Implemented scope:

- `AuthenticationService` now persists refresh sessions, rotates them, detects replay, and revokes sessions on logout.
- `SqlAlchemyRefreshSessionRepository` implements hashed token lookup, rotation revocation, and user-wide active-session revocation.
- `202607190011_auth_refresh_sessions.py` adds the refresh-session table and indexes.
- Auth API schemas and routes expose refresh and logout operations.
- Frontend auth clients and shell lifecycle use backend refresh and logout.
- Unit, API, integration, and frontend tests cover the new session lifecycle.

## Sprint 31: Administration Audit Log

Goal: Add the first backend-backed administration console capability by making organization audit events searchable from the API and visible in Settings.

Deliverables:

- Administration module boundary
- Audit log domain entity
- Audit log repository interface
- SQLAlchemy audit log model and repository
- Administration application service with RBAC checks
- `/admin/audit-log` read API
- Settings audit log API client
- Settings audit log filter controls
- Settings audit event table
- Backend unit, API, and repository integration tests
- Frontend regression tests

Acceptance criteria:

- Audit log reads require `admin:audit_log:read`.
- Audit log reads are scoped to the authenticated principal organization.
- Audit log results are ordered newest first.
- Audit log results can be filtered by actor type, action, and resource type.
- API responses include actor, action, resource, metadata, and event timestamp.
- Settings displays audit events only for users with audit log permission.
- Settings shows clear states for signed-out users, missing permission, loading, request failure, and empty results.
- Frontend tests cover authenticated audit loading and filter query parameters.

Implemented scope:

- `AdministrationService` enforces RBAC and tenant scoping for audit reads.
- `SqlAlchemyAuditLogRepository` reads the existing `audit_log` table through the administration module boundary.
- `/api/v1/admin/audit-log` exposes filtered audit events.
- `SettingsPage` now includes an audit log browser with actor, action, and resource filters.
- Unit, API, integration, and frontend tests cover the audit log capability.

## Sprint 32: Audit Event Instrumentation

Goal: Move the audit log from a read-only administration surface to an application-wide write contract for high-value lifecycle events.

Deliverables:

- Audit event domain command
- Audit event recorder port
- SQLAlchemy audit append implementation
- Authentication login audit events
- Authentication refresh rotation audit events
- Authentication logout audit events
- Project creation audit events
- API dependency wiring for auth and project modules
- Backend unit and repository integration tests
- Security and implementation-state documentation updates

Acceptance criteria:

- Audit writes use the Administration module contract instead of writing SQLAlchemy models from feature modules.
- Authentication login records `auth.login` without storing credentials or tokens.
- Refresh-token rotation records `auth.refresh` with source and replacement session identifiers.
- Logout records `auth.logout` only when a refresh session is actually revoked.
- Project creation records `projects.create` with project id, slug, name, actor, and organization.
- Audit writes participate in the request transaction when the API dependency provides the SQLAlchemy repository.
- Existing audit log read API returns newly recorded events without a schema migration.
- Unit tests cover auth and project audit emission.
- Repository integration tests cover appending and reading recorded audit events.

Implemented scope:

- `AuditLogEvent` captures append requests separate from persisted `AuditLogEntry` records.
- `AuditEventRecorder` lets application services depend on an audit-write port.
- `SqlAlchemyAuditLogRepository.record` appends immutable events to the existing `audit_log` table.
- `AuthenticationService` records successful login, refresh rotation, and logout events through optional dependency injection.
- `ProjectService` records project creation events through optional dependency injection.
- Auth and project API dependencies provide the shared SQLAlchemy audit repository.
- Backend tests cover emitted audit payloads and repository persistence.

## Sprint 33: ML Lifecycle Audit Coverage

Goal: Extend central audit logging to high-risk ML platform operations while preserving module-local lifecycle events.

Deliverables:

- Shared Administration application helper for user audit events
- Training run queue audit events
- Training cancellation audit events
- Model approval request audit events
- Model approval and rejection audit events
- Deployment rollout audit events
- Deployment traffic update audit events
- Deployment rollback audit events
- Alert open, acknowledgement, and resolution audit events
- Retraining pending approval, trigger, skip, approval, and rejection audit events
- API dependency wiring for Training, Model Registry, Deployment, Alerting, and Retraining modules
- Backend unit coverage for each instrumented lifecycle family
- Security and implementation-state documentation updates

Acceptance criteria:

- New audit writes use the `AuditEventRecorder` port and do not import SQLAlchemy models from application services.
- API-created service instances share the request-scoped SQLAlchemy audit repository.
- Audit metadata includes stable resource, project, decision, and lifecycle identifiers.
- Audit metadata excludes credentials, bearer tokens, free-form approval comments, and raw operator notes.
- Training queue and cancellation events include run, experiment, algorithm, model type, and orchestrator context.
- Model governance events include model version, registered model, project, approval id, and decision context.
- Deployment rollout, traffic update, and rollback events include revision and environment context.
- Alert lifecycle events include rule, endpoint, severity, observed value, threshold, and status transition context.
- Retraining decisions include policy, deployment, trigger source, status, training run, and guardrail reason context.
- Unit tests cover emitted audit payloads for each instrumented lifecycle family.

Implemented scope:

- `record_user_audit_event` centralizes the append-call shape while keeping action names and metadata in owning services.
- `TrainingRunService` records `training_runs.queue` and `training_runs.cancel`.
- `ModelRegistryService` records `model_versions.request_approval`, `model_versions.approved`, and `model_versions.rejected`.
- `DeploymentService` records `deployments.rollout`, `deployments.update_traffic`, and `deployments.rollback`.
- `AlertingService` records `alert_events.open`, `alert_events.acknowledge`, and `alert_events.resolve`.
- `RetrainingService` records `retraining_runs.pending_approval`, `retraining_runs.trigger`, `retraining_runs.skip`, `retraining_runs.approve`, and `retraining_runs.reject`.
- Unit tests cover audit emission across training, registry, deployment, alerting, and retraining workflows.

## Sprint 34: Audit Operations Console

Goal: Turn the Settings audit log from a basic table into an operator-grade triage surface for security and ML lifecycle events.

Deliverables:

- Audit preset filters for common ML lifecycle families
- Project-context activity filter over audit metadata
- Selected audit event detail panel
- Metadata key-value inspection
- Action-specific visual indicators
- Regression coverage for audit presets, project scoping, and detail inspection
- Product-surface and implementation-state documentation updates

Acceptance criteria:

- Authorized users can quickly filter all events, training events, model review events, deployment rollout events, alert events, and retraining events.
- Users can narrow returned audit events to the active browser project context when metadata includes `project_id`.
- Selecting an audit event shows actor, organization, resource, time, and metadata in a stable detail panel.
- The audit table keeps its existing manual actor, action, and resource filters.
- The UI handles events with no metadata without layout shifts.
- Existing signed-out and missing-permission states are preserved.
- Frontend regression tests cover authenticated loading, presets, project scoping, manual filters, detail inspection, and project-context clearing.

Implemented scope:

- `SettingsPage` now includes audit presets, project activity filtering, selected-row highlighting, and a detail panel.
- Audit metadata is rendered as key-value rows with stable wrapping for long IDs and nested values.
- Action icons distinguish alert, deployment, retraining, training, and generic audit event families.
- `SettingsPage` tests cover preset filtering, active-project filtering, detail metadata inspection, and existing workspace controls.

## Sprint 35: Frontend Supply-Chain Hardening

Goal: Remove vulnerable production frontend dependencies and make dependency auditing a release-blocking control.

Deliverables:

- Frontend production dependency audit
- Removal of vulnerable React Router packages from the shipped bundle dependency graph
- First-party browser routing abstraction for the app shell, navigation, login redirect, and tests
- CI production dependency audit gate
- Production-readiness supply-chain contract
- Runbook and threat-model updates
- Frontend router regression tests

Acceptance criteria:

- `npm --prefix frontend audit --omit=dev` reports zero production vulnerabilities.
- CI runs the production dependency audit after installing frontend dependencies.
- The production-readiness script verifies the audit gate exists.
- The frontend lockfile does not include `react-router` or `react-router-dom`.
- App navigation, active nav state, login redirects, and wildcard redirects continue to work.
- Frontend tests cover routing, login redirect behavior, shell auth behavior, and app rendering.

Implemented scope:

- `react-router-dom` and transitive `react-router` were removed from production dependencies.
- `frontend/src/shared/routing/router.tsx` provides ForgeML's narrow browser-routing contract over the History API.
- App, shell, login, and tests now use the first-party routing abstraction.
- GitHub Actions runs `npm --prefix frontend audit --omit=dev` in the frontend job.
- `scripts/ci/production_readiness.py` validates the frontend supply-chain gate offline.
- Runbook, threat model, README, and readiness tests document and enforce the new control.

## Sprint 36: Frontend Performance Budgets

Goal: Convert frontend bundle-size risk into a measured release gate while keeping the application shell responsive as ForgeML grows.

Deliverables:

- Route-level lazy loading for all primary ForgeML pages
- Suspense-backed route loading state in the application shell
- Sidebar route preloading on hover and keyboard focus
- Frontend JavaScript chunk budget checker
- CI bundle-budget gate after production build
- Production-readiness performance contract
- Frontend route contract and bundle-budget tests
- Runbook and implementation-state documentation updates

Acceptance criteria:

- The app shell no longer statically imports every page module.
- Each navigable page route is backed by a preloadable lazy import.
- Unknown routes still redirect to the dashboard.
- Keyboard and pointer navigation can warm route chunks before activation.
- `npm --prefix frontend run build` produces JavaScript chunks below the 500 KB budget.
- CI runs the bundle-budget checker after building the frontend.
- Production-readiness checks verify route-level code splitting and the bundle-budget gate.

Implemented scope:

- `frontend/src/app/routes.tsx` centralizes lazy route definitions and route preloaders.
- `App` renders routes behind a Suspense loading state.
- `Shell` preloads route chunks on nav focus and hover.
- `scripts/ci/check_frontend_bundle_budget.py` enforces the JavaScript chunk budget over built Vite assets.
- GitHub Actions runs the bundle-budget check in the frontend job.
- Backend ops tests cover the bundle-budget checker and readiness contract.

## Sprint 37: API Contract Governance

Goal: Make the ForgeML REST API contract explicit, deterministic, and release-gated so frontend, SDK, and automation clients can depend on stable platform APIs.

Deliverables:

- Canonical OpenAPI contract generated from the FastAPI application
- Deterministic OpenAPI serialization
- CI drift check for the checked-in API contract
- Production-readiness contract validation
- Contract tests for generation, drift detection, and core API coverage
- OpenAPI runbook documentation
- Implementation-state documentation updates

Acceptance criteria:

- `contracts/openapi/forgeml.v1.openapi.json` is generated from the running FastAPI app.
- The generator supports write and `--check` modes.
- CI fails when the checked-in OpenAPI contract is stale.
- Production-readiness checks verify the OpenAPI contract exists and covers core API groups.
- Tests prove deterministic serialization, stale-contract detection, write/check round trips, and checked-in contract freshness.
- Contract documentation explains how to regenerate and verify the schema.

Implemented scope:

- `scripts/ci/generate_openapi_contract.py` generates and verifies the canonical OpenAPI artifact.
- `contracts/openapi/forgeml.v1.openapi.json` captures the current FastAPI API schema.
- GitHub Actions runs the OpenAPI contract check in the backend job.
- Production-readiness checks include an OpenAPI contract gate.
- Backend ops tests cover contract freshness, core route coverage, and generator behavior.

## Sprint 38: API Authorization Contract

Goal: Prevent accidental unauthenticated API exposure by making public and protected route posture explicit, generated, and release-gated.

Deliverables:

- Generated API authorization contract from the FastAPI route table
- Public route allowlist for health, metrics, and token exchange endpoints
- Detection for any non-allowlisted public API route
- CI authorization contract gate
- Production-readiness authorization contract gate
- Security contract documentation
- Threat-model and implementation-state documentation updates
- Unit tests for route classification, stale contract detection, and policy violations

Acceptance criteria:

- Every non-allowlisted API route is protected by the `get_current_principal` dependency.
- The checked-in authorization contract lists all public and protected route records.
- The checker fails when the checked-in contract is stale.
- The checker fails when a private API route is reachable without a principal dependency.
- CI runs the authorization contract checker in the backend job.
- Production-readiness checks verify public and protected route invariants.

Implemented scope:

- `scripts/ci/check_api_authorization_contract.py` introspects FastAPI `APIRoute` dependencies and validates public route posture.
- `contracts/security/api-authorization.v1.json` captures the current generated authorization manifest.
- GitHub Actions runs the API authorization contract check after the OpenAPI check.
- Production-readiness checks enforce key public and protected route coverage.
- Security docs and threat model now describe the API authorization contract.

## Sprint 39: Permission Catalog Governance

Goal: Make ForgeML's RBAC vocabulary explicit, role-oriented, and release-gated so new service-layer permission checks cannot drift into undocumented string literals.

Deliverables:

- Central permission catalog with module, action, and description metadata
- Role presets for platform admins, ML engineers, ML operators, viewers, and security auditors
- Generated permission catalog security contract
- Service-layer permission scanner for enforced `principal.has(...)` and `_require(...)` checks
- CI permission catalog gate
- Production-readiness permission catalog gate
- Contract tests for catalog coverage, stale detection, role references, and unknown permission detection
- Security and runbook documentation updates

Acceptance criteria:

- Every service-enforced permission string is present in the central catalog.
- Every role preset references known permissions or the explicit wildcard.
- `contracts/security/permission-catalog.v1.json` captures permissions, roles, and enforcement locations.
- The checker fails when a service enforces an unknown permission.
- The checker fails when the checked-in permission catalog is stale.
- CI and production-readiness both run the permission catalog gate.

Implemented scope:

- `forgeml.platform.security.permissions` defines the canonical permission and role preset vocabulary.
- `scripts/ci/check_permission_catalog.py` extracts enforced permissions from service modules and verifies the catalog.
- `contracts/security/permission-catalog.v1.json` records the generated permission catalog contract.
- GitHub Actions and production-readiness checks enforce permission catalog freshness.
- Ops tests cover catalog coverage, role references, stale detection, and unknown permission violations.

## Sprint 40: Runtime Configuration Safety

Goal: Prevent ForgeML from booting production-like runtimes with local development
defaults, exposed docs, wildcard CORS, disabled throttling, or localhost backing
services.

Deliverables:

- Runtime configuration policy module enforced during FastAPI app creation
- Production-like environment aliases for `production`, `prod`, and `staging`
- Guardrails for JWT secrets, docs exposure, rate limiting, CORS, PostgreSQL, Redis,
  object storage, MLflow, and Airflow
- Generated runtime config security contract
- CI runtime config policy gate
- Production-readiness runtime config policy gate
- Policy, app startup, contract, and readiness tests
- Security, runbook, and implementation-state documentation updates

Acceptance criteria:

- Local development continues to support low-friction defaults.
- Production-like environments fail fast when `FORGEML_JWT_SECRET` is default or too short.
- Production-like environments fail fast when API docs are exposed.
- Production-like environments fail fast when rate limiting is disabled.
- Production-like environments require explicit non-local CORS origins.
- Production-like environments reject localhost database, Redis, object storage, MLflow,
  and Airflow endpoints.
- The checked-in runtime config policy contract is deterministic and release-gated.
- CI and production-readiness both run the runtime config policy checker.

Implemented scope:

- `forgeml.platform.config_policy` defines and enforces runtime guardrails.
- `create_app` validates resolved settings before configuring database resources.
- `contracts/security/runtime-config-policy.v1.json` records the generated policy contract.
- `scripts/ci/check_runtime_config_policy.py` verifies guardrail coverage and contract freshness.
- GitHub Actions and production-readiness checks enforce runtime config safety.
- Unit and API tests cover local defaults, hardened production config, insecure production config,
  startup enforcement, stale contracts, and contract shape.

## Sprint 41: Dependency-Aware Readiness Probes

Goal: Replace static readiness with typed dependency probes so deployment platforms can
stop routing traffic to ForgeML API instances that cannot reach core control-plane
dependencies.

Deliverables:

- Platform readiness checker with injectable dependency probes
- Typed readiness response models for passing and failing probe states
- Database readiness probe using the configured SQLAlchemy engine
- Redis readiness probe with explicit socket timeouts
- Prometheus metrics for readiness probe status and latency
- `/health/ready` `503` response contract for failed dependency checks
- Production config policy requirement for enabled readiness checks
- Production-readiness gate for readiness wiring, metrics, and OpenAPI coverage
- Unit and API tests for shallow readiness, passing probes, failing probes, metrics, and sanitized errors
- Runbook, threat-model, monitoring, ADR, and sprint documentation updates

Acceptance criteria:

- Local development can keep shallow readiness for low-friction workflows.
- Production-like environments must enable dependency readiness checks.
- `/health/ready` returns `200` with probe details when enabled probes pass.
- `/health/ready` returns `503` with sanitized probe details when any enabled probe fails.
- Readiness probe status and latency are exposed as low-cardinality Prometheus metrics.
- OpenAPI includes the `503` readiness response model.
- Production-readiness checks verify readiness config, probes, metrics, and API contract wiring.

Implemented scope:

- `forgeml.platform.health` defines `ReadinessChecker`, `DependencyProbe`, and typed response models.
- `forgeml.platform.database.session` exposes a narrow database ping using the configured engine.
- `create_app` accepts an injectable readiness checker and wires `/health/ready` to the checker.
- Runtime config policy now requires readiness checks in production-like environments.
- OpenAPI and runtime config policy contracts were regenerated.
- Unit and API tests cover readiness state transitions, metrics, Redis ping behavior, startup wiring, and sanitized failure payloads.

## Sprint 42: Structured Request Logging Contract

Goal: Make API request logging queryable, traceable, and safe for production operations by
emitting contracted structured events with redaction before log emission.

Deliverables:

- Structured JSON log formatter for platform runtime logs
- Versioned HTTP request log event builder
- Request middleware emission with service, environment, trace ID, route, status, latency, client host, and sanitized query parameters
- Sensitive field redaction for authorization, cookies, tokens, passwords, secrets, and API keys
- Runtime config flags for structured logging and request logging
- Production config policy guardrails requiring structured and request logging
- Generated observability contract for request log event shape and redaction markers
- CI request logging contract gate
- Production-readiness request logging gate
- Unit, API, contract, and readiness tests
- Runbook, threat-model, monitoring, testing, CI, ADR, and implementation-state documentation updates

Acceptance criteria:

- API middleware emits `forgeml.request_log.v1` events with stable top-level and HTTP fields.
- Request logs include the same trace ID returned to clients.
- Sensitive query parameters are redacted before the event reaches the logger.
- Request logging can be disabled for local workflows through explicit settings.
- Production-like environments fail fast when structured logging or request logging is disabled.
- The checked observability contract is deterministic and release-gated.
- Production-readiness verifies logging config, middleware emission, redaction, and contract wiring.

Implemented scope:

- `forgeml.platform.observability.logging` defines the JSON formatter, event builder, redaction helpers, and request log schema constants.
- `RequestContextMiddleware` now emits structured request events after metrics and trace headers.
- `scripts/ci/check_request_logging_contract.py` verifies event shape, redaction, and checked-in contract freshness.
- `contracts/observability/request-log-event.v1.json` captures the request logging contract.
- GitHub Actions and production-readiness run the request logging contract gate.
- Tests cover redaction, formatter serialization, middleware emission, disabling request logs, contract freshness, and production policy guardrails.

## Sprint 43: API Problem Details Contract

Goal: Make API failures stable, traceable, and safe for frontend, SDK, and automation clients by
normalizing errors into a checked Problem Details envelope.

Deliverables:

- API-wide Problem Details response builder and typed response model
- Normalized ForgeML domain error responses
- Sanitized request validation error responses without raw input values
- Normalized HTTP exception responses for framework-level errors
- Generic internal-error handler with sanitized detail
- Generated API Problem Details contract
- CI Problem Details contract gate
- Production-readiness Problem Details gate
- Unit, API, contract, and readiness tests
- API contract, runbook, threat-model, testing, CI, ADR, and implementation-state documentation updates

Acceptance criteria:

- All API error responses handled by the platform include `type`, `title`, `status`, `detail`,
  `trace_id`, and `errors`.
- Domain errors preserve their status codes, codes, messages, details, and trace IDs.
- Request validation errors omit raw input values.
- HTTP exceptions return the shared envelope.
- Unexpected exceptions return a generic internal-error detail.
- The checked API error contract is deterministic and release-gated.
- CI and production-readiness both run the Problem Details checker.

Implemented scope:

- `forgeml.platform.api.problem_details` defines the Problem Details model, builders, and validation-error normalization.
- `install_error_handlers` now covers ForgeML errors, request validation errors, HTTP exceptions, and unexpected exceptions.
- `scripts/ci/check_problem_details_contract.py` verifies envelope shape, sanitized validation errors, domain error mappings, and contract freshness.
- `contracts/api/problem-details.v1.json` captures the checked API error contract.
- GitHub Actions and production-readiness run the Problem Details gate.
- Tests cover response builders, domain errors, validation errors, HTTP exceptions, sanitized internal errors, contract freshness, and readiness wiring.

## Sprint 44: Alembic Migration Governance

Goal: Make database schema evolution explicit, reviewable, and release-gated by
publishing a checked Alembic migration topology contract.

Deliverables:

- Alembic migration graph extractor that parses migration metadata without importing migrations
- Deterministic database contract under `contracts/database`
- CI gate for duplicate revisions, unknown parent revisions, multiple heads, and stale contracts
- Production-readiness gate for migration contract freshness and reversible migration hooks
- Unit tests for graph extraction, stale contracts, duplicate revisions, unknown parents, multiple heads, missing downgrades, deterministic serialization, and checked-in contract freshness
- Database contract documentation, production-readiness runbook updates, testing strategy updates, CI strategy updates, schema strategy updates, ADR, and README updates

Acceptance criteria:

- The checked contract records the current base revision, head revision, migration count, branch points, merge revisions, migration files, and topological order.
- The repository has exactly one Alembic base revision and exactly one Alembic head revision.
- Every migration defines both `upgrade()` and `downgrade()`.
- Future migration changes fail CI unless the checked contract is regenerated.
- Production-readiness runs the same migration contract check used by CI.

Implemented scope:

- `scripts/ci/check_alembic_migration_contract.py` parses Alembic migration files with `ast`, validates graph topology, writes contracts, and checks contract freshness.
- `contracts/database/alembic-migrations.v1.json` captures the checked migration chain from `202607180001` through the current head.
- GitHub Actions and production-readiness run the Alembic migration contract gate.
- Tests cover valid topology, graph violations, checked-in contract freshness, readiness wiring, and deterministic serialization.

## Sprint 45: SQLAlchemy Schema Contract Governance

Goal: Make the application-owned database metadata explicit and release-gated so ORM
schema changes cannot drift from the platform contract.

Deliverables:

- SQLAlchemy metadata contract generator compiled for PostgreSQL
- Checked schema contract under `contracts/database`
- CI gate for schema contract freshness
- Production-readiness gate for required tables, metadata depth, and indexed foreign keys
- Central metadata registration fix for the administration audit log table
- Alembic migration adding indexes for foreign-key lookup columns surfaced by the schema gate
- Unit tests for checked metadata extraction, stale contracts, missing required tables, keyless tables, naming policy, unindexed foreign keys, deterministic serialization, and production-readiness wiring
- README, database contract docs, runbook, schema strategy, testing strategy, CI strategy, ADR, and sprint documentation updates

Acceptance criteria:

- The checked contract records tables, columns, primary keys, foreign keys, indexes, and unique constraints from `Base.metadata`.
- The application metadata registry includes all core platform tables, including audit logs.
- Foreign-key columns are indexed unless they are already primary keys.
- ORM schema changes fail CI unless the checked contract is regenerated.
- Schema metadata governance and Alembic topology governance both run in production-readiness.

Implemented scope:

- `scripts/ci/check_sqlalchemy_schema_contract.py` imports the central model registry, validates `Base.metadata`, writes deterministic contracts, and checks contract freshness.
- `contracts/database/sqlalchemy-schema.v1.json` captures the current 38-table PostgreSQL schema metadata surface.
- `forgeml.platform.database.models` now registers `AuditLogModel`.
- Migration `202607190013_schema_contract_indexes.py` adds indexes for refresh-session replacement lineage and feature-pipeline source dataset lookups.
- GitHub Actions and production-readiness run the SQLAlchemy schema contract gate.
- Tests cover valid metadata, contract drift, required-table coverage, naming policy, foreign-key index coverage, readiness wiring, and deterministic serialization.

## Sprint 46: Browser E2E Platform Flows

Goal: Add browser-level confidence that ForgeML's control-plane UI can drive the core ML lifecycle without requiring live infrastructure in every frontend CI run.

Deliverables:

- Stateful Playwright ForgeML API mock that preserves project, dataset, training, registry, deployment, inference, monitoring, and alert state across pages
- Browser lifecycle spec covering login, project creation, dataset validation, training result capture, model approval, deployment release, endpoint probing, metric snapshots, and alert evaluation
- GitHub Actions frontend E2E gate
- Production-readiness E2E contract check
- README, readiness runbook, testing strategy, CI strategy, and ADR updates

Acceptance criteria:

- `npm --prefix frontend run e2e` exercises the primary ML platform workflow through user-facing pages.
- The E2E fixture intercepts network requests at the browser boundary instead of replacing application code.
- CI fails if the browser lifecycle spec is removed from the frontend job.
- Production-readiness verifies the E2E suite and stateful mock remain checked in.

Implemented scope:

- `frontend/tests/e2e/fixtures/forgemlApiMock.ts` implements a stateful API surface for auth, projects, datasets, training, model registry, deployments, inference, monitoring, and alerting.
- `frontend/tests/e2e/platform-lifecycle.spec.ts` drives a realistic chargeback-risk workflow across ForgeML pages.
- GitHub Actions runs the Playwright E2E suite in the frontend job.
- `scripts/ci/production_readiness.py` validates the E2E contract and CI wiring.

## Sprint 47: Release Candidate Smoke Governance

Goal: Give operators and reviewers a deterministic way to prove a ForgeML release can reach the real API control plane end to end without mutating target data.

Deliverables:

- Non-mutating release smoke runner for live local or staging APIs
- Versioned operations contract for required smoke stages
- CI contract checker and production-readiness gate
- Unit tests for successful smoke runs, auth failure, missing project context, optional training-log coverage, stale contracts, and CI wiring
- README, readiness runbook, testing strategy, CI strategy, operations contract documentation, and ADR updates

Acceptance criteria:

- The smoke runner logs in and verifies health, identity, projects, datasets, features, experiments, training, training logs when available, model registry, deployments, inference endpoints, monitoring, alerts, drift, and retraining surfaces.
- The runner emits a versioned JSON report suitable for release evidence.
- The checked operations contract is deterministic and release-gated in CI.
- Production-readiness verifies the smoke script, contract, runbook command, and required stage coverage.

Implemented scope:

- `scripts/ops/release_smoke.py` implements a read-only live API smoke harness with injectable transport for tests.
- `contracts/ops/release-smoke.v1.json` records required release smoke stages and runtime requirements.
- `scripts/ci/check_release_smoke_contract.py` validates contract freshness, required stage depth, read-only posture, and CI wiring.
- Backend ops tests cover smoke execution behavior, contract drift, and production-readiness wiring.

## Sprint 48: Release Manifest Provenance

Goal: Make every ForgeML release reviewable by producing a signed-off manifest of source revision, required contract hashes, Docker image targets, quality gates, and smoke evidence.

Deliverables:

- Release manifest builder for local, CI, and staging release evidence
- Versioned operations contract for manifest structure, required artifacts, image targets, evidence types, and quality gates
- CI contract checker and production-readiness gate
- Unit tests for manifest hashing, image target provenance, smoke evidence ingestion, missing required artifacts, stale contracts, and CI wiring
- README, readiness runbook, operations contract documentation, testing strategy, CI strategy, and ADR updates

Acceptance criteria:

- The manifest records Git SHA, branch, worktree cleanliness, release version, CI URL, required artifact SHA-256 hashes, Docker image targets, quality gates, and optional release smoke evidence.
- The checked operations contract is deterministic and release-gated in CI.
- Production-readiness verifies the manifest builder, contract, runbook command, required artifacts, image targets, quality gates, and hashing behavior.
- The release runbook tells operators how to build the manifest after smoke and CI evidence are available.

Implemented scope:

- `scripts/ops/build_release_manifest.py` builds versioned release provenance manifests with deterministic file hashing and optional smoke-result evidence.
- `contracts/ops/release-manifest.v1.json` records required manifest fields, release artifacts, image targets, quality gates, and evidence types.
- `scripts/ci/check_release_manifest_contract.py` validates contract freshness, required artifact coverage, image target coverage, quality gates, and CI wiring.
- Backend ops tests cover manifest behavior, contract drift, and production-readiness wiring.

## Sprint 49: CI Release Evidence Publication

Goal: Make the release manifest automatically available from successful main-branch CI runs so reviewers and operators do not have to reconstruct release evidence by hand.

Deliverables:

- Main-branch `release-evidence` GitHub Actions job that runs after backend, frontend, Docker, and production-readiness jobs
- Release manifest artifact upload with `if-no-files-found: error`
- Versioned operations contract for release evidence workflow requirements
- CI checker and production-readiness gate for release evidence publication
- Unit tests for workflow fragments, stale contracts, checked-in contract freshness, and production-readiness wiring
- README, readiness runbook, operations contract documentation, testing strategy, CI strategy, and ADR updates

Acceptance criteria:

- CI builds `dist/release/forgeml-release-manifest.json` after required release gates pass.
- CI uploads the manifest as the `forgeml-release-manifest` artifact on pushes to `main`.
- The checked workflow contract is deterministic and release-gated in CI.
- Production-readiness verifies the evidence job, dependencies, manifest path, upload behavior, and contract documentation.

Implemented scope:

- `.github/workflows/ci.yml` now includes a `release-evidence` job gated on backend, frontend, Docker, and production-readiness success.
- `contracts/ops/release-evidence-workflow.v1.json` records required workflow fragments, dependencies, manifest path, and artifact name.
- `scripts/ci/check_release_evidence_workflow.py` validates workflow contract freshness and CI publication behavior.
- Backend ops tests cover workflow validation, contract drift, and production-readiness wiring.

## Sprint 50: Release Manifest Verification

Goal: Make every release manifest independently verifiable so operators and
reviewers can prove the CI artifact still matches the checked source tree and
release governance contracts.

Deliverables:

- Release manifest verifier CLI for local, CI, and staging evidence checks
- Versioned operations contract for verifier behavior and required checks
- CI gate for verifier contract freshness and release-evidence job execution
- Release-evidence job verification before artifact upload
- Unit tests for successful verification, artifact hash tampering, missing quality gates, CI evidence linkage, image digest requirements, stale contracts, and readiness wiring
- README, readiness runbook, operations contract documentation, testing strategy, CI strategy, and ADR updates

Acceptance criteria:

- The verifier checks manifest schema version, release metadata, source metadata, artifact hashes, Dockerfile hashes, image digest shape, quality gate coverage, CI evidence linkage, and release smoke evidence integrity.
- CI verifies `dist/release/forgeml-release-manifest.json` before uploading the `forgeml-release-manifest` artifact.
- The checked verifier contract is deterministic and release-gated in CI.
- Production-readiness verifies the verifier CLI, contract, runbook command, CI wiring, and hash-validation behavior.

Implemented scope:

- `scripts/ops/verify_release_manifest.py` emits versioned verification reports and fails on release evidence integrity violations.
- `contracts/ops/release-manifest-verification.v1.json` records required verifier checks, CLI flags, and report schema version.
- `scripts/ci/check_release_manifest_verifier_contract.py` validates verifier contract freshness and CI wiring.
- `.github/workflows/ci.yml` now verifies the release manifest before upload from the `release-evidence` job.
- The release manifest contract now includes release evidence workflow and verifier contracts as required operations artifacts.

## Unified Sprint Plan from Sprint 46

This track reconciles the completed release-governance work with the
product/runtime platform hardening roadmap. Completed sprint sections above
remain the implementation record; future sprint work should follow this unified
sequence.

| Sprint | Theme | Status | Scope |
| --- | --- | --- | --- |
| 46 | Browser E2E Platform Flows | Completed | Login, project creation, dataset validation, training result capture, model approval, deployment release, endpoint probing, monitoring snapshots, and alert evaluation through Playwright. |
| 47 | Release Candidate Smoke Governance | Completed | Read-only live API smoke runner, release smoke contract, CI gate, production-readiness gate, and operator runbook coverage. |
| 48 | Release Manifest Provenance | Completed | Release manifest builder, required contract hashes, image target provenance, quality gates, smoke evidence ingestion, and manifest contract. |
| 49 | CI Release Evidence Publication | Completed | Main-branch release-evidence job, manifest artifact upload, workflow contract, CI gate, and production-readiness validation. |
| 50 | Release Manifest Verification | Completed | Manifest verifier CLI, verification contract, CI verification before upload, artifact and Dockerfile hash checks, quality gate coverage, and CI evidence linkage. |
| 51 | Background Worker / Job Queue Hardening | Next | Real queued job lifecycle, retry policy, dead-letter handling, worker heartbeat, job lease timeout, and worker observability. |
| 52 | Artifact Storage Abstraction | Planned | MinIO/S3-backed artifacts, model artifact manifests, dataset artifact manifests, checksum validation, artifact lineage, and storage contract tests. |
| 53 | MLflow Integration Layer | Planned | MLflow adapter behind ForgeML interfaces, parameter/metric/artifact logging, training-run synchronization, experiment mapping, and adapter contract tests. |
| 54 | Airflow Orchestration Adapter | Planned | DAG trigger adapter, training pipeline DAG contracts, status polling, local fallback adapter, retry mapping, and orchestration contract tests. |
| 55 | Deployment Runtime Hardening | Planned | Model serving adapter boundary, endpoint revision resolution, canary traffic simulation, rollback validation, inference health probes, and runtime contract tests. |
| 56 | Monitoring Dashboards v2 | Planned | Richer frontend monitoring for inference errors, latency percentiles, drift trends, training failures, retraining activity, and operational drilldowns. |
| 57 | Security and Multi-Tenant Hardening | Planned | Organization isolation tests, RBAC matrix tests, rate-limit tests, audit-log coverage expansion, secrets policy, and configuration documentation. |
| 58 | Developer Experience / Demo Readiness | Planned | One-command local bootstrap, guided demo script, seeded data refresh, screenshots, architecture walkthrough, and reviewer-facing setup path. |

The numbering keeps the shipped release-governance sprints intact and moves the
runtime platform roadmap forward from Sprint 51.
