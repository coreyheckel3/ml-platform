from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forgeml.platform.security.permissions import (
    PERMISSIONS,
    ROLE_PRESETS,
    permission_codes,
)

DEFAULT_OUTPUT_PATH = Path("contracts/security/permission-catalog.v1.json")
DEFAULT_SCAN_ROOT = Path("backend/src/forgeml/modules")


@dataclass(frozen=True)
class EnforcedPermission:
    code: str
    source_path: str
    line_number: int


def build_permission_catalog(scan_root: Path = DEFAULT_SCAN_ROOT) -> dict[str, Any]:
    enforced_permissions = extract_enforced_permissions(scan_root)
    enforced_by_code: dict[str, list[str]] = {}
    for permission in enforced_permissions:
        enforced_by_code.setdefault(permission.code, []).append(
            f"{permission.source_path}:{permission.line_number}"
        )

    return {
        "schema_version": "forgeml.permission_catalog.v1",
        "generated_from": [
            "forgeml.platform.security.permissions",
            scan_root.as_posix(),
        ],
        "summary": {
            "permission_count": len(PERMISSIONS),
            "role_preset_count": len(ROLE_PRESETS),
            "enforced_permission_count": len(enforced_by_code),
        },
        "permissions": [
            {
                "code": permission.code,
                "module": permission.module,
                "action": permission.action,
                "description": permission.description,
                "enforced_at": sorted(enforced_by_code.get(permission.code, [])),
            }
            for permission in sorted(PERMISSIONS, key=lambda item: item.code)
        ],
        "role_presets": [
            {
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "permissions": sorted(role.permissions),
            }
            for role in sorted(ROLE_PRESETS, key=lambda item: item.code)
        ],
    }


def extract_enforced_permissions(
    scan_root: Path = DEFAULT_SCAN_ROOT,
) -> tuple[EnforcedPermission, ...]:
    permissions: list[EnforcedPermission] = []
    for path in sorted(scan_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            permission = _permission_from_call(node)
            if permission is None:
                continue
            permissions.append(
                EnforcedPermission(
                    code=permission,
                    source_path=path.as_posix(),
                    line_number=node.lineno,
                )
            )
    return tuple(
        sorted(permissions, key=lambda item: (item.code, item.source_path, item.line_number))
    )


def validate_permission_catalog(
    enforced_permissions: tuple[EnforcedPermission, ...],
    known_permissions: frozenset[str] | None = None,
) -> tuple[str, ...]:
    known = known_permissions or permission_codes()
    findings: list[str] = []

    duplicate_codes = _duplicates(permission.code for permission in PERMISSIONS)
    for code in duplicate_codes:
        findings.append(f"Permission {code} is defined more than once.")

    duplicate_roles = _duplicates(role.code for role in ROLE_PRESETS)
    for code in duplicate_roles:
        findings.append(f"Role preset {code} is defined more than once.")

    for role in ROLE_PRESETS:
        unknown_role_permissions = sorted(
            permission
            for permission in role.permissions
            if permission != "*" and permission not in known
        )
        if unknown_role_permissions:
            findings.append(
                f"Role preset {role.code} references unknown permissions: "
                f"{', '.join(unknown_role_permissions)}"
            )

    unknown_enforced_permissions = sorted(
        {
            permission.code
            for permission in enforced_permissions
            if permission.code != "*" and permission.code not in known
        }
    )
    for code in unknown_enforced_permissions:
        locations = sorted(
            f"{permission.source_path}:{permission.line_number}"
            for permission in enforced_permissions
            if permission.code == code
        )
        findings.append(f"Enforced permission {code} is missing from catalog: {locations}")

    return tuple(findings)


def serialize_permission_catalog(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, indent=2, sort_keys=True) + "\n"


def write_permission_catalog(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_permission_catalog(build_permission_catalog()),
        encoding="utf-8",
    )


def check_permission_catalog(output_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    enforced_permissions = extract_enforced_permissions()
    findings = validate_permission_catalog(enforced_permissions)
    if findings:
        return False, "Permission catalog violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Permission catalog contract does not exist: {output_path}"

    expected = serialize_permission_catalog(build_permission_catalog())
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Permission catalog contract is stale: {output_path}"
    return True, f"Permission catalog contract is current: {output_path}"


def _permission_from_call(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "has"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "principal"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "_require"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return node.args[1].value
    return None


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        text = str(value)
        if text in seen:
            duplicates.add(text)
        seen.add(text)
    return tuple(sorted(duplicates))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML permission definitions and role presets."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in permission catalog contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in permission catalog contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_permission_catalog(args.output)
        print(f"Wrote permission catalog contract: {args.output}")
        return 0

    passed, detail = check_permission_catalog(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
