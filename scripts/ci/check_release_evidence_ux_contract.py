from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RELEASE_EVIDENCE_UX_CONTRACT_SCHEMA_VERSION = "forgeml.release_evidence_ux_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-ux.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "frontend/src/app/navigation.ts",
    "frontend/src/app/routes.tsx",
    "frontend/tests/e2e/smoke.spec.ts",
    "frontend/tests/e2e/demo-screenshots.spec.ts",
    "docs/portfolio/screenshot-catalog.md",
    "docs/portfolio/evidence-map.md",
)


def build_release_evidence_ux_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_UX_CONTRACT_SCHEMA_VERSION,
        "generated_from": [
            "frontend.modules.release_evidence",
            "frontend.app.navigation",
            "frontend.app.routes",
            "frontend.tests.e2e.demo-screenshots",
            "docs.portfolio.screenshot-catalog",
        ],
        "route": {
            "path": "/release-evidence",
            "label": "Release Evidence",
            "navigation_icon": "FileCheck2",
        },
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "required_ui_sections": [
            "Release Manifest",
            "Reviewer Commands",
            "Quality Gate Coverage",
            "Demo Screenshot Evidence",
        ],
        "required_release_signals": [
            "forgeml-release-manifest",
            "dist/release/forgeml-release-manifest.json",
            "contracts/ops/release-manifest.v1.json",
            "contracts/ops/portfolio-readiness.v1.json",
            "release_manifest_verifier_contract",
            "make production-readiness",
            "make demo-screenshots",
            "09-release-evidence.png",
        ],
        "operator_commands": [
            "PYTHONPATH=. python scripts/ci/check_release_evidence_ux_contract.py",
            "make production-readiness",
            "make demo-screenshots",
        ],
        "quality_gates": [
            "python scripts/ci/check_release_evidence_ux_contract.py",
            "backend/tests/unit/ops/test_release_evidence_ux_contract.py",
            "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
            "frontend/tests/e2e/smoke.spec.ts",
            "frontend/tests/e2e/demo-screenshots.spec.ts",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "ui_section_count": 4,
            "release_signal_count": 8,
        },
    }


def serialize_release_evidence_ux_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_ux_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_ux_contract(build_release_evidence_ux_contract()),
        encoding="utf-8",
    )


def check_release_evidence_ux_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_evidence_ux_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Release evidence UX contract does not exist: {output_path}")
    else:
        expected = serialize_release_evidence_ux_contract(
            build_release_evidence_ux_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release evidence UX contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_release_evidence_ux_contract.py" not in ci_source:
            findings.append("Release evidence UX contract checker is not wired into CI.")

    if findings:
        return False, "Release evidence UX violations: " + "; ".join(findings)
    return True, f"Release evidence UX contract is current: {output_path}"


def validate_release_evidence_ux_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_release_evidence_ux_contract()

    for source_asset in contract["required_source_assets"]:
        asset_path = repo_root / source_asset
        if not asset_path.is_file():
            findings.append(f"Missing release evidence UX source asset: {source_asset}")

    page_source = _read(
        repo_root, "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx"
    )
    page_test_source = _read(
        repo_root, "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx"
    )
    data_source = _read(
        repo_root, "frontend/src/modules/release_evidence/data/releaseEvidence.ts"
    )
    routes_source = _read(repo_root, "frontend/src/app/routes.tsx")
    navigation_source = _read(repo_root, "frontend/src/app/navigation.ts")
    smoke_source = _read(repo_root, "frontend/tests/e2e/smoke.spec.ts")
    screenshots_source = _read(repo_root, "frontend/tests/e2e/demo-screenshots.spec.ts")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")

    required_page_fragments = [
        "Release Evidence",
        *contract["required_ui_sections"],
        *contract["required_release_signals"],
    ]
    missing_page_fragments = [
        fragment
        for fragment in required_page_fragments
        if fragment not in page_source and fragment not in data_source
    ]
    if missing_page_fragments:
        findings.append(
            f"Release evidence page is missing fragments: {missing_page_fragments}"
        )

    required_route_fragments = [
        'path: "/release-evidence"',
        "loadReleaseEvidencePage",
        "ReleaseEvidencePage",
    ]
    missing_route_fragments = [
        fragment for fragment in required_route_fragments if fragment not in routes_source
    ]
    if missing_route_fragments:
        findings.append(f"Release evidence route is missing fragments: {missing_route_fragments}")

    required_navigation_fragments = [
        'label: "Release Evidence"',
        'path: "/release-evidence"',
        "FileCheck2",
    ]
    missing_navigation_fragments = [
        fragment for fragment in required_navigation_fragments if fragment not in navigation_source
    ]
    if missing_navigation_fragments:
        findings.append(
            f"Release evidence navigation is missing fragments: {missing_navigation_fragments}"
        )

    if "Release Evidence" not in smoke_source:
        findings.append("Playwright smoke test does not navigate to Release Evidence.")
    if "09-release-evidence.png" not in screenshots_source:
        findings.append("Demo screenshot flow does not capture Release Evidence.")
    if "09-release-evidence.png" not in screenshot_catalog_source:
        findings.append("Screenshot catalog does not list Release Evidence.")
    if "Release evidence UX" not in evidence_map_source:
        findings.append("Evidence map does not mention the Release evidence UX.")
    if "release_manifest_verifier_contract" not in page_test_source:
        findings.append("Release evidence page unit test does not cover quality gates.")

    if contract["schema_version"] != RELEASE_EVIDENCE_UX_CONTRACT_SCHEMA_VERSION:
        findings.append("Release evidence UX contract schema version is inconsistent.")

    return tuple(findings)


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML release evidence frontend workflow."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence UX contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence UX contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_ux_contract(args.output)
        print(f"Wrote release evidence UX contract: {args.output}")
        return 0

    passed, detail = check_release_evidence_ux_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
