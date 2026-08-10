from datetime import UTC, datetime
from uuid import uuid4

from forgeml.platform.mlflow import (
    MLFLOW_TRACKING_SYNC_SCHEMA_VERSION,
    InMemoryMLflowTrackingGateway,
    MLflowHttpTrackingGateway,
    MLflowRestError,
    build_training_run_mlflow_record,
    mlflow_sync_result_payload,
)


class FakeMLflowHttpTransport:
    def __init__(self, *, experiment_exists: bool = True) -> None:
        self.experiment_exists = experiment_exists
        self.requests: list[dict[str, object]] = []

    def request_json(self, method, path, *, query=None, payload=None):
        self.requests.append(
            {
                "method": method,
                "path": path,
                "query": query or {},
                "payload": payload or {},
            }
        )
        if path.endswith("/experiments/get-by-name"):
            if not self.experiment_exists:
                raise MLflowRestError(404, "missing experiment")
            return {"experiment": {"experiment_id": "12"}}
        if path.endswith("/experiments/create"):
            return {"experiment_id": "13"}
        if path.endswith("/runs/create"):
            return {"run": {"info": {"run_id": "mlflow-run-1"}}}
        if path.endswith("/runs/log-batch") or path.endswith("/runs/update"):
            return {}
        raise AssertionError(f"Unexpected MLflow path: {path}")


def test_build_training_run_mlflow_record_extracts_lineage_and_artifacts() -> None:
    organization_id = uuid4()
    project_id = uuid4()
    experiment_id = uuid4()
    experiment_run_id = uuid4()
    training_run_id = uuid4()
    completed_at = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)

    record = build_training_run_mlflow_record(
        experiment_prefix="forgeml-prod",
        organization_id=organization_id,
        project_id=project_id,
        experiment_id=experiment_id,
        experiment_run_id=experiment_run_id,
        training_run_id=training_run_id,
        run_name="fraud-xgb-depth-6",
        status="succeeded",
        started_at=completed_at,
        completed_at=completed_at,
        artifact_uri="s3://forgeml-artifacts/training-runs/run-1",
        algorithm="xgboost",
        model_type="xgboost",
        objective_metric_name="auc",
        parameters={"max_depth": 6, "class_weights": {"fraud": 10}},
        metrics={"auc": 0.95, "nan_metric": float("nan")},
        evaluation_report={
            "training_execution": {
                "artifacts": [
                    {
                        "name": "model",
                        "artifact_type": "model",
                        "uri": "file:///tmp/model.json",
                        "media_type": "application/json",
                        "metadata": {"sha256": "sha256:abc", "size_bytes": 128},
                    }
                ]
            }
        },
    )

    assert record.experiment_name.startswith("forgeml-prod/organizations/")
    assert record.run_name == "fraud-xgb-depth-6"
    assert record.parameters["max_depth"] == "6"
    assert record.parameters["class_weights"] == '{"fraud": 10}'
    assert record.metrics == {"auc": 0.95}
    assert record.tags["forgeml.training_run_id"] == str(training_run_id)
    assert record.artifacts[0].uri == "file:///tmp/model.json"


def test_in_memory_mlflow_gateway_records_run_and_payload_shape() -> None:
    record = _minimal_record()
    gateway = InMemoryMLflowTrackingGateway()

    result = gateway.sync_training_run(record)
    payload = mlflow_sync_result_payload(result)

    assert gateway.records == (record,)
    assert result.run_id == f"in-memory:{record.training_run_id}"
    assert payload["schema_version"] == MLFLOW_TRACKING_SYNC_SCHEMA_VERSION
    assert payload["status"] == "synced"
    assert payload["logged_metric_count"] == 1


def test_http_mlflow_gateway_logs_params_metrics_artifact_references_and_status() -> None:
    transport = FakeMLflowHttpTransport()
    gateway = MLflowHttpTrackingGateway(
        tracking_uri="http://mlflow.internal",
        transport=transport,
    )

    result = gateway.sync_training_run(_minimal_record())

    paths = [request["path"] for request in transport.requests]
    log_batch = next(
        request for request in transport.requests if request["path"].endswith("/runs/log-batch")
    )
    update = next(
        request for request in transport.requests if request["path"].endswith("/runs/update")
    )
    tags = {tag["key"]: tag["value"] for tag in log_batch["payload"]["tags"]}

    assert result.run_id == "mlflow-run-1"
    assert paths == [
        "/api/2.0/mlflow/experiments/get-by-name",
        "/api/2.0/mlflow/runs/create",
        "/api/2.0/mlflow/runs/log-batch",
        "/api/2.0/mlflow/runs/update",
    ]
    assert log_batch["payload"]["params"][0]["key"] == "algorithm"
    assert log_batch["payload"]["metrics"][0]["key"] == "auc"
    assert tags["forgeml.artifact.model.uri"] == "file:///tmp/model.json"
    assert update["payload"]["status"] == "FINISHED"


def test_http_mlflow_gateway_creates_missing_experiment() -> None:
    transport = FakeMLflowHttpTransport(experiment_exists=False)
    gateway = MLflowHttpTrackingGateway(
        tracking_uri="http://mlflow.internal",
        transport=transport,
    )

    result = gateway.sync_training_run(_minimal_record())

    paths = [request["path"] for request in transport.requests]
    assert result.run_id == "mlflow-run-1"
    assert "/api/2.0/mlflow/experiments/create" in paths


def _minimal_record():
    now = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    return build_training_run_mlflow_record(
        experiment_prefix="forgeml",
        organization_id=uuid4(),
        project_id=uuid4(),
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        training_run_id=uuid4(),
        run_name="fraud-xgb",
        status="succeeded",
        started_at=now,
        completed_at=now,
        artifact_uri="s3://forgeml-artifacts/training-runs/run-1",
        algorithm="xgboost",
        model_type="xgboost",
        objective_metric_name="auc",
        parameters={"algorithm": "xgboost"},
        metrics={"auc": 0.94},
        evaluation_report={
            "training_execution": {
                "artifacts": [
                    {
                        "name": "model",
                        "artifact_type": "model",
                        "uri": "file:///tmp/model.json",
                        "media_type": "application/json",
                        "metadata": {"sha256": "sha256:model"},
                    }
                ]
            }
        },
    )
