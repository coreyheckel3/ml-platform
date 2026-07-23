# API Specification

ForgeML exposes a versioned REST API under `/api/v1`. The API is resource-oriented, project-scoped where appropriate, and designed for both the web application and automation clients.

## API Principles

- JSON request and response bodies.
- UUID identifiers.
- Cursor pagination for list endpoints.
- Idempotency keys for create and workflow-trigger endpoints.
- Problem Details style error responses.
- JWT bearer authentication.
- Project-scoped authorization enforced in application services.
- OpenAPI generated from FastAPI and checked into `contracts/openapi`.

## Common Conventions

### Pagination

List endpoints accept:

| Parameter | Description |
| --- | --- |
| `limit` | Maximum records, default 50, max 200 |
| `cursor` | Opaque cursor from prior response |
| `sort` | Stable sort key when supported |

Response:

```json
{
  "items": [],
  "next_cursor": null
}
```

### Error Shape

```json
{
  "type": "https://forgeml.dev/errors/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "Dataset schema is incompatible with the requested training run.",
  "trace_id": "01HV...",
  "errors": []
}
```

### Idempotency

Mutating endpoints that create workflows accept:

```http
Idempotency-Key: <client-generated-key>
```

## Authentication

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/login` | Exchange credentials for access and refresh tokens |
| `POST` | `/auth/refresh` | Refresh access token |
| `POST` | `/auth/logout` | Revoke refresh token |
| `GET` | `/auth/me` | Return current user, organizations, roles, permissions |
| `POST` | `/auth/api-keys` | Create API key |
| `GET` | `/auth/api-keys` | List API keys for current principal |
| `DELETE` | `/auth/api-keys/{api_key_id}` | Revoke API key |

## Projects

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects` | Create project |
| `GET` | `/projects` | List visible projects |
| `GET` | `/projects/{project_id}` | Get project |
| `PATCH` | `/projects/{project_id}` | Update project metadata |
| `POST` | `/projects/{project_id}/archive` | Archive project |
| `GET` | `/projects/{project_id}/activity` | Project activity feed |
| `GET` | `/projects/{project_id}/settings` | Get project settings |
| `PUT` | `/projects/{project_id}/settings/{key}` | Update project setting |

## Datasets

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/datasets` | Create dataset |
| `GET` | `/projects/{project_id}/datasets` | List datasets |
| `GET` | `/datasets/{dataset_id}` | Get dataset |
| `POST` | `/datasets/{dataset_id}/versions` | Create dataset version upload record |
| `GET` | `/datasets/{dataset_id}/versions` | List dataset versions |
| `GET` | `/dataset-versions/{version_id}` | Get dataset version |
| `POST` | `/dataset-versions/{version_id}/finalize` | Finalize object upload and lock the immutable version |
| `POST` | `/dataset-versions/{version_id}/validate` | Trigger schema validation workflow |
| `GET` | `/dataset-versions/{version_id}/validation-runs` | List validation runs |
| `GET` | `/dataset-validation-runs/{run_id}` | Get validation status and report URI |
| `POST` | `/dataset-versions/{version_id}/profile` | Trigger dataset profiling |

Dataset upload should use signed object-storage URLs:

1. Client requests a dataset version upload record.
2. API returns a signed upload URL and expected object metadata.
3. Client uploads directly to object storage.
4. Client finalizes the version.
5. API triggers validation.

## Feature Store

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/feature-sets` | Create feature set |
| `GET` | `/projects/{project_id}/feature-sets` | List feature sets |
| `GET` | `/feature-sets/{feature_set_id}` | Get feature set |
| `POST` | `/feature-sets/{feature_set_id}/features` | Register feature definitions |
| `POST` | `/feature-sets/{feature_set_id}/pipelines` | Register feature pipeline |
| `POST` | `/feature-pipelines/{pipeline_id}/materialize` | Trigger materialization |
| `GET` | `/feature-sets/{feature_set_id}/materializations` | List materializations |
| `GET` | `/feature-sets/{feature_set_id}/lineage` | Get feature lineage |

## Experiments

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/experiments` | Create experiment |
| `GET` | `/projects/{project_id}/experiments` | List experiments |
| `GET` | `/experiments/{experiment_id}` | Get experiment |
| `GET` | `/experiments/{experiment_id}/runs` | List runs |
| `GET` | `/experiment-runs/{run_id}` | Get run details |
| `GET` | `/experiment-runs/{run_id}/metrics` | Get metrics |
| `GET` | `/experiment-runs/{run_id}/artifacts` | List artifacts |
| `GET` | `/experiment-runs/{run_id}/evaluation-report` | Get evaluation report |

## Training

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/training-runs` | Start training run |
| `GET` | `/projects/{project_id}/training-runs` | List training runs |
| `GET` | `/training-runs/{training_run_id}` | Get training run |
| `POST` | `/training-runs/{training_run_id}/result` | Record terminal result |
| `POST` | `/training-runs/{training_run_id}/cancel` | Cancel run |
| `GET` | `/training-runs/{training_run_id}/events` | List lifecycle events |
| `POST` | `/projects/{project_id}/hyperparameter-searches` | Start tuning workflow |

Training job request:

```json
{
  "experiment_id": "uuid",
  "dataset_version_id": "uuid",
  "algorithm": "xgboost",
  "objective": "binary_classification",
  "training_config": {
    "target_column": "is_fraud",
    "parameters": {
      "max_depth": 6,
      "learning_rate": 0.05
    }
  }
}
```

