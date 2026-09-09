import json
from pathlib import Path

from scripts.ci.check_platform_admin_controls_contract import (
    build_platform_admin_controls_contract,
    check_platform_admin_controls_contract,
    serialize_platform_admin_controls_contract,
    validate_platform_admin_controls_definition,
    write_platform_admin_controls_contract,
)


def test_platform_admin_controls_definition_validates_required_assets() -> None:
    assert validate_platform_admin_controls_definition(Path(".")) == ()


def test_platform_admin_controls_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "platform-admin-controls.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_platform_admin_controls_contract.py",
        encoding="utf-8",
    )

    write_platform_admin_controls_contract(contract_path)

    passed, detail = check_platform_admin_controls_contract(
        contract_path,
        ci_path=ci_path,
    )
    assert passed
    assert str(contract_path) in detail


def test_platform_admin_controls_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "platform-admin-controls.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_platform_admin_controls_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_platform_admin_controls_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_platform_admin_controls_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "platform-admin-controls.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_platform_admin_controls_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_platform_admin_controls_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_platform_admin_controls_contract_matches_source() -> None:
    passed, detail = check_platform_admin_controls_contract(
        Path("contracts/ops/platform-admin-controls.v1.json")
    )

    assert passed, detail


def test_platform_admin_controls_contract_shape() -> None:
    parsed = json.loads(
        serialize_platform_admin_controls_contract(
            build_platform_admin_controls_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.platform_admin_controls_contract.v1"
    assert parsed["route"]["path"] == "/admin"
    assert parsed["route"]["label"] == "Admin"
    assert "GET /api/v1/admin/controls" in parsed["api_surface"]
    assert parsed["rbac_permission"] == "admin:controls:read"
    assert "Organization Overview" in parsed["required_ui_sections"]
    assert "production_like" in parsed["required_runtime_signals"]
    assert "Tenant isolation" in parsed["required_safeguards"]
    assert "12-admin-controls.png" in parsed["required_release_signals"]
    assert "python scripts/ci/check_platform_admin_controls_contract.py" in parsed[
        "quality_gates"
    ]
