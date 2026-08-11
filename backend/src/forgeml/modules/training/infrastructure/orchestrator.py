from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from forgeml.modules.training.domain.entities import (
    TrainingOrchestrationStatus,
    TrainingRun,
    TrainingRunStatus,
)
from forgeml.platform.airflow import (
    AirflowDagRunRequest,
    AirflowWorkflowGateway,
    build_airflow_workflow_gateway,
)
from forgeml.platform.config import Settings

TRAINING_AIRFLOW_CONF_SCHEMA_VERSION: Final[str] = "forgeml.training_airflow_dag_run.v1"
AIRFLOW_ORCHESTRATOR_RUN_PREFIX: Final[str] = "airflow"


class LocalTrainingWorkflowOrchestrator:
    def trigger_training(self, training_run: TrainingRun) -> str:
        return f"local-training:{training_run.project_id}:{training_run.id}"

    def cancel_training(self, training_run: TrainingRun) -> str:
        return f"local-training-cancel:{training_run.orchestrator_run_id}"

    def get_training_status(self, training_run: TrainingRun) -> TrainingOrchestrationStatus:
        return TrainingOrchestrationStatus(
            training_run_id=training_run.id,
            orchestrator_run_id=training_run.orchestrator_run_id,
            orchestrator="local",
            external_status=training_run.status.value,
            mapped_training_status=training_run.status,
            is_terminal=_is_terminal_training_status(training_run.status),
            external_url=None,
            metadata={
                "schema_version": TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
                "source": "local-training-orchestrator",
            },
            observed_at=_utcnow(),
        )


@dataclass(frozen=True)
class TrainingAirflowOrchestratorConfig:
    dag_id: str


class AirflowTrainingWorkflowOrchestrator:
    def __init__(
        self,
        *,
        gateway: AirflowWorkflowGateway,
        config: TrainingAirflowOrchestratorConfig,
    ) -> None:
        self._gateway = gateway
        self._config = config

    def trigger_training(self, training_run: TrainingRun) -> str:
        dag_run_id = training_airflow_dag_run_id(training_run.id)
        request = AirflowDagRunRequest(
            dag_id=self._config.dag_id,
            dag_run_id=dag_run_id,
            conf=training_airflow_conf(training_run),
            note=f"ForgeML training run {training_run.id}",
        )
        record = self._gateway.trigger_dag_run(request)
        return training_airflow_orchestrator_run_id(record.dag_id, record.dag_run_id)

    def cancel_training(self, training_run: TrainingRun) -> str:
        dag_ref = parse_training_airflow_orchestrator_run_id(training_run.orchestrator_run_id)
        if dag_ref is None:
            return training_run.orchestrator_run_id
        self._gateway.cancel_dag_run(
            dag_id=dag_ref.dag_id,
            dag_run_id=dag_ref.dag_run_id,
            note=f"Canceled by ForgeML for training run {training_run.id}.",
        )
        return training_run.orchestrator_run_id

    def get_training_status(self, training_run: TrainingRun) -> TrainingOrchestrationStatus:
        dag_ref = parse_training_airflow_orchestrator_run_id(training_run.orchestrator_run_id)
        if dag_ref is None:
            return TrainingOrchestrationStatus(
                training_run_id=training_run.id,
                orchestrator_run_id=training_run.orchestrator_run_id,
                orchestrator="airflow",
                external_status="unrecognized_run_id",
                mapped_training_status=None,
                is_terminal=False,
                external_url=None,
                metadata={
                    "schema_version": TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
                    "expected_prefix": AIRFLOW_ORCHESTRATOR_RUN_PREFIX,
                },
                observed_at=_utcnow(),
            )

        record = self._gateway.get_dag_run(dag_id=dag_ref.dag_id, dag_run_id=dag_ref.dag_run_id)
        mapped_status = map_airflow_state_to_training_status(record.state)
        return TrainingOrchestrationStatus(
            training_run_id=training_run.id,
            orchestrator_run_id=training_run.orchestrator_run_id,
            orchestrator="airflow",
            external_status=record.state,
            mapped_training_status=mapped_status,
            is_terminal=mapped_status is not None and _is_terminal_training_status(mapped_status),
            external_url=record.external_url,
            metadata={
                **record.metadata,
                "dag_id": record.dag_id,
                "dag_run_id": record.dag_run_id,
                "conf_schema_version": record.conf.get("schema_version"),
            },
            observed_at=record.observed_at,
        )


