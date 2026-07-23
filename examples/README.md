# ForgeML Example Projects

Sprint 11 adds three reference workloads that exercise ForgeML as a platform rather than as a single-model app:

- Movie Recommendation
- Semantic Search
- Fraud Detection

Each project includes a manifest, fixture dataset, evaluation report, feature metadata, model registry metadata, deployment contract, inference samples, drift profile, alert rule, and retraining policy.

## Layout

```text
examples/
  catalog.json
  projects/
    movie_recommendation/
    semantic_search/
    fraud_detection/
```

The catalog points at each `project.json` manifest. The SDK validates these manifests with `ml.libraries.forgeml_sdk.examples`.

## Bootstrap Command

Start the backend with seeded local auth data, then run:

```bash
PYTHONPATH=. .venv/bin/python scripts/examples/bootstrap_examples.py
```

The script logs in as `admin@forgeml.dev`, then creates or reuses:

- project
- dataset and dataset version
- feature set, feature definitions, and feature pipeline
- experiment and succeeded training run
- registered model and approved model version
- deployment, revision, health check, and inference endpoint
- prediction logs and metric snapshot
- drift profile and report
- alert rule and evaluated alert signal
- retraining policy and evaluated retraining run

Run a single workload by slug:

```bash
PYTHONPATH=. .venv/bin/python scripts/examples/bootstrap_examples.py --project fraud-detection
```

The bootstrapper is idempotent by name or deterministic content hash, so repeated runs refresh runtime signals without duplicating long-lived catalog objects.
