from pathlib import Path

from scripts.ci.check_permission_catalog import (
    EnforcedPermission,
    check_permission_catalog,
    extract_enforced_permissions,
    serialize_permission_catalog,
    validate_permission_catalog,
    write_permission_catalog,
)

from forgeml.platform.security.permissions import ROLE_PRESETS, permission_codes


def test_permission_catalog_covers_all_enforced_service_permissions() -> None:
    enforced_permissions = extract_enforced_permissions()
    enforced_codes = {permission.code for permission in enforced_permissions}

    assert enforced_codes.issubset(permission_codes())
    assert "projects:create" in enforced_codes
    assert "training_runs:create" in enforced_codes
    assert "inference:predict" in enforced_codes


def test_role_presets_reference_known_permissions_or_wildcard() -> None:
    known_permissions = permission_codes()

    for role in ROLE_PRESETS:
        assert role.permissions
        assert all(
            permission == "*" or permission in known_permissions for permission in role.permissions
        )


def test_permission_catalog_rejects_unknown_enforced_permission() -> None:
    findings = validate_permission_catalog(
        (
            EnforcedPermission(
                code="models:launch_rocket",
                source_path="backend/src/forgeml/modules/models/application/services.py",
                line_number=42,
            ),
        )
    )

    assert findings == (
        "Enforced permission models:launch_rocket is missing from catalog: "
        "['backend/src/forgeml/modules/models/application/services.py:42']",
    )


def test_permission_catalog_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "permission-catalog.v1.json"

    write_permission_catalog(contract_path)

    passed, detail = check_permission_catalog(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_permission_catalog_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "permission-catalog.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_permission_catalog(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_permission_catalog_matches_source() -> None:
    passed, detail = check_permission_catalog(Path("contracts/security/permission-catalog.v1.json"))

    assert passed, detail


def test_permission_catalog_serialization_is_deterministic() -> None:
    catalog = {
        "schema_version": "forgeml.permission_catalog.v1",
        "permissions": [{"code": "projects:read"}],
    }

    serialized = serialize_permission_catalog(catalog)

    assert serialized == serialize_permission_catalog(catalog)
