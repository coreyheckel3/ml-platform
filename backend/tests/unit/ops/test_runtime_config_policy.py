import json
from pathlib import Path

from scripts.ci.check_runtime_config_policy import (
    REQUIRED_GUARDRAILS,
    build_runtime_config_policy_contract,
    check_runtime_config_policy,
    serialize_runtime_config_policy,
    validate_runtime_config_policy,
    write_runtime_config_policy,
)

from forgeml.platform.config import Settings
from forgeml.platform.config_policy import RUNTIME_CONFIG_GUARDRAILS, validate_runtime_config


def test_runtime_config_policy_defines_required_guardrails() -> None:
    guardrail_codes = {guardrail.code for guardrail in RUNTIME_CONFIG_GUARDRAILS}

    assert REQUIRED_GUARDRAILS.issubset(guardrail_codes)


def test_runtime_config_policy_validates_fixture_coverage() -> None:
    assert validate_runtime_config_policy() == ()


def test_runtime_config_policy_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "runtime-config-policy.v1.json"

    write_runtime_config_policy(contract_path)

    passed, detail = check_runtime_config_policy(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_runtime_config_policy_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "runtime-config-policy.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_runtime_config_policy(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_runtime_config_policy_matches_source() -> None:
    passed, detail = check_runtime_config_policy(
        Path("contracts/security/runtime-config-policy.v1.json")
    )

    assert passed, detail


def test_runtime_config_policy_serialization_is_deterministic() -> None:
    contract = build_runtime_config_policy_contract()

    assert serialize_runtime_config_policy(contract) == serialize_runtime_config_policy(contract)


def test_runtime_config_policy_contract_shape() -> None:
    contract = build_runtime_config_policy_contract()
    parsed = json.loads(serialize_runtime_config_policy(contract))

    assert parsed["schema_version"] == "forgeml.runtime_config_policy.v1"
    assert "production" in parsed["production_like_environments"]
    assert parsed["summary"]["guardrail_count"] == len(RUNTIME_CONFIG_GUARDRAILS)


def test_default_production_runtime_is_not_considered_safe() -> None:
    violations = validate_runtime_config(Settings(environment="production"))

    assert violations
