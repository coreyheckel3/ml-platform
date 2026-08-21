from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RELEASE_EVIDENCE_NOTIFICATIONS_CONTRACT_SCHEMA_VERSION = (
    "forgeml.release_evidence_notifications_contract.v1"
)
DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-notifications.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_AUDIT_ACTIONS = (
    "release_evidence.notification_delivered",
    "release_evidence.notification_failed",
    "release_evidence.notification_skipped",
)
REQUIRED_CONFIG_VARS = (
    "FORGEML_RELEASE_EVIDENCE_NOTIFICATIONS_ENABLED",
    "FORGEML_RELEASE_EVIDENCE_NOTIFICATION_CHANNEL",
    "FORGEML_RELEASE_EVIDENCE_NOTIFICATION_WEBHOOK_URL",
    "FORGEML_RELEASE_EVIDENCE_NOTIFICATION_TIMEOUT_SECONDS",
    "FORGEML_RELEASE_EVIDENCE_NOTIFICATION_ESCALATION_WINDOW_SECONDS",
)
REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/platform/notifications/__init__.py",
    "backend/src/forgeml/platform/notifications/delivery.py",
    "backend/src/forgeml/platform/config.py",
    "backend/src/forgeml/modules/administration/application/services.py",
    "backend/src/forgeml/modules/administration/api/routes.py",
    "backend/src/forgeml/modules/administration/api/schemas.py",
    "backend/src/forgeml/platform/release_evidence/retrieval.py",
    "backend/tests/api/test_administration_api.py",
    "backend/tests/unit/administration/test_administration_service.py",
    "backend/tests/unit/ops/test_release_evidence_notifications_contract.py",
    "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "scripts/ops/build_release_manifest.py",
    "scripts/ci/production_readiness.py",
    "contracts/openapi/forgeml.v1.openapi.json",
    "contracts/ops/README.md",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/reviewer-guide.md",
    "README.md",
)


def build_release_evidence_notifications_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_NOTIFICATIONS_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.notifications",
            "forgeml.modules.administration",
            "frontend.modules.release_evidence",
        ],
        "notification_payload": {
            "schema_version": "forgeml.release_evidence_notification.v1",
            "trigger_statuses": ["failed"],
            "severity": "critical",
            "secret_handling": "webhook targets are redacted before API/UI/audit exposure",
        },
        "adapters": {
            "protocol": "ReleaseEvidenceNotificationGateway",
            "implementations": [
                "NoopReleaseEvidenceNotificationGateway",
                "WebhookReleaseEvidenceNotificationGateway",
            ],
            "default_mode": "audit_only",
        },
        "configuration": {
            "env_vars": list(REQUIRED_CONFIG_VARS),
            "allowed_channels": ["noop", "webhook"],
            "default_enabled": False,
        },
        "api": {
            "endpoint": "/api/v1/admin/release-evidence/refresh/status",
            "response_model": "ReleaseEvidenceRefreshStatusResponse",
            "response_field": "notification_policy",
            "permission": "admin:release_evidence:read",
        },
        "audit": {
            "resource_type": "release_evidence_notification",
            "actions": list(REQUIRED_AUDIT_ACTIONS),
            "delivery_statuses": ["delivered", "failed", "skipped"],
        },
        "ui": {
            "route": "/release-evidence",
            "section": "Notification Routing",
            "signals": [
                "Delivery Audit Records",
                "Escalation Command",
                "webhook active",
                "audit only",
            ],
        },
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "quality_gates": [
            "python scripts/ci/check_release_evidence_notifications_contract.py",
            "backend/tests/api/test_administration_api.py",
            "backend/tests/unit/administration/test_administration_service.py",
            "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
        ],
        "release_manifest": {
            "artifact_name": "release_evidence_notifications_contract",
            "quality_gate_name": "release_evidence_notifications_contract",
        },
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "audit_action_count": len(REQUIRED_AUDIT_ACTIONS),
            "config_var_count": len(REQUIRED_CONFIG_VARS),
        },
    }


