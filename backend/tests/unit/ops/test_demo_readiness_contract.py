import json
from pathlib import Path

from scripts.ci.check_demo_readiness_contract import (
    build_demo_readiness_contract,
    check_demo_readiness_contract,
    serialize_demo_readiness_contract,
    validate_demo_readiness_definition,
    write_demo_readiness_contract,
)


def test_demo_readiness_definition_validates_required_assets() -> None:
    assert validate_demo_readiness_definition(Path(".")) == ()


def test_demo_readiness_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "demo-readiness.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("python scripts/ci/check_demo_readiness_contract.py", encoding="utf-8")

    write_demo_readiness_contract(contract_path)

    passed, detail = check_demo_readiness_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_demo_readiness_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "demo-readiness.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text("python scripts/ci/check_demo_readiness_contract.py", encoding="utf-8")

    passed, detail = check_demo_readiness_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_demo_readiness_contract_matches_source() -> None:
    passed, detail = check_demo_readiness_contract(Path("contracts/ops/demo-readiness.v1.json"))

    assert passed, detail


def test_demo_readiness_contract_shape() -> None:
    parsed = json.loads(serialize_demo_readiness_contract(build_demo_readiness_contract()))

    assert parsed["schema_version"] == "forgeml.demo_readiness_contract.v1"
    assert "one_command_local_stack" in parsed["demo_capabilities"]
    assert "seeded_data_refresh" in parsed["demo_capabilities"]
    assert "frontend_screenshot_capture" in parsed["demo_capabilities"]
    assert "architecture_walkthrough" in parsed["demo_capabilities"]
    assert "training_runs" in parsed["seeded_surfaces"]
    assert "fraud-detection" in parsed["demo_projects"]
    assert "python scripts/ci/check_demo_readiness_contract.py" in parsed["quality_gates"]
