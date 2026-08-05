from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_PATH = Path("contracts/ops/release-evidence-workflow.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")
RELEASE_EVIDENCE_WORKFLOW_CONTRACT_VERSION = "forgeml.release_evidence_workflow.v1"
RELEASE_EVIDENCE_JOB_NAME = "release-evidence"
RELEASE_EVIDENCE_MANIFEST_PATH = "dist/release/forgeml-release-manifest.json"
RELEASE_EVIDENCE_ARTIFACT_NAME = "forgeml-release-manifest"
REQUIRED_RELEASE_EVIDENCE_NEEDS = (
    "backend",
    "frontend",
    "docker",
    "production-readiness",
)
REQUIRED_WORKFLOW_FRAGMENTS = (
    "release-evidence:",
    "needs: [backend, frontend, docker, production-readiness]",
    "github.event_name == 'push'",
    "github.ref == 'refs/heads/main'",
    "python scripts/ops/build_release_manifest.py",
    "--output dist/release/forgeml-release-manifest.json",
    '--git-sha "$GITHUB_SHA"',
    '--git-branch "$GITHUB_REF_NAME"',
    '--ci-run-url "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"',
    "actions/upload-artifact@v4",
    "name: forgeml-release-manifest",
    "path: dist/release/forgeml-release-manifest.json",
    "if-no-files-found: error",
)


def build_release_evidence_workflow_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_EVIDENCE_WORKFLOW_CONTRACT_VERSION,
        "generated_from": [".github/workflows/ci.yml", "scripts.ops.build_release_manifest"],
        "job_name": RELEASE_EVIDENCE_JOB_NAME,
        "manifest_path": RELEASE_EVIDENCE_MANIFEST_PATH,
        "artifact_name": RELEASE_EVIDENCE_ARTIFACT_NAME,
        "required_needs": list(REQUIRED_RELEASE_EVIDENCE_NEEDS),
        "required_fragments": list(REQUIRED_WORKFLOW_FRAGMENTS),
        "summary": {
            "required_need_count": len(REQUIRED_RELEASE_EVIDENCE_NEEDS),
            "required_fragment_count": len(REQUIRED_WORKFLOW_FRAGMENTS),
        },
    }


def serialize_release_evidence_workflow_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_evidence_workflow_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_release_evidence_workflow_contract(
            build_release_evidence_workflow_contract()
        ),
        encoding="utf-8",
    )


def check_release_evidence_workflow_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
) -> tuple[bool, str]:
    findings: list[str] = []
    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        findings.extend(validate_release_evidence_workflow(ci_path.read_text(encoding="utf-8")))

    if not output_path.is_file():
        findings.append(f"Release evidence workflow contract does not exist: {output_path}")
    else:
        expected = serialize_release_evidence_workflow_contract(
            build_release_evidence_workflow_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Release evidence workflow contract is stale: {output_path}")

    if findings:
        return False, "Release evidence workflow violations: " + "; ".join(findings)
    return True, f"Release evidence workflow contract is current: {output_path}"


def validate_release_evidence_workflow(ci_source: str) -> tuple[str, ...]:
    findings: list[str] = []
    missing_fragments = [
        fragment for fragment in REQUIRED_WORKFLOW_FRAGMENTS if fragment not in ci_source
    ]
    if missing_fragments:
        findings.append(f"Release evidence workflow missing fragments: {missing_fragments}")

    if "actions/upload-artifact@v4" in ci_source and "if-no-files-found: error" not in ci_source:
        findings.append("Release manifest artifact upload must fail when the file is absent.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ForgeML CI release evidence publication."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in release evidence workflow contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in release evidence workflow contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_release_evidence_workflow_contract(args.output)
        print(f"Wrote release evidence workflow contract: {args.output}")
        return 0

    passed, detail = check_release_evidence_workflow_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
