import json
from pathlib import Path

from scripts.ci.check_portfolio_interview_mode_contract import (
    build_portfolio_interview_mode_contract,
    check_portfolio_interview_mode_contract,
    serialize_portfolio_interview_mode_contract,
    validate_portfolio_interview_mode_definition,
    write_portfolio_interview_mode_contract,
)


def test_portfolio_interview_mode_definition_validates_required_assets() -> None:
    assert validate_portfolio_interview_mode_definition(Path(".")) == ()


def test_portfolio_interview_mode_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "portfolio-interview-mode.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_portfolio_interview_mode_contract.py",
        encoding="utf-8",
    )

    write_portfolio_interview_mode_contract(contract_path)

    passed, detail = check_portfolio_interview_mode_contract(
        contract_path,
        ci_path=ci_path,
    )
    assert passed
    assert str(contract_path) in detail


def test_portfolio_interview_mode_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "portfolio-interview-mode.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_portfolio_interview_mode_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_portfolio_interview_mode_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_portfolio_interview_mode_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "portfolio-interview-mode.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_portfolio_interview_mode_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_portfolio_interview_mode_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_portfolio_interview_mode_contract_matches_source() -> None:
    passed, detail = check_portfolio_interview_mode_contract(
        Path("contracts/ops/portfolio-interview-mode.v1.json")
    )

    assert passed, detail


def test_portfolio_interview_mode_contract_shape() -> None:
    parsed = json.loads(
        serialize_portfolio_interview_mode_contract(
            build_portfolio_interview_mode_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.portfolio_interview_mode_contract.v1"
    assert parsed["route"]["path"] == "/portfolio"
    assert parsed["route"]["label"] == "Portfolio"
    assert "Reviewer Dashboard" in parsed["required_ui_sections"]
    assert "Architecture Walkthrough" in parsed["required_ui_sections"]
    assert "Validation Paths" in parsed["required_ui_sections"]
    assert "portfolio_interview_mode_contract" in parsed["required_interview_signals"]
    assert "make portfolio-interview" in parsed["operator_commands"]
    assert "make demo-stack-fresh" in parsed["operator_commands"]
    assert "frontend/tests/e2e/demo-walkthrough.spec.ts" in parsed["quality_gates"]
