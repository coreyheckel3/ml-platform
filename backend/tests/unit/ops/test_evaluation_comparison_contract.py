import json
from pathlib import Path

from scripts.ci.check_evaluation_comparison_contract import (
    build_evaluation_comparison_contract,
    check_evaluation_comparison_contract,
    serialize_evaluation_comparison_contract,
    validate_evaluation_comparison_definition,
    write_evaluation_comparison_contract,
)


def test_evaluation_comparison_definition_validates_required_assets() -> None:
    assert validate_evaluation_comparison_definition(Path(".")) == ()


def test_evaluation_comparison_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "evaluation-comparison.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_evaluation_comparison_contract.py",
        encoding="utf-8",
    )

    write_evaluation_comparison_contract(contract_path)

    passed, detail = check_evaluation_comparison_contract(
        contract_path,
        ci_path=ci_path,
    )
    assert passed
    assert str(contract_path) in detail


def test_evaluation_comparison_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "evaluation-comparison.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_evaluation_comparison_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_evaluation_comparison_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_evaluation_comparison_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "evaluation-comparison.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_evaluation_comparison_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_evaluation_comparison_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_evaluation_comparison_contract_matches_source() -> None:
    passed, detail = check_evaluation_comparison_contract(
        Path("contracts/ops/evaluation-comparison.v1.json")
    )

    assert passed, detail


def test_evaluation_comparison_contract_shape() -> None:
    parsed = json.loads(
        serialize_evaluation_comparison_contract(
            build_evaluation_comparison_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.evaluation_comparison_contract.v1"
    assert parsed["route"]["path"] == "/evaluation"
    assert parsed["rbac_permission"] == "evaluation:read"
    assert (
        "GET /api/v1/projects/{project_id}/evaluation/comparison"
        in parsed["api_surface"]
    )
    assert "Run Leaderboard" in parsed["required_ui_sections"]
    assert "risk_flags" in parsed["required_comparison_signals"]
    assert "14-evaluation.png" in parsed["required_release_signals"]
    assert "python scripts/ci/check_evaluation_comparison_contract.py" in parsed[
        "quality_gates"
    ]
