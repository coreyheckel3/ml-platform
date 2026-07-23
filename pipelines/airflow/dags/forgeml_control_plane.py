from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="forgeml_control_plane_smoke",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["forgeml", "platform"],
)
def forgeml_control_plane_smoke():
    @task
    def validate_runtime_contract() -> dict[str, str]:
        return {"status": "ok", "contract": "workflow-dispatch"}

    validate_runtime_contract()


forgeml_control_plane_smoke()

