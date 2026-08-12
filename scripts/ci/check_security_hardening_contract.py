from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SECURITY_HARDENING_CONTRACT_SCHEMA_VERSION = "forgeml.security_hardening_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/security/security-hardening.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def build_security_hardening_contract() -> dict[str, Any]:
    return {
        "schema_version": SECURITY_HARDENING_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.security.permissions",
            "forgeml.platform.api.middleware",
            "forgeml.platform.config_policy",
            "forgeml.modules.administration.application.audit",
            "backend.tests.integration.security.test_tenant_isolation",
        ],
        "control_families": [
            "organization_isolation",
            "rbac_role_matrix",
            "rate_limit_partitioning",
            "audit_metadata_redaction",
            "secrets_and_runtime_guardrails",
        ],
        "tenant_isolation_sources": [
            "projects",
            "datasets",
            "training_runs",
            "audit_log",
        ],
        "rbac_role_presets": [
            "platform_admin",
            "ml_engineer",
            "ml_operator",
            "ml_viewer",
            "security_auditor",
        ],
        "sensitive_audit_metadata_keys": [
            "api_key",
            "authorization",
            "credential",
            "credentials",
            "jwt",
            "password",
            "refresh_token",
            "secret",
            "token",
        ],
        "quality_gates": [
            "python scripts/ci/check_security_hardening_contract.py",
            "backend/tests/integration/security/test_tenant_isolation.py",
            "backend/tests/unit/security/test_rbac_matrix.py",
            "backend/tests/unit/security/test_audit_sanitization.py",
            "backend/tests/api/test_security_hardening_api.py",
        ],
    }


def serialize_security_hardening_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_security_hardening_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_security_hardening_contract(build_security_hardening_contract()),
        encoding="utf-8",
    )


def check_security_hardening_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_security_hardening_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Security hardening contract does not exist: {output_path}")
    else:
        expected = serialize_security_hardening_contract(
            build_security_hardening_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Security hardening contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_security_hardening_contract.py" not in ci_source:
            findings.append("Security hardening contract checker is not wired into CI.")

    if findings:
        return False, "Security hardening contract violations: " + "; ".join(findings)
    return True, f"Security hardening contract is current: {output_path}"


def validate_security_hardening_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/platform/security/permissions.py",
        "backend/src/forgeml/platform/api/middleware.py",
        "backend/src/forgeml/platform/config_policy.py",
        "backend/src/forgeml/modules/administration/application/audit.py",
        "backend/tests/integration/security/test_tenant_isolation.py",
        "backend/tests/unit/security/test_rbac_matrix.py",
        "backend/tests/unit/security/test_audit_sanitization.py",
        "backend/tests/api/test_security_hardening_api.py",
        "outputs/forgeml/docs/13-security-strategy.md",
        ".env.example",
    ]
    findings = [
        f"Missing security hardening file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    contract = serialize_security_hardening_contract(build_security_hardening_contract())
    required_fragments = (
        (
            "ROLE_PRESETS",
            sources["backend/src/forgeml/platform/security/permissions.py"],
        ),
        (
            "FixedWindowRateLimiter",
            sources["backend/src/forgeml/platform/api/middleware.py"],
        ),
        (
            "SENSITIVE_AUDIT_METADATA_KEYS",
            sources["backend/src/forgeml/modules/administration/application/audit.py"],
        ),
        (
            "PRODUCTION_LIKE_ENVIRONMENTS",
            sources["backend/src/forgeml/platform/config_policy.py"],
        ),
        (
            "test_repository_queries_do_not_cross_tenant_boundaries",
            sources["backend/tests/integration/security/test_tenant_isolation.py"],
        ),
        (
            "test_role_preset_permissions_match_security_matrix",
            sources["backend/tests/unit/security/test_rbac_matrix.py"],
        ),
        (
            "test_record_user_audit_event_persists_sanitized_metadata",
            sources["backend/tests/unit/security/test_audit_sanitization.py"],
        ),
        (
            "test_rate_limiter_partitions_by_client_and_path",
            sources["backend/tests/api/test_security_hardening_api.py"],
        ),
        (
            "FORGEML_JWT_SECRET",
            sources[".env.example"],
        ),
        (
            "security hardening contract",
            sources["outputs/forgeml/docs/13-security-strategy.md"].lower(),
        ),
        ("organization_isolation", contract),
        ("audit_metadata_redaction", contract),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing security hardening fragments: {missing_fragments}")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML security hardening contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in security hardening contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in security hardening contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_security_hardening_contract(args.output)
        print(f"Wrote security hardening contract: {args.output}")
        return 0

    passed, detail = check_security_hardening_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
