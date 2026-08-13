# ForgeML Architecture Diagrams

These diagrams are intended for technical walkthroughs. They complement
`docs/architecture-walkthrough.md` with compact visuals that can be pasted into
GitHub Markdown, a portfolio site, or interview notes.

## Modular Monolith

```mermaid
flowchart LR
  UI["React Operations Console"] --> API["FastAPI Modular Monolith"]
  API --> Auth["Authentication"]
  API --> Projects["Projects"]
  API --> Data["Datasets"]
  API --> Features["Feature Store"]
  API --> Training["Training"]
  API --> Registry["Model Registry"]
  API --> Deployments["Deployments"]
  API --> Inference["Inference"]
  API --> Monitoring["Monitoring"]
  API --> Retraining["Retraining"]
  API --> Admin["Administration"]
  Auth --> DB[("PostgreSQL")]
  Projects --> DB
  Data --> DB
  Features --> DB
  Training --> DB
  Registry --> DB
  Deployments --> DB
  Inference --> DB
  Monitoring --> DB
  Retraining --> DB
  Admin --> DB
  API --> Redis[("Redis")]
  API --> Metrics["Prometheus Metrics"]
```

## ML Lifecycle

```mermaid
sequenceDiagram
  participant Engineer
  participant UI as React Console
  participant API as FastAPI Control Plane
  participant Store as Artifact Store
  participant Runner as Training Runner
  participant Registry as Model Registry
  participant Runtime as Serving Runtime
  Engineer->>UI: Register dataset and feature metadata
  UI->>API: Create dataset version and feature set
  API->>Store: Write manifest metadata and checksums
  Engineer->>UI: Start training run
  UI->>API: Queue run with lineage references
  API->>Runner: Dispatch through adapter boundary
  Runner->>Store: Persist model and evaluation artifacts
  Runner->>API: Record metrics and artifact manifest
  Engineer->>UI: Promote and approve model version
  UI->>Registry: Promotion and approval requests
  Engineer->>UI: Deploy approved version
  UI->>Runtime: Create revision, probe health, shift traffic
```

## Monitoring To Retraining

```mermaid
flowchart TD
  Endpoint["Inference Endpoint"] --> Logs["Request Logs"]
  Endpoint --> Snapshots["Metric Snapshots"]
  Logs --> Drift["Drift Report"]
  Snapshots --> Alerts["Alert Evaluation"]
  Drift --> Policy["Retraining Policy"]
  Alerts --> Policy
  Policy --> Guardrails["Cooldowns, Daily Limits, Idempotency"]
  Guardrails --> TrainingRun["Queued Training Run"]
  TrainingRun --> Registry["Model Registry"]
```

## Release Governance

```mermaid
flowchart LR
  Source["Source Commit"] --> CI["GitHub Actions"]
  CI --> Tests["Tests and Contract Gates"]
  CI --> Docker["Docker Builds"]
  Tests --> Readiness["Production Readiness"]
  Docker --> Manifest["Release Manifest"]
  Readiness --> Manifest
  Manifest --> Verify["Manifest Verification"]
  Verify --> Evidence["Published Release Evidence"]
```
