from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RELEASE_EVIDENCE_RETRIEVAL_CONTRACT_SCHEMA_VERSION = (
    "forgeml.release_evidence_retrieval_contract.v1"
)
RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION = "forgeml.release_evidence_retrieval.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-retrieval.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SOURCE_ASSETS = (
    "backend/src/forgeml/platform/release_evidence/__init__.py",
    "backend/src/forgeml/platform/release_evidence/retrieval.py",
    "backend/tests/unit/platform/test_release_evidence_retrieval.py",
    "backend/tests/unit/ops/test_release_evidence_retrieval_cli.py",
    "backend/tests/unit/ops/test_release_evidence_retrieval_contract.py",
    "scripts/ops/retrieve_release_evidence.py",
    "scripts/ci/check_release_evidence_retrieval_contract.py",
    "frontend/src/modules/release_evidence/data/releaseEvidence.ts",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx",
    "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
    "docs/runbooks/production-readiness.md",
    "docs/portfolio/evidence-map.md",
    "docs/portfolio/screenshot-catalog.md",
    "contracts/ops/README.md",
)

REQUIRED_RETRIEVER_FRAGMENTS = (
    "ReleaseEvidenceGateway",
    "GitHubActionsReleaseEvidenceGateway",
    "LocalReleaseEvidenceGateway",
    "ReleaseEvidenceComparison",
    "compare_release_manifest_to_contract",
    "archive_download_url",
    "Authorization",
    "zipfile",
)

REQUIRED_CLI_FRAGMENTS = (
    "RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION",
    "GitHubActionsReleaseEvidenceGateway",
    "LocalReleaseEvidenceGateway",
    "--repo",
    "--manifest",
    "GITHUB_TOKEN",
)

REQUIRED_COMPARISON_CHECKS = (
    "manifest_schema_version",
    "main_branch_source",
    "required_artifact_coverage",
    "required_quality_gate_coverage",
    "ci_run_url_present",
)


def build_release_evidence_retrieval_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_RETRIEVAL_CONTRACT_SCHEMA_VERSION,
        "retrieval_schema_version": RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.release_evidence.retrieval",
            "scripts.ops.retrieve_release_evidence",
            "frontend.modules.release_evidence",
        ],
        "retrieval_boundary": {
            "gateway_protocol": "ReleaseEvidenceGateway",
            "github_gateway": "GitHubActionsReleaseEvidenceGateway",
            "local_gateway": "LocalReleaseEvidenceGateway",
            "default_branch": "main",
            "workflow_file": "ci.yml",
            "artifact_name": "forgeml-release-manifest",
        },
        "operator_command": (
            "PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py "
            "--repo coreyheckel3/ml-platform --branch main --workflow ci.yml "
            "--artifact-name forgeml-release-manifest"
        ),
        "local_comparison_command": (
            "PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py "
            "--manifest dist/release/forgeml-release-manifest.json"
        ),
        "required_source_assets": list(REQUIRED_SOURCE_ASSETS),
        "required_retriever_fragments": list(REQUIRED_RETRIEVER_FRAGMENTS),
        "required_cli_fragments": list(REQUIRED_CLI_FRAGMENTS),
        "required_comparison_checks": list(REQUIRED_COMPARISON_CHECKS),
        "required_ui_sections": [
            "Live Evidence Retrieval",
            "Comparison Signals",
        ],
        "required_release_signals": [
            "GitHub Actions",
            "GitHubActionsReleaseEvidenceGateway",
            "forgeml-release-manifest",
            "release_evidence_retrieval_contract",
            "contracts/ops/release-evidence-retrieval.v1.json",
            "scripts/ops/retrieve_release_evidence.py --repo",
        ],
        "quality_gates": [
            "python scripts/ci/check_release_evidence_retrieval_contract.py",
            "backend/tests/unit/platform/test_release_evidence_retrieval.py",
            "backend/tests/unit/ops/test_release_evidence_retrieval_cli.py",
            "backend/tests/unit/ops/test_release_evidence_retrieval_contract.py",
            "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.test.tsx",
        ],
        "summary": {
            "source_asset_count": len(REQUIRED_SOURCE_ASSETS),
            "comparison_check_count": len(REQUIRED_COMPARISON_CHECKS),
            "quality_gate_count": 5,
        },
    }


def serialize_release_evidence_retrieval_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_retrieval_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_retrieval_contract(
            build_release_evidence_retrieval_contract()
        ),
        encoding="utf-8",
    )


