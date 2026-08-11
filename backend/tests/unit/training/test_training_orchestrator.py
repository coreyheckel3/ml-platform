from uuid import uuid4

from forgeml.modules.training.domain.entities import TrainingRun, TrainingRunStatus
from forgeml.modules.training.infrastructure.orchestrator import (
    AirflowTrainingWorkflowOrchestrator,
    LocalTrainingWorkflowOrchestrator,
    TrainingAirflowOrchestratorConfig,
    map_airflow_state_to_training_status,
    parse_training_airflow_orchestrator_run_id,
    training_airflow_conf,
    training_airflow_dag_run_id,
)
from forgeml.platform.airflow import AirflowDagRunRecord, AirflowDagRunRequest


class FakeAirflowWorkflowGateway:
    def __init__(self, state: str = "queued") -> None:
        self.state = state
        self.requests: list[AirflowDagRunRequest] = []
        self.canceled: list[tuple[str, str, str]] = []

    def trigger_dag_run(self, request: AirflowDagRunRequest) -> AirflowDagRunRecord:
        self.requests.append(request)
        return AirflowDagRunRecord(
            dag_id=request.dag_id,
            dag_run_id=request.dag_run_id,
            state=self.state,
            external_url=f"http://airflow.local/dags/{request.dag_id}/grid",
            conf=request.conf,
            metadata={"run_type": "manual"},
            observed_at=_observed_at(),
        )

    def get_dag_run(self, *, dag_id: str, dag_run_id: str) -> AirflowDagRunRecord:
        return AirflowDagRunRecord(
            dag_id=dag_id,
            dag_run_id=dag_run_id,
            state=self.state,
            external_url=f"http://airflow.local/dags/{dag_id}/grid",
            conf={"schema_version": "forgeml.training_airflow_dag_run.v1"},
            metadata={"run_type": "manual"},
            observed_at=_observed_at(),
        )

    def cancel_dag_run(self, *, dag_id: str, dag_run_id: str, note: str) -> AirflowDagRunRecord:
        self.canceled.append((dag_id, dag_run_id, note))
        return self.get_dag_run(dag_id=dag_id, dag_run_id=dag_run_id)


def test_local_training_orchestrator_reports_current_training_status() -> None:
    training_run = _training_run(status=TrainingRunStatus.RUNNING)
    orchestrator = LocalTrainingWorkflowOrchestrator()

    status = orchestrator.get_training_status(training_run)

    assert status.orchestrator == "local"
    assert status.external_status == "running"
    assert status.mapped_training_status == TrainingRunStatus.RUNNING
    assert status.is_terminal is False


def test_airflow_training_orchestrator_triggers_versioned_training_dag_conf() -> None:
    gateway = FakeAirflowWorkflowGateway()
    orchestrator = AirflowTrainingWorkflowOrchestrator(
        gateway=gateway,
        config=TrainingAirflowOrchestratorConfig(dag_id="forgeml_training_pipeline"),
    )
    training_run = _training_run(status=TrainingRunStatus.QUEUED)

    orchestrator_run_id = orchestrator.trigger_training(training_run)

    assert orchestrator_run_id == (
        f"airflow://forgeml_training_pipeline/{training_airflow_dag_run_id(training_run.id)}"
    )
    assert gateway.requests[0].dag_id == "forgeml_training_pipeline"
    assert gateway.requests[0].conf["schema_version"] == "forgeml.training_airflow_dag_run.v1"
    assert gateway.requests[0].conf["training_run_id"] == str(training_run.id)
    assert gateway.requests[0].conf["artifact_uri"] == training_run.artifact_uri


def test_airflow_training_orchestrator_polls_and_maps_external_status() -> None:
    gateway = FakeAirflowWorkflowGateway(state="success")
    orchestrator = AirflowTrainingWorkflowOrchestrator(
        gateway=gateway,
        config=TrainingAirflowOrchestratorConfig(dag_id="forgeml_training_pipeline"),
    )
    training_run = _training_run(
        status=TrainingRunStatus.RUNNING,
        orchestrator_run_id="airflow://forgeml_training_pipeline/forgeml_training__run-1",
    )

    status = orchestrator.get_training_status(training_run)

    assert status.external_status == "success"
    assert status.mapped_training_status == TrainingRunStatus.SUCCEEDED
    assert status.is_terminal is True
    assert status.metadata["dag_id"] == "forgeml_training_pipeline"
    assert status.metadata["dag_run_id"] == "forgeml_training__run-1"


def test_airflow_training_orchestrator_cancels_external_dag_run() -> None:
    gateway = FakeAirflowWorkflowGateway(state="running")
    orchestrator = AirflowTrainingWorkflowOrchestrator(
        gateway=gateway,
        config=TrainingAirflowOrchestratorConfig(dag_id="forgeml_training_pipeline"),
    )
    training_run = _training_run(
        status=TrainingRunStatus.RUNNING,
        orchestrator_run_id="airflow://forgeml_training_pipeline/forgeml_training__run-1",
    )

    returned = orchestrator.cancel_training(training_run)

    assert returned == training_run.orchestrator_run_id
    assert gateway.canceled == [
        (
            "forgeml_training_pipeline",
            "forgeml_training__run-1",
            f"Canceled by ForgeML for training run {training_run.id}.",
        )
    ]


def test_training_airflow_conf_and_state_mapping_are_deterministic() -> None:
    training_run = _training_run(status=TrainingRunStatus.QUEUED)
    conf = training_airflow_conf(training_run)

    assert conf["schema_version"] == "forgeml.training_airflow_dag_run.v1"
    assert conf["organization_id"] == str(training_run.organization_id)
    assert conf["dataset_version_id"] == str(training_run.dataset_version_id)
    assert conf["hyperparameters"] == {"max_depth": 6}
    assert map_airflow_state_to_training_status("queued") == TrainingRunStatus.QUEUED
    assert map_airflow_state_to_training_status("running") == TrainingRunStatus.RUNNING
    assert map_airflow_state_to_training_status("success") == TrainingRunStatus.SUCCEEDED
    assert map_airflow_state_to_training_status("failed") == TrainingRunStatus.FAILED
    assert map_airflow_state_to_training_status("skipped") == TrainingRunStatus.CANCELED
    assert map_airflow_state_to_training_status("unknown") is None
    assert parse_training_airflow_orchestrator_run_id("local-training:run") is None


def _training_run(
    *,
    status: TrainingRunStatus,
    orchestrator_run_id: str = "workflow-1",
) -> TrainingRun:
    return TrainingRun(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=uuid4(),
        algorithm="xgboost",
        model_type="xgboost",
        objective_metric_name="auc",
        hyperparameters={"max_depth": 6},
        status=status,
        requested_by=uuid4(),
        artifact_uri="s3://forgeml-artifacts/training-runs/run-1",
        orchestrator_run_id=orchestrator_run_id,
        metrics={},
        error_message=None,
    )


def _observed_at():
    from datetime import UTC, datetime

    return datetime(2026, 8, 10, 23, 0, tzinfo=UTC)
