import json
from pathlib import Path

from scripts.ci.check_problem_details_contract import (
    build_problem_details_contract,
    check_problem_details_contract,
    serialize_problem_details_contract,
    validate_problem_details_contract,
    write_problem_details_contract,
)


def test_problem_details_contract_validates_samples() -> None:
    assert validate_problem_details_contract() == ()


def test_problem_details_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "problem-details.v1.json"

    write_problem_details_contract(contract_path)

    passed, detail = check_problem_details_contract(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_problem_details_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "problem-details.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_problem_details_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_problem_details_contract_matches_source() -> None:
    passed, detail = check_problem_details_contract(Path("contracts/api/problem-details.v1.json"))

    assert passed, detail


def test_problem_details_contract_serialization_is_deterministic() -> None:
    contract = build_problem_details_contract()

    assert serialize_problem_details_contract(contract) == serialize_problem_details_contract(
        contract
    )


def test_problem_details_contract_shape() -> None:
    parsed = json.loads(serialize_problem_details_contract(build_problem_details_contract()))
    domain_error_codes = {error["code"] for error in parsed["domain_errors"]}

    assert parsed["schema_version"] == "forgeml.problem_details_contract.v1"
    assert parsed["problem_details_schema_version"] == "forgeml.problem_details.v1"
    assert "trace_id" in parsed["required_fields"]
    assert "input" not in parsed["validation_error_required_fields"]
    assert {"validation_failed", "resource_not_found", "internal_error"}.issubset(
        domain_error_codes
    )
