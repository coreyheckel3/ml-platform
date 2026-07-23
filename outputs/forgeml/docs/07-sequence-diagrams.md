# Sequence Diagrams

These diagrams define the expected control flow for core ForgeML workflows.

## Authentication

```mermaid
sequenceDiagram
  participant User
  participant UI as React UI
  participant API as FastAPI Auth API
  participant Auth as Auth Application Service
  participant DB as PostgreSQL
  participant Audit as Audit Log

  User->>UI: Submit credentials
  UI->>API: POST /api/v1/auth/login
  API->>Auth: authenticate(email, password)
  Auth->>DB: Load user and password hash
  Auth->>Auth: Verify password and status
  Auth->>DB: Store refresh token hash
  Auth->>Audit: Record login success
  Auth-->>API: Access token and refresh token
  API-->>UI: 200 OK
```

## Dataset Upload, Versioning, and Validation

```mermaid
sequenceDiagram
  participant User
  participant UI as React UI
  participant API as Dataset API
  participant App as Dataset Application Service
  participant DB as PostgreSQL
  participant Obj as Object Storage
  participant Airflow as Airflow Adapter
  participant DAG as Validation DAG

  User->>UI: Create dataset version
  UI->>API: POST /datasets/{id}/versions
  API->>App: create_upload_version(command)
  App->>DB: Insert pending dataset_version
  App->>Obj: Create signed upload URL
  App-->>API: Upload instructions
  API-->>UI: Signed URL and version id
  UI->>Obj: Upload dataset bytes
  UI->>API: POST /dataset-versions/{id}/finalize
  API->>App: finalize_version(command)
  App->>DB: Mark version finalized
  App->>Airflow: Trigger validation DAG
  Airflow->>DAG: Run schema validation
  DAG->>Obj: Read dataset
  DAG->>Obj: Write validation report
  DAG->>DB: Update validation status
```

## Feature Materialization

```mermaid
sequenceDiagram
  participant User
  participant UI
  participant API as Feature API
  participant App as Feature Application Service
  participant DB as PostgreSQL
  participant Airflow
  participant DAG as Materialization DAG
  participant Obj as Object Storage

  User->>UI: Trigger materialization
  UI->>API: POST /feature-pipelines/{id}/materialize
  API->>App: request_materialization(command)
  App->>DB: Create materialization record
  App->>Airflow: Trigger materialization DAG
  Airflow->>DAG: Execute feature pipeline
  DAG->>Obj: Read source dataset/features
  DAG->>Obj: Write offline feature snapshot
  DAG->>DB: Mark materialization completed
  UI->>API: Poll materialization status
  API-->>UI: Completed with offline URI
```

## Training, Evaluation, and Model Registration

```mermaid
sequenceDiagram
  participant User
  participant UI
  participant API as Training API
  participant App as Training Service
  participant DB as PostgreSQL
  participant Airflow
  participant Trainer as Training Worker
  participant MLflow
  participant Obj as Object Storage
  participant Registry as Model Registry Service

  User->>UI: Launch training run
  UI->>API: POST /projects/{id}/training-runs
  API->>App: start_training_run(command)
  App->>DB: Insert experiment_run and training_run
  App->>Airflow: Trigger training DAG
  Airflow->>Trainer: Start training task
  Trainer->>Obj: Load dataset and features
  Trainer->>MLflow: Start run and log params
  Trainer->>Trainer: Train model
  Trainer->>MLflow: Log metrics and artifacts
  Trainer->>Obj: Write evaluation report
  Trainer->>DB: Mark training completed
  User->>UI: Register model from run
  UI->>API: POST /model-versions/from-training-run
  API->>Registry: register_model_version(command)
  Registry->>DB: Create model_version and lineage
```

## Model Approval and Canary Deployment

