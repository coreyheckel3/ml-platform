import json
from pathlib import Path

from scripts.ci.check_request_logging_contract import (
    build_request_logging_contract,
    check_request_logging_contract,
    serialize_request_logging_contract,
    validate_request_logging_contract,
    write_request_logging_contract,
)


def test_request_logging_contract_validates_event_shape_and_redaction() -> None:
    assert validate_request_logging_contract() == ()


def test_request_logging_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "request-log-event.v1.json"

    write_request_logging_contract(contract_path)

    passed, detail = check_request_logging_contract(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_request_logging_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "request-log-event.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_request_logging_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_request_logging_contract_matches_source() -> None:
    passed, detail = check_request_logging_contract(
        Path("contracts/observability/request-log-event.v1.json")
    )

    assert passed, detail


def test_request_logging_contract_serialization_is_deterministic() -> None:
    contract = build_request_logging_contract()

    assert serialize_request_logging_contract(contract) == serialize_request_logging_contract(
        contract
    )


def test_request_logging_contract_shape() -> None:
    parsed = json.loads(serialize_request_logging_contract(build_request_logging_contract()))

    assert parsed["schema_version"] == "forgeml.request_logging_contract.v1"
    assert parsed["event_schema_version"] == "forgeml.request_log.v1"
    assert "trace_id" in parsed["required_top_level_fields"]
    assert "duration_ms" in parsed["required_http_fields"]
    assert "token" in parsed["redaction"]["sensitive_field_markers"]
