from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend/src"
for import_path in (REPO_ROOT, BACKEND_SRC):
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)

from scripts.ops.build_release_manifest import (  # noqa: E402
    REQUIRED_QUALITY_GATES,
    REQUIRED_RELEASE_ARTIFACTS,
)

from forgeml.platform.release_evidence import (  # noqa: E402
    GitHubActionsReleaseEvidenceGateway,
    LocalReleaseEvidenceGateway,
    ReleaseEvidenceGateway,
    ReleaseEvidenceRetrievalError,
    compare_release_manifest_to_contract,
    summarize_release_manifest,
)

RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION = "forgeml.release_evidence_retrieval.v1"


def build_release_evidence_retrieval_report(
    gateway: ReleaseEvidenceGateway,
    *,
    required_artifacts: tuple[str, ...] = tuple(item.name for item in REQUIRED_RELEASE_ARTIFACTS),
    required_quality_gates: tuple[str, ...] = REQUIRED_QUALITY_GATES,
    expected_branch: str | None = "main",
) -> dict[str, Any]:
    run = gateway.latest_successful_run()
    manifest = gateway.download_release_manifest(run)
    summary = summarize_release_manifest(manifest)
    comparison = compare_release_manifest_to_contract(
        manifest,
        required_artifacts=required_artifacts,
        required_quality_gates=required_quality_gates,
        expected_branch=expected_branch,
    )
    return {
        "schema_version": RELEASE_EVIDENCE_RETRIEVAL_SCHEMA_VERSION,
        "status": "passed" if comparison.passed else "failed",
        "run": {
            "id": run.id,
            "head_sha": run.head_sha,
            "branch": run.branch,
            "status": run.status,
            "conclusion": run.conclusion,
            "html_url": run.html_url,
        },
        "manifest_summary": summary.as_dict(),
        "comparison": comparison.as_dict(),
    }


def serialize_release_evidence_retrieval_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Retrieve and compare ForgeML release evidence from GitHub Actions."
    )
    parser.add_argument("--repo", help="GitHub repository in owner/name format.")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument("--artifact-name", default="forgeml-release-manifest")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Use a local release manifest instead of calling GitHub Actions.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.manifest:
        gateway: ReleaseEvidenceGateway = LocalReleaseEvidenceGateway(
            args.manifest,
            branch=args.branch,
        )
        expected_branch: str | None = None
    else:
        if not args.repo:
            parser.error("--repo is required when --manifest is not provided")
        gateway = GitHubActionsReleaseEvidenceGateway(
            repository=args.repo,
            token=os.environ.get(args.token_env),
            branch=args.branch,
            workflow_file=args.workflow,
            artifact_name=args.artifact_name,
        )
        expected_branch = args.branch

    try:
        report = build_release_evidence_retrieval_report(
            gateway,
            expected_branch=expected_branch,
        )
    except ReleaseEvidenceRetrievalError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    output = serialize_release_evidence_retrieval_report(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
