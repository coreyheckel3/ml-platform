# ForgeML MLflow Contracts

This directory contains the checked-in integration contract for syncing ForgeML
training runs into MLflow.

`mlflow-tracking.v1.json` defines the gateway boundary, REST endpoints, required
lineage tags, artifact-reference logging policy, sync report payload, and CI gates
that keep the adapter aligned with the training lifecycle.
