from forgeml.platform.airflow import (
    AIRFLOW_ORCHESTRATION_SCHEMA_VERSION,
    AirflowDagRunRequest,
    AirflowHttpWorkflowGateway,
    AirflowRestError,
    InMemoryAirflowWorkflowGateway,
)


class FakeAirflowHttpTransport:
    def __init__(self, *, missing: bool = False) -> None:
        self.missing = missing
        self.requests: list[dict[str, object]] = []

    def request_json(self, method, path, *, payload=None):
        self.requests.append(
            {
                "method": method,
                "path": path,
                "payload": payload or {},
            }
        )
        if self.missing:
            raise AirflowRestError(404, "missing DAG run")
        state = "failed" if method == "PATCH" else "queued"
        return {
            "dag_id": "forgeml_training_pipeline",
            "dag_run_id": "forgeml_training__run-1",
            "state": state,
            "run_type": "manual",
            "logical_date": "2026-08-10T23:00:00Z",
            "start_date": None,
            "end_date": None,
            "note": "Triggered by ForgeML.",
            "conf": {
                "schema_version": "forgeml.training_airflow_dag_run.v1",
                "training_run_id": "run-1",
            },
        }


def test_in_memory_airflow_gateway_triggers_polls_and_cancels_dag_run() -> None:
    gateway = InMemoryAirflowWorkflowGateway(base_url="http://airflow.local")
    request = AirflowDagRunRequest(
        dag_id="forgeml_training_pipeline",
        dag_run_id="forgeml_training__run-1",
        conf={"training_run_id": "run-1"},
    )

    created = gateway.trigger_dag_run(request)
    polled = gateway.get_dag_run(
        dag_id=request.dag_id,
        dag_run_id=request.dag_run_id,
    )
    canceled = gateway.cancel_dag_run(
        dag_id=request.dag_id,
        dag_run_id=request.dag_run_id,
        note="Canceled by ForgeML.",
    )

    assert created.state == "queued"
    assert polled.dag_run_id == request.dag_run_id
    assert canceled.state == "failed"
    assert gateway.triggered_requests == [request]
    assert gateway.canceled_runs == [
        (request.dag_id, request.dag_run_id, "Canceled by ForgeML.")
    ]


def test_http_airflow_gateway_uses_stable_rest_dag_run_endpoints() -> None:
    transport = FakeAirflowHttpTransport()
    gateway = AirflowHttpWorkflowGateway(
        base_url="http://airflow.local",
        transport=transport,
    )
    dag_request = AirflowDagRunRequest(
        dag_id="forgeml_training_pipeline",
        dag_run_id="forgeml_training__run-1",
        conf={"training_run_id": "run-1"},
    )

    created = gateway.trigger_dag_run(dag_request)
    polled = gateway.get_dag_run(
        dag_id=dag_request.dag_id,
        dag_run_id=dag_request.dag_run_id,
    )
    canceled = gateway.cancel_dag_run(
        dag_id=dag_request.dag_id,
        dag_run_id=dag_request.dag_run_id,
        note="Canceled by ForgeML.",
    )
    paths = [request["path"] for request in transport.requests]

    assert created.state == "queued"
    assert polled.metadata["schema_version"] == AIRFLOW_ORCHESTRATION_SCHEMA_VERSION
    assert canceled.state == "failed"
    assert paths == [
        "/api/v1/dags/forgeml_training_pipeline/dagRuns",
        "/api/v1/dags/forgeml_training_pipeline/dagRuns/forgeml_training__run-1",
        "/api/v1/dags/forgeml_training_pipeline/dagRuns/forgeml_training__run-1",
    ]
    assert transport.requests[0]["payload"]["dag_run_id"] == "forgeml_training__run-1"
    assert transport.requests[2]["method"] == "PATCH"
    assert transport.requests[2]["payload"]["state"] == "failed"