## Model Registry

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/models` | Create registered model |
| `GET` | `/projects/{project_id}/models` | List registered models |
| `GET` | `/models/{model_id}` | Get registered model |
| `POST` | `/models/{model_id}/versions` | Register model version from a succeeded training run reference |
| `POST` | `/models/{model_id}/versions/promote-training-run` | Promote a succeeded training run after validating its execution manifest |
| `GET` | `/models/{model_id}/versions` | List model versions |
| `GET` | `/model-versions/{version_id}` | Get model version |
| `POST` | `/model-versions/{version_id}/approval-request` | Request approval |
| `POST` | `/model-versions/{version_id}/review` | Approve or reject model version |
| `GET` | `/model-versions/{version_id}/approvals` | List approval decisions |
| `GET` | `/model-versions/{version_id}/lineage` | Get model lineage |

## Deployments

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/deployments` | Create deployment target |
| `GET` | `/projects/{project_id}/deployments` | List deployments |
| `GET` | `/deployments/{deployment_id}` | Get deployment |
| `POST` | `/deployments/{deployment_id}/revisions` | Create deployment revision |
| `POST` | `/deployment-revisions/{revision_id}/rollout` | Start rollout |
| `POST` | `/deployment-revisions/{revision_id}/promote` | Promote canary to full traffic |
| `POST` | `/deployments/{deployment_id}/rollback` | Roll back to prior healthy revision |
| `GET` | `/deployments/{deployment_id}/events` | Get rollout events |
| `GET` | `/deployments/{deployment_id}/health` | Get deployment health |

## Inference

Inference endpoints are project scoped and bind to a specific deployment revision. This keeps
prediction logs attributable to the exact model version and serving configuration used for a
request.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/inference-endpoints` | Create inference endpoint for a deployment revision |
| `GET` | `/projects/{project_id}/inference-endpoints` | List project inference endpoints |
| `GET` | `/inference-endpoints/{endpoint_id}` | Get inference endpoint metadata |
| `POST` | `/inference-endpoints/{endpoint_id}/predict` | Run online prediction through the endpoint runtime |
| `GET` | `/inference-endpoints/{endpoint_id}/requests` | List immutable prediction request logs |
| `POST` | `/inference-endpoints/{endpoint_id}/metric-snapshots` | Record aggregated prediction, error, and latency metrics |
| `GET` | `/inference-endpoints/{endpoint_id}/metric-snapshots` | List endpoint metric snapshots |

Prediction response:

```json
{
  "log_id": "uuid",
  "endpoint_id": "uuid",
  "deployment_revision_id": "uuid",
  "request_id": "01HV...",
  "status": "succeeded",
  "latency_ms": 23.4,
  "output_payload": {}
}
```

## Monitoring

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/projects/{project_id}/monitoring/summary` | Project inference, error, latency, and active alert summary |
| `GET` | `/projects/{project_id}/monitoring/inference-endpoints` | Per-endpoint prediction, request, error-rate, and latency summaries |

## Drift Detection

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/drift-profiles` | Create reference profile |
| `GET` | `/projects/{project_id}/drift-profiles` | List reference profiles |
| `POST` | `/drift-profiles/{profile_id}/reports` | Run drift analysis for an inference endpoint |
| `GET` | `/drift-profiles/{profile_id}/reports` | List drift reports for a profile |
| `GET` | `/projects/{project_id}/drift-reports` | List project drift reports |
| `GET` | `/drift-reports/{report_id}/features` | List feature-level drift results |

## Alerting

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/alert-rules` | Create alert rule |
| `GET` | `/projects/{project_id}/alert-rules` | List alert rules |
| `POST` | `/alert-rules/{rule_id}/evaluate` | Evaluate a rule against an inference endpoint snapshot |
| `GET` | `/projects/{project_id}/alert-events` | List alert events |
| `POST` | `/alert-events/{event_id}/acknowledge` | Acknowledge alert |
| `POST` | `/alert-events/{event_id}/resolve` | Resolve alert |

## Retraining

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/projects/{project_id}/retraining-policies` | Create deployment-scoped retraining policy |
| `GET` | `/projects/{project_id}/retraining-policies` | List retraining policies |
| `POST` | `/retraining-policies/{policy_id}/evaluate` | Evaluate drift or alert trigger |
| `POST` | `/retraining-policies/{policy_id}/trigger` | Manually trigger retraining |
| `GET` | `/projects/{project_id}/retraining-runs` | List retraining runs |
| `GET` | `/retraining-runs/{run_id}` | Get retraining run |
| `POST` | `/retraining-runs/{run_id}/approve` | Approve pending retraining run and launch training |
| `POST` | `/retraining-runs/{run_id}/reject` | Reject pending retraining run |

## Administration

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/admin/audit-log` | Search audit events |
| `GET` | `/admin/users` | List users |
| `POST` | `/admin/users` | Invite or create user |
| `PATCH` | `/admin/users/{user_id}` | Update user |
| `GET` | `/admin/roles` | List roles |
| `POST` | `/admin/roles` | Create custom role |
| `GET` | `/admin/system/status` | Platform system status |
| `GET` | `/admin/feature-flags` | List feature flags |

## Realtime Updates

The initial implementation should use polling through TanStack Query for job and deployment status. Server-Sent Events can be added for high-volume status screens after the API contracts stabilize.
