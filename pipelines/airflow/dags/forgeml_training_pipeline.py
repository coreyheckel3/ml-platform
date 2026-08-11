from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

TRAINING_AIRFLOW_CONF_SCHEMA_VERSION = "forgeml.training_airflow_dag_run.v1"
REQUIRED_TRAINING_CONF_FIELDS = (
    "schema_version",
    "organization_id",
    "project_id",
    "experiment_id",
    "experiment_run_id",
    "training_run_id",
    "dataset_version_id",
    "feature_set_id",
    "algorithm",
    "model_type",
    "objective_metric_name",
    "hyperparameters",
    "artifact_uri",
    "requested_by",
)
NULLABLE_TRAINING_CONF_FIELDS = {"dataset_version_id", "feature_set_id"}


@dag(
    dag_id="forgeml_training_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["forgeml", "training"],
)
def forgeml_training_pipeline():
    @task
    def validate_training_conf() -> dict[str, str]:
        context = get_current_context()
        dag_run = context["dag_run"]
        conf = dag_run.conf or {}
        missing = [field for field in REQUIRED_TRAINING_CONF_FIELDS if field not in conf]
        null_fields = [
            field
            for field in REQUIRED_TRAINING_CONF_FIELDS
            if field not in NULLABLE_TRAINING_CONF_FIELDS and conf.get(field) is None
        ]
        if missing or null_fields:
            invalid_fields = sorted([*missing, *null_fields])
            raise ValueError(
                f"Training DAG run conf has invalid fields: {', '.join(invalid_fields)}"
            )
        if not conf.get("dataset_version_id") and not conf.get("feature_set_id"):
            raise ValueError("Training DAG run conf must include dataset or feature lineage.")
        if conf["schema_version"] != TRAINING_AIRFLOW_CONF_SCHEMA_VERSION:
            raise ValueError("Training DAG run conf schema version is not supported.")
        return {
            "schema_version": TRAINING_AIRFLOW_CONF_SCHEMA_VERSION,
            "training_run_id": str(conf["training_run_id"]),
            "status": "accepted",
        }

    validate_training_conf()


forgeml_training_pipeline()
