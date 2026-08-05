import json
from pathlib import Path

from scripts.ci.check_release_smoke_contract import (
    build_release_smoke_contract,
    check_release_smoke_contract,
    serialize_release_smoke_contract,
    validate_release_smoke_definition,
    write_release_smoke_contract,
)


def test_release_smoke_definition_validates_required_surface_area() -> None:
    assert validate_release_smoke_definition() == ()


def test_release_smoke_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-smoke.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("python scripts/ci/check_release_smoke_contract.py", encoding="utf-8")

    write_release_smoke_contract(contract_path)

    passed, detail = check_release_smoke_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_release_smoke_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-smoke.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text("python scripts/ci/check_release_smoke_contract.py", encoding="utf-8")

    passed, detail = check_release_smoke_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_release_smoke_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-smoke.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_smoke_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_release_smoke_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_smoke_contract_matches_source() -> None:
    passed, detail = check_release_smoke_contract(Path("contracts/ops/release-smoke.v1.json"))

    assert passed, detail


def test_release_smoke_contract_shape() -> None:
    parsed = json.loads(serialize_release_smoke_contract(build_release_smoke_contract()))
    stage_codes = {stage["code"] for stage in parsed["stages"]}

    assert parsed["schema_version"] == "forgeml.release_smoke_contract.v1"
    assert parsed["runtime_requirements"]["mutates_data"] is False
    assert parsed["summary"]["required_stage_count"] >= 16
    assert "training_logs_surface" in stage_codes
