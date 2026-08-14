from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

OPERATIONAL_AUDIT_UX_CONTRACT_SCHEMA_VERSION = "forgeml.operational_audit_ux_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/operational-audit-ux.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "frontend/src/modules/operational_audit/pages/OperationalAuditPage.tsx",
    "frontend/src/modules/operational_audit/pages/OperationalAuditPage.test.tsx",
    "frontend/src/modules/operational_audit/lib/auditTimeline.ts",
    "frontend/src/modules/operational_audit/lib/auditTimeline.test.ts",
    "frontend/src/modules/operational_audit/data/releaseEvidenceAuditEvents.ts",
    "frontend/src/modules/settings/api/auditLog.ts",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/tests/e2e/smoke.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "frontend/tests/e2e/fixtures/forgemlApiMock.ts",
    "docs/portfolio/screenshot-catalog.md",
    "docs/portfolio/evidence-map.md",
)


def build_operational_audit_ux_contract() -> dict[str, Any]:
    return {
        "schema_version": OPERATIONAL_AUDIT_UX_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "frontend.modules.operational_audit",
            "frontend.modules.settings.api.auditLog",
            "frontend.app.navigation",
            "frontend.app.routes",
            "frontend.tests.e2e.demo-screenshots",
            "docs.portfolio.screenshot-catalog",
        ],
        "route": {
            "path": "/operational-audit",
            "label": "Operational Audit",
            "navigation_icon": "ClipboardList",
        },
        "api_surface": ["GET /api/v1/admin/audit-log"],
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "required_ui_sections": [
            "Audit Timeline",
            "Event Detail",
            "Release Evidence",
            "Live Audit Events",
        ],
        "required_signal_families": [
            "release_evidence",
            "deployment",
            "retraining",
            "security",
            "training",
            "registry",
            "dataset",
            "monitoring",
        ],
        "required_release_signals": [
            "forgeml-release-manifest",
            "release_evidence.manifest_published",
            "release_manifest_verifier_contract",
            "10-operational-audit.png",
            "operational_audit_ux_contract",
        ],
        "operator_commands": [
            "PYTHONPATH=. python scripts/ci/check_operational_audit_ux_contract.py",
            "make demo-screenshots",
            "make production-readiness",
        ],
        "quality_gates": [
            "python scripts/ci/check_operational_audit_ux_contract.py",
            "backend/tests/unit/ops/test_operational_audit_ux_contract.py",
            "frontend/src/modules/operational_audit/pages/OperationalAuditPage.test.tsx",
            "frontend/src/modules/operational_audit/lib/auditTimeline.test.ts",
            "frontend/tests/e2e/smoke.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "ui_section_count": 4,
            "signal_family_count": 8,
            "release_signal_count": 5,
        },
    }


def serialize_operational_audit_ux_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_operational_audit_ux_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_operational_audit_ux_contract(build_operational_audit_ux_contract()),
        encoding="utf-8",
    )


