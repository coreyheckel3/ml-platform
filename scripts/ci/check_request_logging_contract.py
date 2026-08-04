from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from forgeml.platform.observability.logging import (
    REDACTED_VALUE,
    REQUEST_LOG_REQUIRED_HTTP_FIELDS,
    REQUEST_LOG_REQUIRED_TOP_LEVEL_FIELDS,
    REQUEST_LOG_SCHEMA_VERSION,
    SENSITIVE_FIELD_MARKERS,
    build_http_request_log_event,
)

DEFAULT_OUTPUT_PATH = Path("contracts/observability/request-log-event.v1.json")


def build_request_logging_contract() -> dict[str, Any]:
    return {
        "schema_version": "forgeml.request_logging_contract.v1",
        "event_schema_version": REQUEST_LOG_SCHEMA_VERSION,
        "generated_from": ["forgeml.platform.observability.logging"],
        "summary": {
            "required_top_level_field_count": len(REQUEST_LOG_REQUIRED_TOP_LEVEL_FIELDS),
            "required_http_field_count": len(REQUEST_LOG_REQUIRED_HTTP_FIELDS),
            "sensitive_field_marker_count": len(SENSITIVE_FIELD_MARKERS),
        },
        "required_top_level_fields": sorted(REQUEST_LOG_REQUIRED_TOP_LEVEL_FIELDS),
        "required_http_fields": sorted(REQUEST_LOG_REQUIRED_HTTP_FIELDS),
        "redaction": {
            "replacement": REDACTED_VALUE,
            "sensitive_field_markers": sorted(SENSITIVE_FIELD_MARKERS),
        },
    }


def validate_request_logging_contract() -> tuple[str, ...]:
    findings: list[str] = []
    event = build_http_request_log_event(
        service="forgeml-api",
        environment="production",
        trace_id="trace-123",
        method="GET",
        route="/api/v1/projects",
        path="/api/v1/projects",
        status_code=200,
        duration_seconds=0.0123,
        client_host="203.0.113.10",
        query_params=[
            ("project", "fraud"),
            ("access_token", "sensitive-token"),
            ("password", "sensitive-password"),
        ],
    )

    missing_top_level = sorted(set(REQUEST_LOG_REQUIRED_TOP_LEVEL_FIELDS) - set(event))
    if missing_top_level:
        findings.append(f"Request log event missing top-level fields: {missing_top_level}")

    http_fields = event.get("http", {})
    if not isinstance(http_fields, dict):
        findings.append("Request log event http field is not an object.")
        return tuple(findings)

    missing_http = sorted(set(REQUEST_LOG_REQUIRED_HTTP_FIELDS) - set(http_fields))
    if missing_http:
        findings.append(f"Request log event missing HTTP fields: {missing_http}")

    query_params = http_fields.get("query_params", {})
    if not isinstance(query_params, dict):
        findings.append("Request log event query_params field is not an object.")
        return tuple(findings)

    if query_params.get("project") != "fraud":
        findings.append("Non-sensitive query parameter was not preserved.")
    if query_params.get("access_token") != REDACTED_VALUE:
        findings.append("Sensitive access_token query parameter was not redacted.")
    if query_params.get("password") != REDACTED_VALUE:
        findings.append("Sensitive password query parameter was not redacted.")

    return tuple(findings)


def serialize_request_logging_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_request_logging_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_request_logging_contract(build_request_logging_contract()),
        encoding="utf-8",
    )


def check_request_logging_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    findings = validate_request_logging_contract()
    if findings:
        return False, "Request logging contract violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Request logging contract does not exist: {output_path}"

    expected = serialize_request_logging_contract(build_request_logging_contract())
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Request logging contract is stale: {output_path}"
    return True, f"Request logging contract is current: {output_path}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML structured request logging contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in request logging contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in request logging contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_request_logging_contract(args.output)
        print(f"Wrote request logging contract: {args.output}")
        return 0

    passed, detail = check_request_logging_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