@dataclass(frozen=True)
class TrainingAirflowDagReference:
    dag_id: str
    dag_run_id: str


def build_training_workflow_orchestrator(settings: Settings):
    gateway = build_airflow_workflow_gateway(
        enabled=settings.airflow_orchestration_enabled,
        base_url=settings.airflow_base_url,
        username=settings.airflow_username,
        password=settings.airflow_password,
        timeout_seconds=settings.airflow_http_timeout_seconds,
    )
    if gateway is None:
        return LocalTrainingWorkflowOrchestrator()
    return AirflowTrainingWorkflowOrchestrator(
        gateway=gateway,
        config=TrainingAirflowOrchestratorConfig(dag_id=settings.airflow_training_dag_id),
    )


def training_airflow_dag_run_id(training_run_id: UUID) -> str:
    return f"forgeml_training__{training_run_id}"


def training_airflow_orchestrator_run_id(dag_id: str, dag_run_id: str) -> str:
    return f"{AIRFLOW_ORCHESTRATOR_RUN_PREFIX}://{dag_id}/{dag_run_id}"


def parse_training_airflow_orchestrator_run_id(
    orchestrator_run_id: str,
) -> TrainingAirflowDagReference | None:
    prefix = f"{AIRFLOW_ORCHESTRATOR_RUN_PREFIX}://"
    if not orchestrator_run_id.startswith(prefix):
        return None
    raw_reference = orchestrator_run_id.removeprefix(prefix)
    dag_id, separator, dag_run_id = raw_reference.partition("/")
    if not separator or not dag_id.strip() or not dag_run_id.strip():
        return None
    return TrainingAirflowDagReference(dag_id=dag_id, dag_run_id=dag_run_id)


def training_airflow_conf(training_run: TrainingRun) -> dict[str, object]:
    return {
        "schema_version": TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
        "organization_id": str(training_run.organization_id),
        "project_id": str(training_run.project_id),
        "experiment_id": str(training_run.experiment_id),
        "experiment_run_id": str(training_run.experiment_run_id),
        "training_run_id": str(training_run.id),
        "dataset_version_id": (
            str(training_run.dataset_version_id) if training_run.dataset_version_id else None
        ),
        "feature_set_id": str(training_run.feature_set_id) if training_run.feature_set_id else None,
        "algorithm": training_run.algorithm,
        "model_type": training_run.model_type,
        "objective_metric_name": training_run.objective_metric_name,
        "hyperparameters": training_run.hyperparameters,
        "artifact_uri": training_run.artifact_uri,
        "requested_by": str(training_run.requested_by),
    }


def map_airflow_state_to_training_status(state: str) -> TrainingRunStatus | None:
    normalized = state.strip().lower()
    if normalized in {"queued", "scheduled"}:
        return TrainingRunStatus.QUEUED
    if normalized in {"running", "restarting"}:
        return TrainingRunStatus.RUNNING
    if normalized == "success":
        return TrainingRunStatus.SUCCEEDED
    if normalized in {"failed", "upstream_failed"}:
        return TrainingRunStatus.FAILED
    if normalized in {"skipped", "removed"}:
        return TrainingRunStatus.CANCELED
    return None


def _is_terminal_training_status(status: TrainingRunStatus) -> bool:
    return status in {
        TrainingRunStatus.SUCCEEDED,
        TrainingRunStatus.FAILED,
        TrainingRunStatus.CANCELED,
        TrainingRunStatus.DEAD_LETTERED,
    }


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
