from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from forgeml.platform.api.problem_details import (
    INTERNAL_ERROR_DETAIL,
    PROBLEM_DETAILS_REQUIRED_FIELDS,
    PROBLEM_DETAILS_SCHEMA_VERSION,
    PROBLEM_TYPE_BASE_URL,
    VALIDATION_ERROR_REQUIRED_FIELDS,
    http_problem_details,
    internal_problem_details,
    normalize_validation_errors,
    problem_details_response,
    validation_problem_details,
)
from forgeml.platform.domain.errors import (
    AuthenticationFailedError,
    ConflictError,
    DomainValidationError,
    ForgeMLError,
    PermissionDeniedError,
    ResourceNotFoundError,
)

DEFAULT_OUTPUT_PATH = Path("contracts/api/problem-details.v1.json")
ERROR_TYPES = (
    AuthenticationFailedError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ConflictError,
    DomainValidationError,
    ForgeMLError,
)


def build_problem_details_contract() -> dict[str, Any]:
    return {
        "schema_version": "forgeml.problem_details_contract.v1",
        "problem_details_schema_version": PROBLEM_DETAILS_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.api.problem_details",
            "forgeml.platform.api.errors",
        ],
        "type_base_url": PROBLEM_TYPE_BASE_URL,
        "summary": {
            "required_field_count": len(PROBLEM_DETAILS_REQUIRED_FIELDS),
            "validation_error_required_field_count": len(VALIDATION_ERROR_REQUIRED_FIELDS),
            "domain_error_code_count": len(ERROR_TYPES),
        },
        "required_fields": sorted(PROBLEM_DETAILS_REQUIRED_FIELDS),
        "validation_error_required_fields": sorted(VALIDATION_ERROR_REQUIRED_FIELDS),
        "domain_errors": [
            {
                "class_name": error_type.__name__,
                "code": error_type.code,
                "status_code": error_type.status_code,
                "type": f"{PROBLEM_TYPE_BASE_URL}/{error_type.code}",
            }
            for error_type in sorted(ERROR_TYPES, key=lambda item: item.code)
        ],
        "handled_exception_types": [
            "ForgeMLError",
            "RequestValidationError",
            "StarletteHTTPException",
            "Exception",
        ],
        "internal_error_detail": INTERNAL_ERROR_DETAIL,
    }


def validate_problem_details_contract() -> tuple[str, ...]:
    findings: list[str] = []
    samples = [
        problem_details_response(
            code="conflict",
            status_code=409,
            detail="Project already exists.",
            trace_id="trace-123",
        ),
        validation_problem_details(
            trace_id="trace-123",
            errors=[
                {
                    "loc": ("body", "password"),
                    "msg": "Field required",
                    "type": "missing",
                    "input": "sensitive",
                }
            ],
        ),
        http_problem_details(status_code=404, detail="Not Found", trace_id="trace-123"),
        internal_problem_details(trace_id="trace-123"),
    ]

    for sample in samples:
        missing = sorted(set(PROBLEM_DETAILS_REQUIRED_FIELDS) - set(sample))
        if missing:
            findings.append(f"Problem details sample missing fields: {missing}")

    validation_errors = normalize_validation_errors(
        [
            {
                "loc": ("body", "password"),
                "msg": "Field required",
                "type": "missing",
                "input": "sensitive",
            }
        ]
    )
    validation_error = validation_errors[0]
    missing_validation = sorted(set(VALIDATION_ERROR_REQUIRED_FIELDS) - set(validation_error))
    if missing_validation:
        findings.append(f"Validation error sample missing fields: {missing_validation}")
    if "input" in validation_error or "sensitive" in json.dumps(validation_error):
        findings.append("Validation error sample leaked raw input.")

    internal_error = internal_problem_details(trace_id="trace-123")
    if internal_error.get("detail") != INTERNAL_ERROR_DETAIL:
        findings.append("Internal error detail is not sanitized.")

    domain_codes = [error_type.code for error_type in ERROR_TYPES]
    duplicate_codes = sorted({code for code in domain_codes if domain_codes.count(code) > 1})
    if duplicate_codes:
        findings.append(f"Duplicate domain error codes: {duplicate_codes}")

    return tuple(findings)


def serialize_problem_details_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_problem_details_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_problem_details_contract(build_problem_details_contract()),
        encoding="utf-8",
    )


def check_problem_details_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    findings = validate_problem_details_contract()
    if findings:
        return False, "Problem details contract violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Problem details contract does not exist: {output_path}"

    expected = serialize_problem_details_contract(build_problem_details_contract())
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Problem details contract is stale: {output_path}"
    return True, f"Problem details contract is current: {output_path}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ForgeML API problem details contract.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in problem details contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in problem details contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_problem_details_contract(args.output)
        print(f"Wrote problem details contract: {args.output}")
        return 0

    passed, detail = check_problem_details_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
