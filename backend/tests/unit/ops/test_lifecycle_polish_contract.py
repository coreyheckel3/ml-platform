import json
from pathlib import Path

from scripts.ci.check_lifecycle_polish_contract import (
    build_lifecycle_polish_contract,
    check_lifecycle_polish_contract,
    serialize_lifecycle_polish_contract,
    validate_lifecycle_polish_definition,
    write_lifecycle_polish_contract,
)


def test_lifecycle_polish_definition_validates_required_assets() -> None:
    assert validate_lifecycle_polish_definition(Path(".")) == ()


def test_lifecycle_polish_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "lifecycle-polish.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_lifecycle_polish_contract.py",
        encoding="utf-8",
    )

    write_lifecycle_polish_contract(contract_path)

    passed, detail = check_lifecycle_polish_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_lifecycle_polish_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "lifecycle-polish.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_lifecycle_polish_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_lifecycle_polish_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_lifecycle_polish_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "lifecycle-polish.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_lifecycle_polish_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_lifecycle_polish_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_lifecycle_polish_contract_matches_source() -> None:
    passed, detail = check_lifecycle_polish_contract(
        Path("contracts/ops/lifecycle-polish.v1.json")
    )

    assert passed, detail


def test_lifecycle_polish_contract_shape() -> None:
    parsed = json.loads(
        serialize_lifecycle_polish_contract(build_lifecycle_polish_contract())
    )

    assert parsed["schema_version"] == "forgeml.lifecycle_polish_contract.v1"
    assert parsed["route"]["path"] == "/lifecycle"
    assert parsed["rbac_permission"] == "lifecycle:read"
    assert "GET /api/v1/projects/{project_id}/lifecycle/summary" in parsed["api_surface"]
    assert "Stage Readiness" in parsed["required_ui_sections"]
    assert "retraining" in parsed["required_lifecycle_stages"]
    assert "13-lifecycle.png" in parsed["required_release_signals"]
    assert "python scripts/ci/check_lifecycle_polish_contract.py" in parsed[
        "quality_gates"
    ]
