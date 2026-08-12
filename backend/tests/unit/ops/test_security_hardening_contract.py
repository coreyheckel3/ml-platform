import json
from pathlib import Path

from scripts.ci.check_security_hardening_contract import (
    build_security_hardening_contract,
    check_security_hardening_contract,
    serialize_security_hardening_contract,
    validate_security_hardening_definition,
    write_security_hardening_contract,
)


def test_security_hardening_definition_validates_required_sources() -> None:
    assert validate_security_hardening_definition(Path(".")) == ()


def test_security_hardening_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "security-hardening.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_security_hardening_contract.py",
        encoding="utf-8",
    )

    write_security_hardening_contract(contract_path)

    passed, detail = check_security_hardening_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_security_hardening_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "security-hardening.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_security_hardening_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_security_hardening_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_security_hardening_contract_matches_source() -> None:
    passed, detail = check_security_hardening_contract(
        Path("contracts/security/security-hardening.v1.json")
    )

    assert passed, detail


def test_security_hardening_contract_shape() -> None:
    parsed = json.loads(
        serialize_security_hardening_contract(build_security_hardening_contract())
    )

    assert parsed["schema_version"] == "forgeml.security_hardening_contract.v1"
    assert "organization_isolation" in parsed["control_families"]
    assert "rbac_role_matrix" in parsed["control_families"]
    assert "audit_log" in parsed["tenant_isolation_sources"]
    assert "security_auditor" in parsed["rbac_role_presets"]
    assert "password" in parsed["sensitive_audit_metadata_keys"]
