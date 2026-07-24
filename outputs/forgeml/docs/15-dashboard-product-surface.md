# Dashboard and Product Surface

The ForgeML web application should feel like a commercial SaaS product for ML engineering teams: dense, navigable, operational, and focused on repeated workflows.

## Product Navigation

Primary pages:

- Dashboard
- Sign In
- Projects
- Examples
- Datasets
- Feature Store
- Experiments
- Training Runs
- Models
- Deployments
- Inference
- Monitoring
- Drift
- Retraining
- Alerts
- Settings

The navigation should support organization and project context switching without hiding operational state.

## Sign In

Purpose: Exchange human operator credentials for API access and make authenticated workflows discoverable.

Capabilities:

- Email and password credential exchange through `/auth/login`
- Access and refresh token persistence in browser-local session storage
- Access token expiry visibility
- Redirect back to the requested workflow after login
- Shell account state backed by `/auth/me`
- Sign-out action that clears token and active project context

## Dashboard

Purpose: Give ML engineers and platform operators a fast summary of work needing attention.

Core widgets:

- Active projects
- Recent training runs
- Failed pipelines
- Deployments by health
- Open alerts by severity
- Drift incidents
- Model approvals waiting for review
- Prediction volume trend

## Projects

Purpose: Manage independent ML projects.

Capabilities:

- Project list with owner, status, recent activity, and health summary
- Project creation
- Project details
- Active project context selection for downstream workflow pages
- API-backed inventory mode with local browser fallback
- Project members
- Project settings
- Project activity timeline

## Examples

Purpose: Show reference workloads that exercise the platform lifecycle end to end.

Capabilities:

- Movie Recommendation, Semantic Search, and Fraud Detection catalog
- Dataset, feature set, model, endpoint, alert, and retraining summary
- Offline quality metrics surfaced per workload
- Lifecycle coverage view across ingestion, feature engineering, experiments, registry, deployment, drift, and retraining

## Datasets

Purpose: Manage dataset assets and version history.

Capabilities:

- Dataset list
- Dataset creation
- Selected dataset state
- Dataset version timeline
- Dataset version upload instructions using signed URLs
- Version finalization with content hash, size, row count, and schema metadata
- CSV sample schema inference controls
- Manual schema field controls
- Schema view
- Validation run execution
- Validation report history
- Profile summary
- Dataset lineage links
- Operation feedback for ingestion actions

## Feature Store

Purpose: Manage reusable feature contracts, transformation pipelines, lineage, and materialized feature versions.

Capabilities:

- Feature set list
- Feature set creation
- Selected feature set state
- Feature definition registration
- Feature definition replacement workflow
- Feature constraints inspection
- Pipeline registration with code reference and schedule
- Source dataset lineage selection
- Pipeline detail view
- Manual materialization trigger
- Materialization history
- Offline URI and online reference inspection
- Lineage link browser
- Operation feedback for feature store actions

## Experiments

Purpose: Compare training experiments and inspect run quality.

Capabilities:

- Experiment list
- Experiment creation
- Selected experiment state
- Experiment run launch with dataset version or feature set lineage
- Run table with status, metrics, duration, creator
- Metric comparison charts
- Parameter comparison
- Metric and evaluation report logging
- Artifact metadata logging
- Artifact browser
- Evaluation report view
- Terminal run completion
- Operation feedback for tracking actions

## Training Runs

Purpose: Track active and historical training execution.

Capabilities:

- Run queue
- Manual run submission
- Experiment and training lineage selection
- Dataset version and feature set training sources
- Hyperparameter JSON validation
- Selected run detail
- Training event timeline
- Terminal result recording
- Run cancellation
- Status filters
- Runtime metrics
- Failure details
- Link to dataset, features, experiment, and model output

## Models

Purpose: Govern registered model versions.

Capabilities:

- Registered model list
- Promotion workbench for succeeded training runs
- Model signature editor
- Version table
- Model lineage
- Metrics summary
- Approval request and review actions
- Signature view
- Approval request
- Approval and rejection workflow

## Deployments

Purpose: Operate production model serving safely.

Capabilities:

- Deployment list
- Deployment target creation
- Approved model-version release console
- Revision history
- Canary rollout status
- Traffic promotion, drain, and rollback actions
- Revision health checks with latency and error-rate observations
- Runtime configuration
- Deployment event history
- Linked monitoring panels

## Inference

Purpose: Operate callable prediction endpoints and inspect request-level behavior.

Capabilities:

- Endpoint launchpad from servable deployment revisions
- Inference endpoint list
- Endpoint selection
- Editable prediction probe payloads
- Request trace review
- Prediction output inspection
- Metric snapshot recording
- Latency and error summaries
- Deployment revision attribution

## Monitoring

Purpose: Observe platform and ML runtime health.

Capabilities:

- API latency and errors
- Training duration and failures
- Inference throughput and latency
- Prediction count
- Endpoint health table
- Endpoint drilldown
- Error-rate and latency budget indicators
- Endpoint risk classification
- Alert rule evaluation
- Endpoint-linked alert context
- Highest-risk endpoint focus
- Feature drift
- Inference errors
- Pipeline failures

## Drift

Purpose: Compare reference distributions against production inference traffic and convert drift signals into retraining decisions.

Capabilities:

- Reference profile creation
- Baseline profile JSON validation
- Profile and endpoint selection
- Drift report execution
- Threshold, report window, sample limit, and report URI controls
- Report detail and drift risk badges
- Feature-level drift score analysis
- Deployment-matched retraining policy handoff
- Drift operation feedback

## Retraining

Purpose: Manage adaptive training loops that convert drift, alert, and operator signals into governed training handoffs.

Capabilities:

- Retraining policy creation
- Deployment-scoped policy selection
- Drift, alert, and manual trigger configuration
- Experiment and training lineage controls
- Dataset version and feature set training sources
- Hyperparameter JSON validation
- Cooldown and daily run guardrails
- Manual retraining trigger
- Pending run approval and rejection
- Selected run decision detail

## Alerts

Purpose: Manage operational incidents and ML quality signals.

Capabilities:

- Alert event list
- Severity filters
- Alert rule creation
- Alert rule metric, threshold, window, and severity controls
- Acknowledge and resolve actions
- Incident lifecycle feedback
- Linked runbook references
- Alert rule management
- Notification channel status

## Settings

Purpose: Manage project and organization-level configuration.

Capabilities:

- Members and roles
- API keys
- Service accounts
- Authenticated account context from `/auth/me`
- Permission groups derived from RBAC grants
- Local browser workspace keys for API token and active project context
- Active project context clearing
- Project defaults
- Retraining policies
- Notification channels
- Audit log access for authorized users

## Frontend Architecture

Frontend state should be separated:

| Concern | Tooling |
| --- | --- |
| Server state | TanStack Query |
| Routing | React Router |
| Forms | React Hook Form or equivalent when introduced |
| Styling | TailwindCSS |
| API types | Generated from OpenAPI when stable |
| E2E tests | Playwright |

## UX Standards

- Data tables should support search, filter, sort, pagination, and empty states.
- Long-running actions should show status and safe retry behavior.
- Destructive or high-risk actions need confirmation and audit records.
- Deployment actions should show the target model version, environment, traffic percentage, and rollback target.
- Error states should show actionable messages and trace IDs.
- Screens should prioritize scannability over marketing-style presentation.
