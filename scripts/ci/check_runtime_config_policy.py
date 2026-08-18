from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from forgeml.platform.config import Settings
from forgeml.platform.config_policy import (
    PRODUCTION_LIKE_ENVIRONMENTS,
    RUNTIME_CONFIG_GUARDRAILS,
    validate_runtime_config,
)

DEFAULT_OUTPUT_PATH = Path("contracts/security/runtime-config-policy.v1.json")
REQUIRED_GUARDRAILS = frozenset(
    {
        "jwt_secret_not_default",
        "jwt_secret_minimum_length",
        "docs_disabled",
        "rate_limit_enabled",
        "structured_logging_enabled",
        "request_logging_enabled",
        "readiness_checks_enabled",
        "external_training_profiles_disabled",
        "cors_origins_non_empty",
        "cors_no_wildcard",
        "cors_no_localhost",
        "database_url_not_localhost",
        "redis_url_not_localhost",
        "object_storage_endpoint_not_localhost",
        "mlflow_tracking_uri_not_localhost",
        "airflow_base_url_not_localhost",
    }
)


def build_runtime_config_policy_contract() -> dict[str, Any]:
    return {
        "schema_version": "forgeml.runtime_config_policy.v1",
        "generated_from": ["forgeml.platform.config_policy"],
        "production_like_environments": sorted(PRODUCTION_LIKE_ENVIRONMENTS),
        "summary": {
            "guardrail_count": len(RUNTIME_CONFIG_GUARDRAILS),
            "required_guardrail_count": len(REQUIRED_GUARDRAILS),
        },
        "guardrails": [
            asdict(guardrail)
            for guardrail in sorted(RUNTIME_CONFIG_GUARDRAILS, key=lambda item: item.code)
        ],
    }


def validate_runtime_config_policy() -> tuple[str, ...]:
    findings: list[str] = []
    guardrail_codes = [guardrail.code for guardrail in RUNTIME_CONFIG_GUARDRAILS]
    duplicate_codes = _duplicates(guardrail_codes)
    if duplicate_codes:
        findings.append(f"Duplicate runtime config guardrails: {', '.join(duplicate_codes)}")

    missing_required = sorted(REQUIRED_GUARDRAILS - set(guardrail_codes))
    if missing_required:
        findings.append(
            f"Missing required runtime config guardrails: {', '.join(missing_required)}"
        )

    for code, settings in _insecure_fixture_settings_by_guardrail().items():
        violation_codes = {violation.code for violation in validate_runtime_config(settings)}
        if code not in violation_codes:
            findings.append(f"Insecure fixture did not trigger guardrail: {code}")

    hardened_violations = validate_runtime_config(_hardened_production_settings())
    if hardened_violations:
        findings.append(
            "Hardened production settings triggered guardrails: "
            + ", ".join(violation.code for violation in hardened_violations)
        )

    return tuple(findings)


def serialize_runtime_config_policy(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_runtime_config_policy(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_runtime_config_policy(build_runtime_config_policy_contract()),
        encoding="utf-8",
    )


def check_runtime_config_policy(output_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    findings = validate_runtime_config_policy()
    if findings:
        return False, "Runtime config policy violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Runtime config policy contract does not exist: {output_path}"

    expected = serialize_runtime_config_policy(build_runtime_config_policy_contract())
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Runtime config policy contract is stale: {output_path}"
    return True, f"Runtime config policy contract is current: {output_path}"


def _hardened_production_settings() -> Settings:
    return Settings(
        environment="production",
        database_url="postgresql+psycopg://forgeml:forgeml@postgres.internal:5432/forgeml",
        redis_url="redis://redis.internal:6379/0",
        object_storage_endpoint="https://s3.us-east-1.amazonaws.com",
        mlflow_tracking_uri="https://mlflow.forgeml.internal",
        airflow_base_url="https://airflow.forgeml.internal",
        jwt_secret=_example_signing_material(),
        enable_docs=False,
        cors_origins=["https://app.forgeml.example"],
        rate_limit_enabled=True,
        readiness_checks_enabled=True,
        external_training_profiles_enabled=False,
    )


def _insecure_fixture_settings_by_guardrail() -> dict[str, Settings]:
    base = _hardened_production_settings()
    return {
        "jwt_secret_not_default": base.model_copy(
            update={"jwt_secret": "change-me-for-local-development"}
        ),
        "jwt_secret_minimum_length": base.model_copy(update={"jwt_secret": "short"}),
        "docs_disabled": base.model_copy(update={"enable_docs": True}),
        "rate_limit_enabled": base.model_copy(update={"rate_limit_enabled": False}),
        "structured_logging_enabled": base.model_copy(
            update={"structured_logging_enabled": False}
        ),
        "request_logging_enabled": base.model_copy(update={"request_logging_enabled": False}),
        "readiness_checks_enabled": base.model_copy(
            update={"readiness_checks_enabled": False}
        ),
        "external_training_profiles_disabled": base.model_copy(
            update={"external_training_profiles_enabled": True}
        ),
        "cors_origins_non_empty": base.model_copy(update={"cors_origins": []}),
        "cors_no_wildcard": base.model_copy(update={"cors_origins": ["*"]}),
        "cors_no_localhost": base.model_copy(
            update={"cors_origins": ["http://localhost:5173"]}
        ),
        "database_url_not_localhost": base.model_copy(
            update={
                "database_url": "postgresql+psycopg://forgeml:forgeml@localhost:5432/forgeml"
            }
        ),
        "redis_url_not_localhost": base.model_copy(update={"redis_url": "redis://127.0.0.1:6379/0"}),
        "object_storage_endpoint_not_localhost": base.model_copy(
            update={"object_storage_endpoint": "http://localhost:9000"}
        ),
        "mlflow_tracking_uri_not_localhost": base.model_copy(
            update={"mlflow_tracking_uri": "http://localhost:5000"}
        ),
        "airflow_base_url_not_localhost": base.model_copy(
            update={"airflow_base_url": "http://localhost:8080"}
        ),
    }


def _example_signing_material() -> str:
    return "production-grade-signing-material-32"


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML production-like runtime configuration guardrails."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in runtime config policy contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in runtime config policy contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_runtime_config_policy(args.output)
        print(f"Wrote runtime config policy contract: {args.output}")
        return 0

    passed, detail = check_runtime_config_policy(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