def serialize_release_evidence_notifications_contract(
    contract: dict[str, Any],
) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_notifications_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_notifications_contract(
            build_release_evidence_notifications_contract()
        ),
        encoding="utf-8",
    )


def check_release_evidence_notifications_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_evidence_notifications_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Release evidence notifications contract does not exist: {output_path}")
    else:
        expected = serialize_release_evidence_notifications_contract(
            build_release_evidence_notifications_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release evidence notifications contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if (
            "python scripts/ci/check_release_evidence_notifications_contract.py"
            not in ci_source
        ):
            findings.append("Release evidence notifications checker is not wired into CI.")

    if findings:
        return False, "Release evidence notifications violations: " + "; ".join(findings)
    return True, f"Release evidence notifications contract is current: {output_path}"


def validate_release_evidence_notifications_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_release_evidence_notifications_contract()
    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing release evidence notifications asset: {source_asset}")

    delivery_source = _read(repo_root, "backend/src/forgeml/platform/notifications/delivery.py")
    config_source = _read(repo_root, "backend/src/forgeml/platform/config.py")
    service_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/application/services.py",
    )
    routes_source = _read(repo_root, "backend/src/forgeml/modules/administration/api/routes.py")
    schemas_source = _read(
        repo_root,
        "backend/src/forgeml/modules/administration/api/schemas.py",
    )
    retrieval_source = _read(
        repo_root,
        "backend/src/forgeml/platform/release_evidence/retrieval.py",
    )
    service_test_source = _read(
        repo_root,
        "backend/tests/unit/administration/test_administration_service.py",
    )
    api_test_source = _read(repo_root, "backend/tests/api/test_administration_api.py")
    frontend_api_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/api/releaseEvidence.ts",
    )
    frontend_data_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    )
    page_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    )
    page_test_source = _read(
        repo_root,
        "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    )
    e2e_mock_source = _read(repo_root, "frontend/tests/e2e/fixtures/forgemlApiMock.ts")
    manifest_source = _read(repo_root, "scripts/ops/build_release_manifest.py")
    production_readiness_source = _read(repo_root, "scripts/ci/production_readiness.py")
    ci_source = _read(repo_root, ".github/workflows/ci.yml")
    contracts_source = _read(repo_root, "contracts/ops/README.md")
    runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    reviewer_guide_source = _read(repo_root, "docs/portfolio/reviewer-guide.md")
    readme_source = _read(repo_root, "README.md")
    openapi_contract = _read_json(repo_root / "contracts/openapi/forgeml.v1.openapi.json")

    _require_fragments(
        findings,
        "notification delivery runtime",
        delivery_source,
        (
            "RELEASE_EVIDENCE_NOTIFICATION_SCHEMA_VERSION",
            "ReleaseEvidenceNotificationGateway",
            "NoopReleaseEvidenceNotificationGateway",
            "WebhookReleaseEvidenceNotificationGateway",
            "NotificationDeliveryResult",
        ),
    )
    _require_fragments(findings, "runtime config", config_source, REQUIRED_CONFIG_VARS)
    _require_fragments(
        findings,
        "administration service",
        service_source,
        (
            "_notify_failed_release_evidence",
            "ReleaseEvidenceNotificationPolicy",
            "release_evidence.notification_delivered",
            "release_evidence.notification_failed",
            "release_evidence.notification_skipped",
            "release_evidence_notification_for_report",
        ),
    )
    _require_fragments(
        findings,
        "administration routes",
        routes_source,
        (
            "_release_evidence_notification_gateway_from_settings",
            "_release_evidence_notification_policy_from_settings",
            "_redacted_webhook_target",
        ),
    )
    _require_fragments(
        findings,
        "administration schemas",
        schemas_source,
        (
            "ReleaseEvidenceNotificationPolicyResponse",
            "notification_policy",
        ),
    )
    _require_fragments(
        findings,
        "release evidence runtime",
        retrieval_source,
        ("release_evidence_notifications_contract",),
    )
    _require_fragments(
        findings,
        "service tests",
        service_test_source,
        (
            "test_administration_service_notifies_on_failed_release_evidence",
            "test_administration_service_audits_notification_delivery_failure",
            "FakeReleaseEvidenceNotificationGateway",
        ),
    )
    _require_fragments(
        findings,
        "API tests",
        api_test_source,
        ("notification_policy", "release_evidence.notification_failed"),
    )
    _require_fragments(
        findings,
        "frontend API client",
        frontend_api_source,
        ("ReleaseEvidenceNotificationPolicy", "notification_policy"),
    )
    _require_fragments(
        findings,
        "frontend data",
        frontend_data_source,
        (
            "Release Evidence Notifications Contract",
            "release_evidence_notifications_contract",
        ),
    )
    _require_fragments(
        findings,
        "release evidence page",
        page_source,
        (
            "Notification Routing",
            "Delivery Audit Records",
            "Escalation Command",
        ),
    )
    _require_fragments(
        findings,
        "release evidence page test",
        page_test_source,
        (
            "Delivery Audit Records",
            "release_evidence.notification_delivered",
            "Release Evidence Notifications Contract",
        ),
    )
    _require_fragments(
        findings,
        "Playwright API mock",
        e2e_mock_source,
        ("notification_policy", "release_evidence_notifications_contract"),
    )
    _require_fragments(
        findings,
        "release manifest builder",
        manifest_source,
        (
            "release_evidence_notifications_contract",
            "contracts/ops/release-evidence-notifications.v1.json",
        ),
    )
    _require_fragments(
        findings,
        "production readiness",
        production_readiness_source,
        ("check_release_evidence_notifications_contract",),
    )
    _require_fragments(
        findings,
        "CI workflow",
        ci_source,
        ("python scripts/ci/check_release_evidence_notifications_contract.py",),
    )
    _require_fragments(
        findings,
        "operations contracts README",
        contracts_source,
        ("release-evidence-notifications.v1.json",),
    )
    _require_fragments(
        findings,
        "production readiness runbook",
        runbook_source,
        (
            "FORGEML_RELEASE_EVIDENCE_NOTIFICATION_WEBHOOK_URL",
            "release_evidence.notification_failed",
        ),
    )
    _require_fragments(
        findings,
        "portfolio evidence map",
        evidence_map_source,
        ("Release evidence notifications",),
    )
    _require_fragments(
        findings,
        "portfolio reviewer guide",
        reviewer_guide_source,
        ("check_release_evidence_notifications_contract.py",),
    )
    _require_fragments(
        findings,
        "README",
        readme_source,
        ("check_release_evidence_notifications_contract.py",),
    )

    schemas = openapi_contract.get("components", {}).get("schemas", {})
    refresh_status_schema = schemas.get("ReleaseEvidenceRefreshStatusResponse", {})
    required_fields = refresh_status_schema.get("required", [])
    properties = refresh_status_schema.get("properties", {})
    if "notification_policy" not in required_fields:
        findings.append("OpenAPI refresh status response does not require notification_policy.")
    if "notification_policy" not in properties:
        findings.append("OpenAPI refresh status response is missing notification_policy.")

    return tuple(findings)


def _require_fragments(
    findings: list[str],
    label: str,
    source: str,
    fragments: tuple[str, ...],
) -> None:
    missing = [fragment for fragment in fragments if fragment not in source]
    if missing:
        findings.append(f"{label} is missing fragments: {missing}")


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release evidence notifications contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence notifications contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence notifications contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_notifications_contract(args.output)
        return 0

    passed, detail = check_release_evidence_notifications_contract(args.output)
    print(detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