def check_operational_audit_ux_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_operational_audit_ux_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Operational audit UX contract does not exist: {output_path}")
    else:
        expected = serialize_operational_audit_ux_contract(
            build_operational_audit_ux_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Operational audit UX contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_operational_audit_ux_contract.py" not in ci_source:
            findings.append("Operational audit UX contract checker is not wired into CI.")

    if findings:
        return False, "Operational audit UX violations: " + "; ".join(findings)
    return True, f"Operational audit UX contract is current: {output_path}"


def validate_operational_audit_ux_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_operational_audit_ux_contract()

    for source_asset in contract["required_source_assets"]:
        asset_path = repo_root / source_asset
        if not asset_path.is_file():
            findings.append(f"Missing operational audit UX source asset: {source_asset}")

    page_source = _read(
        repo_root, "frontend/src/modules/operational_audit/pages/OperationalAuditPage.tsx"
    )
    page_test_source = _read(
        repo_root, "frontend/src/modules/operational_audit/pages/OperationalAuditPage.test.tsx"
    )
    lib_source = _read(repo_root, "frontend/src/modules/operational_audit/lib/auditTimeline.ts")
    lib_test_source = _read(
        repo_root, "frontend/src/modules/operational_audit/lib/auditTimeline.test.ts"
    )
    data_source = _read(
        repo_root,
        "frontend/src/modules/operational_audit/data/releaseEvidenceAuditEvents.ts",
    )
    routes_source = _read(repo_root, "frontend/src/app/routes.tsx")
    navigation_source = _read(repo_root, "frontend/src/app/navigation.ts")
    smoke_source = _read(repo_root, "frontend/tests/e2e/smoke.spec.ts")
    screenshots_source = _read(repo_root, "frontend/tests/e2e/demo-screenshots.spec.ts")
    mock_source = _read(repo_root, "frontend/tests/e2e/fixtures/forgemlApiMock.ts")
    release_evidence_source = _read(
        repo_root, "frontend/src/modules/release_evidence/data/releaseEvidence.ts"
    )
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")

    required_page_fragments = [
        "Operational Audit",
        *contract["required_ui_sections"],
        "listAuditLog",
        "releaseEvidenceAuditEvents",
    ]
    missing_page_fragments = [
        fragment for fragment in required_page_fragments if fragment not in page_source
    ]
    if missing_page_fragments:
        findings.append(
            f"Operational audit page is missing fragments: {missing_page_fragments}"
        )

    missing_family_fragments = [
        family for family in contract["required_signal_families"] if family not in lib_source
    ]
    if missing_family_fragments:
        findings.append(
            f"Operational audit adapter is missing families: {missing_family_fragments}"
        )

    required_route_fragments = [
        'path: "/operational-audit"',
        "loadOperationalAuditPage",
        "OperationalAuditPage",
    ]
    missing_route_fragments = [
        fragment for fragment in required_route_fragments if fragment not in routes_source
    ]
    if missing_route_fragments:
        findings.append(f"Operational audit route is missing fragments: {missing_route_fragments}")

    required_navigation_fragments = [
        'label: "Operational Audit"',
        'path: "/operational-audit"',
        "ClipboardList",
    ]
    missing_navigation_fragments = [
        fragment for fragment in required_navigation_fragments if fragment not in navigation_source
    ]
    if missing_navigation_fragments:
        findings.append(
            f"Operational audit navigation is missing fragments: {missing_navigation_fragments}"
        )

    required_release_fragments = [
        "release_evidence.manifest_published",
        "release_manifest_verifier_contract",
    ]
    missing_release_fragments = [
        fragment for fragment in required_release_fragments if fragment not in data_source
    ]
    if missing_release_fragments:
        findings.append(
            f"Operational audit release annotations are missing: {missing_release_fragments}"
        )

    if "Operational Audit" not in smoke_source:
        findings.append("Playwright smoke test does not navigate to Operational Audit.")
    if "10-operational-audit.png" not in screenshots_source:
        findings.append("Demo screenshot flow does not capture Operational Audit.")
    if "/api/v1/admin/audit-log" not in mock_source:
        findings.append("E2E API mock does not serve admin audit log events.")
    if "Deployments - Rollback" not in page_test_source:
        findings.append("Operational audit page test does not cover live audit rows.")
    if "release_evidence" not in lib_test_source or "deployment" not in lib_test_source:
        findings.append("Operational audit adapter test does not cover signal families.")
    if "10-operational-audit.png" not in screenshot_catalog_source:
        findings.append("Screenshot catalog does not list Operational Audit.")
    if "Operational audit UX" not in evidence_map_source:
        findings.append("Evidence map does not mention the Operational audit UX.")
    if "operational_audit_ux_contract" not in release_evidence_source:
        findings.append("Release Evidence page data does not include the operational audit gate.")

    if contract["schema_version"] != OPERATIONAL_AUDIT_UX_CONTRACT_SCHEMA_VERSION:
        findings.append("Operational audit UX contract schema version is inconsistent.")

    return tuple(findings)


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML operational audit frontend workflow."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in operational audit UX contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in operational audit UX contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_operational_audit_ux_contract(args.output)
        print(f"Wrote operational audit UX contract: {args.output}")
        return 0

    passed, detail = check_operational_audit_ux_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