```mermaid
sequenceDiagram
  participant Reviewer
  participant UI
  participant API as Registry and Deployment APIs
  participant Registry as Model Registry Service
  participant Deploy as Deployment Service
  participant DB as PostgreSQL
  participant Runtime as Inference Runtime
  participant Metrics as Prometheus

  Reviewer->>UI: Approve model version
  UI->>API: POST /model-approvals/{id}/approve
  API->>Registry: approve_model_version(command)
  Registry->>DB: Mark model version approved
  Reviewer->>UI: Start canary rollout
  UI->>API: POST /deployment-revisions/{id}/rollout
  API->>Deploy: start_rollout(command)
  Deploy->>DB: Create rollout event at 5 percent
  Deploy->>Runtime: Apply routing config
  Runtime->>Metrics: Emit latency, errors, prediction count
  Deploy->>DB: Record rollout status
```

## Online Inference and Monitoring

```mermaid
sequenceDiagram
  participant Client
  participant API as FastAPI Inference API
  participant App as Inference Service
  participant DB as PostgreSQL
  participant Runtime as Runtime Adapter
  participant Metrics as Prometheus

  Client->>API: POST /api/v1/inference-endpoints/{endpoint_id}/predict
  API->>App: predict(command)
  App->>DB: Load endpoint and deployment revision reference
  App->>App: Validate endpoint status, revision health, traffic, and payload
  App->>Runtime: Predict(reference, payload)
  Runtime-->>App: Prediction payload and latency
  App->>DB: Insert immutable inference_request_log
  API-->>Client: Prediction response with request and revision metadata
  API->>Metrics: Record route latency and status code
```

## Drift Detection and Automated Retraining

```mermaid
sequenceDiagram
  participant User
  participant API as Drift API
  participant App as Drift Service
  participant DB as PostgreSQL
  participant Analyzer as Drift Analyzer
  participant Retrain as Retraining Service
  participant Training as Training Service

  User->>API: POST /api/v1/drift-profiles/{id}/reports
  API->>App: run_report(command)
  App->>DB: Load drift profile and inference endpoint
  App->>DB: Load recent successful inference request payloads
  App->>Analyzer: Compare baseline profile to production samples
  Analyzer-->>App: Drift score and feature results
  App->>DB: Store drift_report and drift_feature_results
  App-->>API: Completed report
  API-->>User: Drift report
  User->>API: POST /api/v1/retraining-policies/{id}/evaluate
  API->>Retrain: evaluate_policy(drift_report_id)
  Retrain->>DB: Load policy, drift report, prior runs, and guardrail counters
  alt Policy threshold and guardrails pass with approval required
    Retrain->>DB: Insert retraining_run pending_approval
    API-->>User: Pending approval decision
  else Policy threshold and guardrails pass without approval
    Retrain->>Training: launch_training_run(training_template)
    Training->>DB: Insert experiment_run and training_run
    Retrain->>DB: Insert retraining_run queued with training_run_id
    API-->>User: Queued retraining run
  else Trigger skipped
    Retrain->>DB: Insert skipped retraining_run audit record
    API-->>User: Skipped decision with reason
  end
```

## Alert Rule Evaluation

```mermaid
sequenceDiagram
  participant Operator
  participant API as Alerting API
  participant Alert as Alerting Service
  participant DB as PostgreSQL
  participant Monitoring as Inference Metric Snapshot

  Operator->>API: POST /api/v1/alert-rules/{rule_id}/evaluate
  API->>Alert: evaluate_rule(command)
  Alert->>DB: Load alert rule
  Alert->>Monitoring: Load latest endpoint metric snapshot
  Alert->>Alert: Compare observed value with threshold
  alt condition triggered and no open event exists
    Alert->>DB: Insert alert_event
  else existing open event
    Alert->>DB: Return existing alert_event
  end
  API-->>Operator: Evaluation result with optional event
```

## Rollback

```mermaid
sequenceDiagram
  participant Operator
  participant UI
  participant API as Deployment API
  participant Deploy as Deployment Service
  participant DB as PostgreSQL
  participant Runtime as Inference Runtime
  participant Metrics as Prometheus

  Operator->>UI: Request rollback
  UI->>API: POST /deployments/{id}/rollback
  API->>Deploy: rollback(command)
  Deploy->>DB: Find last healthy revision
  Deploy->>Runtime: Route traffic to prior revision
  Runtime->>Metrics: Emit rollout metrics
  Deploy->>DB: Record rollback event
  API-->>UI: Rollback accepted
```
