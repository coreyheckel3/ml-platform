import json
from pathlib import Path

from scripts.ci.check_airflow_orchestration_contract import (
    build_airflow_orchestration_contract,
    check_airflow_orchestration_contract,
    serialize_airflow_orchestration_contract,
    validate_airflow_orchestration_definition,
    write_airflow_orchestration_contract,
)


def test_airflow_orchestration_definition_validates_required_assets() -> None:
    assert validate_airflow_orchestration_definition(Path(".")) == ()


def test_airflow_orchestration_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "airflow-training.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_airflow_orchestration_contract.py",
        encoding="utf-8",
    )

    write_airflow_orchestration_contract(contract_path)

    passed, detail = check_airflow_orchestration_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_airflow_orchestration_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "airflow-training.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_airflow_orchestration_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_airflow_orchestration_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_airflow_orchestration_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "airflow-training.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_airflow_orchestration_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_airflow_orchestration_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_airflow_orchestration_contract_matches_source() -> None:
    passed, detail = check_airflow_orchestration_contract(
        Path("contracts/orchestration/airflow-training.v1.json")
    )

    assert passed, detail


def test_airflow_orchestration_contract_shape() -> None:
    parsed = json.loads(
        serialize_airflow_orchestration_contract(build_airflow_orchestration_contract())
    )

    assert parsed["schema_version"] == "forgeml.airflow_training_orchestration_contract.v1"
    assert parsed["airflow_schema_version"] == "forgeml.airflow_orchestration.v1"
    assert parsed["training_conf_schema_version"] == "forgeml.training_airflow_dag_run.v1"
    assert parsed["gateway_boundary"]["gateway_protocol"] == "AirflowWorkflowGateway"
    assert parsed["gateway_boundary"]["training_adapter"] == "AirflowTrainingWorkflowOrchestrator"
    assert "GET /api/v1/training-runs/{training_run_id}/orchestration-status" in parsed[
        "api_surface"
    ]
    assert parsed["status_mapping"]["success"] == "succeeded"
    assert "training_run_id" in parsed["training_dag_contract"]["required_conf_fields"]
