import json
from pathlib import Path

from scripts.ci.check_api_authorization_contract import (
    PUBLIC_ROUTE_REASONS,
    RouteAuthorizationRecord,
    build_authorization_manifest,
    check_authorization_contract,
    serialize_authorization_manifest,
    validate_authorization_records,
    write_authorization_contract,
)


def test_authorization_manifest_classifies_public_and_protected_routes() -> None:
    manifest = build_authorization_manifest()
    public_routes = {(route["method"], route["path"]) for route in manifest["public_routes"]}
    protected_routes = {(route["method"], route["path"]) for route in manifest["protected_routes"]}

    assert public_routes == set(PUBLIC_ROUTE_REASONS)
    assert ("GET", "/api/v1/auth/me") in protected_routes
    assert ("POST", "/api/v1/projects/{project_id}/training-runs") in protected_routes
    assert ("POST", "/api/v1/inference-endpoints/{endpoint_id}/predict") in protected_routes


def test_authorization_contract_rejects_unallowlisted_public_route() -> None:
    findings = validate_authorization_records(
        (
            RouteAuthorizationRecord(
                method="GET",
                path="/api/v1/projects",
                operation_id="list_projects",
                tags=("projects",),
                authorization="public",
                reason="Not in public route allowlist.",
            ),
        )
    )

    assert "GET /api/v1/projects is public but is not allowlisted." in findings


def test_authorization_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "api-authorization.v1.json"

    write_authorization_contract(contract_path)

    passed, detail = check_authorization_contract(contract_path)
    assert passed
    assert str(contract_path) in detail


def test_authorization_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "api-authorization.v1.json"
    contract_path.write_text("{}", encoding="utf-8")

    passed, detail = check_authorization_contract(contract_path)

    assert not passed
    assert "stale" in detail


def test_checked_in_authorization_contract_matches_application_routes() -> None:
    contract_path = Path("contracts/security/api-authorization.v1.json")
    passed, detail = check_authorization_contract(contract_path)

    assert passed, detail


def test_authorization_contract_serialization_is_deterministic() -> None:
    manifest = build_authorization_manifest()

    serialized = serialize_authorization_manifest(manifest)

    assert serialized == serialize_authorization_manifest(manifest)
    assert json.loads(serialized) == manifest
