import json
from pathlib import Path

from scripts.ci.check_mlflow_tracking_contract import (
    build_mlflow_tracking_contract,
    check_mlflow_tracking_contract,
    serialize_mlflow_tracking_contract,
    validate_mlflow_tracking_definition,
    write_mlflow_tracking_contract,
)


def test_mlflow_tracking_definition_validates_required_assets() -> None:
    assert validate_mlflow_tracking_definition(Path(".")) == ()


def test_mlflow_tracking_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "mlflow-tracking.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("python scripts/ci/check_mlflow_tracking_contract.py", encoding="utf-8")

    write_mlflow_tracking_contract(contract_path)

    passed, detail = check_mlflow_tracking_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_mlflow_tracking_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "mlflow-tracking.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text("python scripts/ci/check_mlflow_tracking_contract.py", encoding="utf-8")

    passed, detail = check_mlflow_tracking_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_mlflow_tracking_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "mlflow-tracking.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_mlflow_tracking_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_mlflow_tracking_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_mlflow_tracking_contract_matches_source() -> None:
    passed, detail = check_mlflow_tracking_contract(
        Path("contracts/mlflow/mlflow-tracking.v1.json")
    )

    assert passed, detail


def test_mlflow_tracking_contract_shape() -> None:
    parsed = json.loads(serialize_mlflow_tracking_contract(build_mlflow_tracking_contract()))

    assert parsed["schema_version"] == "forgeml.mlflow_tracking_contract.v1"
    assert parsed["sync_schema_version"] == "forgeml.mlflow_tracking_sync.v1"
    assert parsed["tracking_boundary"]["gateway_protocol"] == "MLflowTrackingGateway"
    assert parsed["tracking_boundary"]["http_adapter"] == "MLflowHttpTrackingGateway"
    assert parsed["tracking_boundary"]["runtime_dependency_policy"] == "stdlib-http-adapter"
    assert "/api/2.0/mlflow/runs/log-batch" in parsed["rest_endpoints"]
    assert "forgeml.training_run_id" in parsed["required_tags"]
    assert "evaluation_report.mlflow_sync" in parsed["failure_semantics"]["observability"]
