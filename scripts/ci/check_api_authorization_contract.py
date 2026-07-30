from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from forgeml.main import create_app
from forgeml.platform.api.dependencies import get_current_principal
from forgeml.platform.config import Settings

DEFAULT_OUTPUT_PATH = Path("contracts/security/api-authorization.v1.json")
PUBLIC_ROUTE_REASONS = {
    ("GET", "/health/live"): "Kubernetes and local liveness probe.",
    ("GET", "/health/ready"): "Kubernetes and local readiness probe.",
    ("GET", "/metrics"): "Prometheus scrape endpoint.",
    ("POST", "/api/v1/auth/login"): "Credential exchange endpoint.",
    ("POST", "/api/v1/auth/refresh"): "Refresh token exchange endpoint.",
    ("POST", "/api/v1/auth/logout"): "Refresh token revocation endpoint.",
}


@dataclass(frozen=True)
class RouteAuthorizationRecord:
    method: str
    path: str
    operation_id: str
    tags: tuple[str, ...]
    authorization: str
    reason: str


def build_authorization_manifest() -> dict[str, Any]:
    records = list_route_authorization_records()
    public_routes = [
        _record_to_contract(record) for record in records if record.authorization == "public"
    ]
    protected_routes = [
        _record_to_contract(record) for record in records if record.authorization == "principal"
    ]
    return {
        "schema_version": "forgeml.api_authorization.v1",
        "generated_from": "forgeml.main:create_app",
        "public_route_policy": {
            "description": (
                "Only explicitly allowlisted endpoints may be reachable without a "
                "validated JWT principal."
            ),
            "allowlist": [
                {
                    "method": method,
                    "path": path,
                    "reason": reason,
                }
                for (method, path), reason in sorted(PUBLIC_ROUTE_REASONS.items())
            ],
        },
        "summary": {
            "public_route_count": len(public_routes),
            "protected_route_count": len(protected_routes),
            "total_route_count": len(records),
        },
        "public_routes": public_routes,
        "protected_routes": protected_routes,
    }


def list_route_authorization_records() -> tuple[RouteAuthorizationRecord, ...]:
    app = create_app(Settings(environment="contract", enable_docs=False, rate_limit_enabled=False))
    records: list[RouteAuthorizationRecord] = []
    for route in _iter_api_routes(app.routes):
        requires_principal = _requires_current_principal(route)
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            route_key = (method, route.path_format)
            public_reason = PUBLIC_ROUTE_REASONS.get(route_key)
            records.append(
                RouteAuthorizationRecord(
                    method=method,
                    path=route.path_format,
                    operation_id=route.unique_id,
                    tags=tuple(sorted(str(tag) for tag in route.tags)),
                    authorization="principal" if requires_principal else "public",
                    reason=(
                        "Requires get_current_principal dependency."
                        if requires_principal
                        else public_reason or "Not in public route allowlist."
                    ),
                )
            )
    return tuple(sorted(records, key=lambda record: (record.path, record.method)))


def _record_to_contract(record: RouteAuthorizationRecord) -> dict[str, Any]:
    return {
        "authorization": record.authorization,
        "method": record.method,
        "operation_id": record.operation_id,
        "path": record.path,
        "reason": record.reason,
        "tags": list(record.tags),
    }


def _iter_api_routes(routes: list[Any]) -> tuple[Any, ...]:
    api_routes: list[Any] = []
    for route in routes:
        if isinstance(route, APIRoute):
            api_routes.append(route)
            continue
        if hasattr(route, "effective_route_contexts"):
            api_routes.extend(route.effective_route_contexts())
    return tuple(api_routes)


def validate_authorization_records(
    records: tuple[RouteAuthorizationRecord, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    observed_public_routes: set[tuple[str, str]] = set()
    observed_route_keys = {(record.method, record.path) for record in records}

    for record in records:
        route_key = (record.method, record.path)
        allowlisted = route_key in PUBLIC_ROUTE_REASONS
        if record.authorization == "public":
            observed_public_routes.add(route_key)
            if not allowlisted:
                findings.append(f"{record.method} {record.path} is public but is not allowlisted.")
        elif allowlisted:
            findings.append(
                f"{record.method} {record.path} is allowlisted public but requires a principal."
            )

    missing_public_routes = sorted(set(PUBLIC_ROUTE_REASONS) - observed_route_keys)
    for method, path in missing_public_routes:
        findings.append(f"{method} {path} is configured public but no route exists.")

    missing_from_public_contract = sorted(set(PUBLIC_ROUTE_REASONS) - observed_public_routes)
    for method, path in missing_from_public_contract:
        if (method, path) in observed_route_keys:
            findings.append(f"{method} {path} is no longer public but remains allowlisted.")

    return tuple(findings)


def serialize_authorization_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def write_authorization_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_authorization_manifest(build_authorization_manifest()),
        encoding="utf-8",
    )


def check_authorization_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[bool, str]:
    records = list_route_authorization_records()
    findings = validate_authorization_records(records)
    if findings:
        return False, "Authorization policy violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Authorization contract does not exist: {output_path}"

    expected = serialize_authorization_manifest(build_authorization_manifest())
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Authorization contract is stale: {output_path}"
    return True, f"API authorization contract is current: {output_path}"


def _requires_current_principal(route: Any) -> bool:
    return _dependant_tree_contains_call(route.dependant, get_current_principal)


def _dependant_tree_contains_call(dependant: Any, target: object) -> bool:
    if getattr(dependant, "call", None) is target:
        return True
    return any(
        _dependant_tree_contains_call(child, target)
        for child in getattr(dependant, "dependencies", [])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML API routes have explicit authentication posture."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in API authorization contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in API authorization contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_authorization_contract(args.output)
        print(f"Wrote API authorization contract: {args.output}")
        return 0

    passed, detail = check_authorization_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
