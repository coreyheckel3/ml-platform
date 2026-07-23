# Monitoring Strategy

ForgeML should be observable from the first implementation sprint. Monitoring must cover platform health, workflow execution, training, inference, drift, and user-visible reliability.

## Observability Stack

| Component | Purpose |
| --- | --- |
| OpenTelemetry | Traces and structured instrumentation |
| Prometheus | Metrics collection and alert evaluation |
| Grafana | Dashboards |
| Structured JSON logs | Searchable operational events |
| Audit log | Security and compliance history |

## Metric Categories

### API Metrics

- Request count
- Request latency
- Error count
- Error rate
- Rate-limited request count
- Auth failures
- Database query latency
- External adapter latency

### Infrastructure Metrics

- CPU utilization
- Memory utilization
- Container restarts
- Pod readiness
- Database connections
- Database lock waits
- Redis memory and connection count
- Object storage request failures

### Training Metrics

- Training job count
- Training time
- Training failures
- Queue wait time
- Dataset load time
- Feature materialization time
- Hyperparameter trial count
- Evaluation metric summaries

### Inference Metrics

- Prediction count
- Prediction latency
- Inference errors
- Request log count
- Metric snapshot freshness
- Model load failures
- Request validation failures
- Canary traffic percentage
- Rollback count
- Per-model and per-deployment throughput

### Drift Metrics

- Feature drift score
- Prediction drift score
- Number of drifted features
- Drift report failures
- Reference profile age
- Retraining trigger count

Implemented drift APIs persist reference profiles, drift reports, and feature-level drift scores.
The current local analyzer compares baseline numeric and categorical feature summaries against
recent successful inference request payloads.
Implemented retraining APIs persist deployment-scoped policies, trigger evaluations, approval
decisions, guardrail skips, and links to launched training runs.

### Pipeline Metrics

- Pipeline success count
- Pipeline failure count
- Pipeline duration
- Retry count
- Backfill count
- Task-level failure count

## Metric Naming

Metric names should be stable and low-cardinality:

| Metric | Type | Labels |
| --- | --- | --- |
| `forgeml_api_request_duration_seconds` | Histogram | `route`, `method`, `status_code` |
| `forgeml_api_requests_total` | Counter | `route`, `method`, `status_code` |
| `forgeml_training_job_duration_seconds` | Histogram | `project_id`, `algorithm`, `status` |
| `forgeml_model_promotions_total` | Counter | `status` |
| `forgeml_pipeline_failures_total` | Counter | `pipeline_type`, `project_id` |
| `forgeml_inference_predictions_total` | Counter | `deployment_id`, `model_version_id` |
| `forgeml_inference_request_duration_seconds` | Histogram | `deployment_id`, `model_version_id` |
| `forgeml_inference_errors_total` | Counter | `deployment_id`, `error_type` |
| `forgeml_drift_score` | Gauge | `deployment_id`, `drift_type` |
| `forgeml_feature_drift_score` | Gauge | `deployment_id`, `feature_name` |
| `forgeml_retraining_triggers_total` | Counter | `deployment_id`, `trigger_type` |

High-cardinality labels such as raw user IDs, request IDs, dataset version IDs, and arbitrary feature values should not be used in Prometheus metrics.

## Logging

All services should emit structured JSON logs with:

- Timestamp
- Level
- Service name
- Environment
- Trace ID
- Request ID
- Actor ID where safe
- Project ID where relevant
- Event name
- Error type and stack for failures

Sensitive data must not be logged:

- Passwords
- Tokens
- API keys
- Raw prediction payloads unless explicitly sampled and redacted
- Secrets

## Tracing

Trace these flows:

- API request through application service and repository
- Dataset upload finalization through validation workflow trigger
- Training job creation through Airflow DAG trigger
- Model registration through MLflow lookup
- Deployment rollout through runtime update
- Inference request through model prediction

## Dashboards

### Executive Dashboard

- Active projects
- Training jobs by status
- Deployments by health
- Alert count by severity
- Prediction volume
- Drift incidents

### Platform Operations Dashboard

- API latency and errors
- Database latency and connections
- Redis health
- Airflow DAG success/failure
- Worker queue depth
- Container restarts

### ML Engineering Dashboard

- Training duration
- Training failures
- Experiment metric comparison
- Model approval status
- Deployment rollout status
- Drift report summaries

### Inference Dashboard

- Prediction throughput
- p50, p95, p99 latency
- Error rate
- Request validation failures
- Canary performance comparison
- Rollback events

Implemented dashboard APIs provide project-level inference summaries and per-endpoint summaries
from the control-plane database. Prometheus remains the source for low-level API route metrics.
Sprint 12 adds Prometheus scrape configuration and Grafana provisioning under
`infra/observability`. The local `full` Compose profile mounts the dashboard
and datasource configuration automatically.

## Alerting

Initial alert rules:

| Alert | Condition | Severity |
| --- | --- | --- |
| API high error rate | 5xx rate exceeds threshold for 5 minutes | Critical |
| API high latency | p95 exceeds SLO for 10 minutes | Warning |
| API rate limiting spike | Rate-limited requests exceed baseline for 5 minutes | Warning |
| Training failure spike | Failed jobs exceed threshold in 30 minutes | Warning |
| Inference high error rate | Error rate exceeds threshold for deployment | Critical |
| Inference high latency | p95 exceeds deployment SLO | Warning |
| Drift detected | Drift score exceeds configured threshold | Warning |
| Airflow DAG failures | Critical DAG fails repeatedly | Critical |
| Database connection pressure | Connection usage exceeds threshold | Critical |

## SLO Candidates

Initial SLOs should be conservative:

| Capability | SLO |
| --- | --- |
| API availability | 99.5 percent monthly |
| API p95 latency | Under 500 ms for metadata reads |
| Inference availability | 99.5 percent monthly per production deployment |
| Inference p95 latency | Deployment-specific, default under 300 ms for lightweight models |
| Training workflow dispatch | 99 percent of accepted jobs scheduled within 2 minutes |

## Runbooks

Required runbooks:

- API error rate spike
- Database migration failure
- Failed training workflow
- Airflow scheduler unhealthy
- Inference deployment unhealthy
- Canary rollback
- Drift alert investigation
- Object storage access failure
- Redis unavailable
