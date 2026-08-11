import json
from pathlib import Path

from scripts.ci.check_monitoring_dashboard_contract import (
    build_monitoring_dashboard_contract,
    check_monitoring_dashboard_contract,
    serialize_monitoring_dashboard_contract,
    validate_monitoring_dashboard_definition,
    write_monitoring_dashboard_contract,
)


def test_monitoring_dashboard_definition_validates_required_sources() -> None:
    assert validate_monitoring_dashboard_definition(Path(".")) == ()


def test_monitoring_dashboard_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "monitoring-dashboard.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_monitoring_dashboard_contract.py",
        encoding="utf-8",
    )

    write_monitoring_dashboard_contract(contract_path)

    passed, detail = check_monitoring_dashboard_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_monitoring_dashboard_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "monitoring-dashboard.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_monitoring_dashboard_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_monitoring_dashboard_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_monitoring_dashboard_contract_matches_source() -> None:
    passed, detail = check_monitoring_dashboard_contract(
        Path("contracts/observability/monitoring-dashboard.v1.json")
    )

    assert passed, detail


def test_monitoring_dashboard_contract_shape() -> None:
    parsed = json.loads(
        serialize_monitoring_dashboard_contract(build_monitoring_dashboard_contract())
    )

    assert parsed["schema_version"] == "forgeml.monitoring_dashboard_contract.v1"
    assert "GET /api/v1/projects/{project_id}/monitoring/operations" in parsed["api_surface"]
    assert {
        "inference_latency_percentiles",
        "inference_error_breakdown",
        "drift_trends",
        "training_failures",
        "retraining_activity",
    }.issubset(set(parsed["operations_signal_families"]))
    assert "Latency Percentiles" in parsed["frontend_sections"]
    assert "python scripts/ci/check_monitoring_dashboard_contract.py" in parsed[
        "quality_gates"
    ]