def check_release_evidence_retrieval_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_release_evidence_retrieval_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Release evidence retrieval contract does not exist: {output_path}")
    else:
        expected = serialize_release_evidence_retrieval_contract(
            build_release_evidence_retrieval_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release evidence retrieval contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_release_evidence_retrieval_contract.py" not in ci_source:
            findings.append("Release evidence retrieval checker is not wired into CI.")

    if findings:
        return False, "Release evidence retrieval violations: " + "; ".join(findings)
    return True, f"Release evidence retrieval contract is current: {output_path}"


def validate_release_evidence_retrieval_definition(
    repo_root: Path = REPO_ROOT,
) -> tuple[str, ...]:
    findings: list[str] = []
    contract = build_release_evidence_retrieval_contract()

    for source_asset in contract["required_source_assets"]:
        if not (repo_root / source_asset).is_file():
            findings.append(f"Missing release evidence retrieval source asset: {source_asset}")

    retriever_source = _read(
        repo_root,
        "backend/src/forgeml/platform/release_evidence/retrieval.py",
    )
    cli_source = _read(repo_root, "scripts/ops/retrieve_release_evidence.py")
    data_source = _read(
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
    runbook_source = _read(repo_root, "docs/runbooks/production-readiness.md")
    evidence_map_source = _read(repo_root, "docs/portfolio/evidence-map.md")
    screenshot_catalog_source = _read(repo_root, "docs/portfolio/screenshot-catalog.md")
    ops_readme_source = _read(repo_root, "contracts/ops/README.md")
    manifest_builder_source = _read(repo_root, "scripts/ops/build_release_manifest.py")

    missing_retriever_fragments = [
        fragment
        for fragment in contract["required_retriever_fragments"]
        if fragment not in retriever_source
    ]
    if missing_retriever_fragments:
        findings.append(
            "Release evidence retriever is missing fragments: "
            f"{missing_retriever_fragments}"
        )

    missing_cli_fragments = [
        fragment for fragment in contract["required_cli_fragments"] if fragment not in cli_source
    ]
    if missing_cli_fragments:
        findings.append(f"Release evidence CLI is missing fragments: {missing_cli_fragments}")

    required_page_fragments = [
        *contract["required_ui_sections"],
        *contract["required_release_signals"],
    ]
    missing_page_fragments = [
        fragment
        for fragment in required_page_fragments
        if fragment not in page_source
        and fragment not in data_source
        and fragment not in runbook_source
    ]
    if missing_page_fragments:
        findings.append(
            f"Release evidence retrieval UI is missing fragments: {missing_page_fragments}"
        )

    if "release_evidence_retrieval_contract" not in page_test_source:
        findings.append("Release evidence page test does not cover retrieval contract gate.")
    if "scripts/ops/retrieve_release_evidence.py --repo" not in runbook_source:
        findings.append("Production readiness runbook lacks live retrieval command.")
    if "Live release evidence retrieval" not in evidence_map_source:
        findings.append("Evidence map does not mention live release evidence retrieval.")
    if "09-release-evidence.png" not in screenshot_catalog_source:
        findings.append("Screenshot catalog does not list Release Evidence.")
    if "release-evidence-retrieval.v1.json" not in ops_readme_source:
        findings.append("Operations contracts README does not document retrieval contract.")
    if "release_evidence_retrieval_contract" not in manifest_builder_source:
        findings.append("Release manifest does not include retrieval contract evidence.")

    boundary = contract["retrieval_boundary"]
    if boundary.get("gateway_protocol") != "ReleaseEvidenceGateway":
        findings.append("Retrieval contract gateway boundary is inconsistent.")
    if boundary.get("github_gateway") != "GitHubActionsReleaseEvidenceGateway":
        findings.append("Retrieval contract GitHub adapter is inconsistent.")
    if boundary.get("artifact_name") != "forgeml-release-manifest":
        findings.append("Retrieval contract artifact name is inconsistent.")

    if contract["schema_version"] != RELEASE_EVIDENCE_RETRIEVAL_CONTRACT_SCHEMA_VERSION:
        findings.append("Release evidence retrieval contract schema version is inconsistent.")
    if contract["retrieval_schema_version"] != RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION:
        findings.append("Release evidence retrieval report schema version is inconsistent.")

    return tuple(findings)


def _read(repo_root: Path, path: str) -> str:
    file_path = repo_root / path
    if not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML release evidence retrieval contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence retrieval contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence retrieval contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_retrieval_contract(args.output)
        print(f"Wrote release evidence retrieval contract: {args.output}")
        return 0

    passed, detail = check_release_evidence_retrieval_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
