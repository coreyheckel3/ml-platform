from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ops.retrieve_release_evidence import (
    build_release_evidence_retrieval_report,
    main,
    serialize_release_evidence_retrieval_report,
)

from forgeml.platform.release_evidence import LocalReleaseEvidenceGateway


def test_release_evidence_retrieval_report_serializes_comparison(tmp_path: Path) -> None:
    manifest_path = tmp_path / "forgeml-release-manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    report = build_release_evidence_retrieval_report(
        LocalReleaseEvidenceGateway(manifest_path),
        required_artifacts=("openapi_contract",),
        required_quality_gates=("backend_tests",),
        expected_branch="main",
    )
    parsed = json.loads(serialize_release_evidence_retrieval_report(report))

    assert parsed["schema_version"] == "forgeml.release_evidence_retrieval.v1"
    assert parsed["status"] == "passed"
    assert parsed["comparison"]["passed"] is True
    assert parsed["manifest_summary"]["artifact_names"] == ["openapi_contract"]


def test_release_evidence_retrieval_cli_supports_local_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "forgeml-release-manifest.json"
    output_path = tmp_path / "retrieval-report.json"
    manifest_path.write_text(json.dumps(_manifest(include_all_required=True)), encoding="utf-8")

    exit_code = main(["--manifest", str(manifest_path), "--output", str(output_path)])

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["schema_version"] == "forgeml.release_evidence_retrieval.v1"
    assert report["comparison"]["passed"] is True


def _manifest(*, include_all_required: bool = False) -> dict[str, Any]:
    if include_all_required:
        from scripts.ops.build_release_manifest import (  # noqa: PLC0415
            REQUIRED_QUALITY_GATES,
            REQUIRED_RELEASE_ARTIFACTS,
        )

        artifact_names = tuple(item.name for item in REQUIRED_RELEASE_ARTIFACTS)
        quality_gate_names = REQUIRED_QUALITY_GATES
    else:
        artifact_names = ("openapi_contract",)
        quality_gate_names = ("backend_tests",)

    return {
        "schema_version": "forgeml.release_manifest.v1",
        "release": {
            "version": "0.1.0",
            "created_at": "2026-08-05T00:00:00Z",
            "ci_run_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/1",
        },
        "source": {"git_sha": "a" * 40, "git_branch": "main", "dirty": False},
        "artifacts": [{"name": name} for name in artifact_names],
        "quality_gates": [
            {"name": name, "required": True} for name in quality_gate_names
        ],
        "images": [{"name": "backend"}, {"name": "frontend"}],
        "evidence": [{"kind": "ci_run"}],
    }
