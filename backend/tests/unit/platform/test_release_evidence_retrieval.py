from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from forgeml.platform.release_evidence import (
    GitHubActionsReleaseEvidenceGateway,
    LocalReleaseEvidenceGateway,
    ReleaseEvidenceRetrievalError,
    compare_release_manifest_to_contract,
    summarize_release_manifest,
)


def test_release_manifest_summary_extracts_governance_fields() -> None:
    manifest = _manifest(
        artifact_names=("release_manifest_contract", "openapi_contract"),
        quality_gates=("backend_tests", "release_manifest_contract"),
    )

    summary = summarize_release_manifest(manifest)

    assert summary.schema_version == "forgeml.release_manifest.v1"
    assert summary.git_sha == "a" * 40
    assert summary.git_branch == "main"
    assert summary.ci_run_url == "https://github.com/coreyheckel3/ml-platform/actions/runs/1"
    assert summary.artifact_names == ("openapi_contract", "release_manifest_contract")
    assert summary.quality_gate_names == ("backend_tests", "release_manifest_contract")
    assert summary.image_target_names == ("backend", "frontend")


def test_release_manifest_comparison_reports_missing_artifacts_and_gates() -> None:
    comparison = compare_release_manifest_to_contract(
        _manifest(
            artifact_names=("openapi_contract",),
            quality_gates=("backend_tests",),
        ),
        required_artifacts=("openapi_contract", "release_manifest_contract"),
        required_quality_gates=("backend_tests", "frontend_e2e"),
    )

    assert not comparison.passed
    assert comparison.schema_version_matches
    assert comparison.branch_matches
    assert comparison.missing_artifacts == ("release_manifest_contract",)
    assert comparison.missing_quality_gates == ("frontend_e2e",)


def test_release_manifest_comparison_passes_when_required_evidence_matches() -> None:
    comparison = compare_release_manifest_to_contract(
        _manifest(
            artifact_names=("openapi_contract", "release_manifest_contract"),
            quality_gates=("backend_tests", "frontend_e2e"),
        ),
        required_artifacts=("openapi_contract", "release_manifest_contract"),
        required_quality_gates=("backend_tests", "frontend_e2e"),
    )

    assert comparison.passed
    assert comparison.as_dict()["passed"] is True


def test_local_release_evidence_gateway_loads_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "forgeml-release-manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    gateway = LocalReleaseEvidenceGateway(manifest_path)

    run = gateway.latest_successful_run()
    manifest = gateway.download_release_manifest(run)

    assert run.head_sha == "a" * 40
    assert run.branch == "main"
    assert manifest["schema_version"] == "forgeml.release_manifest.v1"


def test_github_actions_gateway_retrieves_manifest_from_artifact_archive() -> None:
    calls: list[str] = []
    zip_bytes = _manifest_zip(_manifest())

    def json_transport(
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        calls.append(url)
        assert headers["Authorization"] == "Bearer token"
        assert timeout_seconds == 15.0
        if "/actions/workflows/ci.yml/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "id": 123,
                        "head_sha": "a" * 40,
                        "head_branch": "main",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/123",
                    }
                ]
            }
        if "/actions/runs/123/artifacts" in url:
            return {
                "artifacts": [
                    {
                        "id": 456,
                        "name": "forgeml-release-manifest",
                        "size_in_bytes": len(zip_bytes),
                        "archive_download_url": "https://api.github.com/artifacts/456/zip",
                    }
                ]
            }
        raise AssertionError(f"unexpected url: {url}")

    def bytes_transport(
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> bytes:
        calls.append(url)
        assert headers["Authorization"] == "Bearer token"
        assert timeout_seconds == 15.0
        return zip_bytes

    gateway = GitHubActionsReleaseEvidenceGateway(
        repository="coreyheckel3/ml-platform",
        token="token",
        json_transport=json_transport,
        bytes_transport=bytes_transport,
    )

    run, manifest = gateway.retrieve_latest_manifest()

    assert run.id == 123
    assert manifest["schema_version"] == "forgeml.release_manifest.v1"
    assert any("branch=main" in call for call in calls)
    assert calls[-1] == "https://api.github.com/artifacts/456/zip"


def test_github_actions_gateway_requires_release_manifest_artifact() -> None:
    def json_transport(
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        if "/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "id": 123,
                        "head_sha": "a" * 40,
                        "head_branch": "main",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/123",
                    }
                ]
            }
        return {
            "artifacts": [
                {
                    "id": 1,
                    "name": "other",
                    "size_in_bytes": 1,
                    "archive_download_url": "https://example.test",
                }
            ]
        }

    gateway = GitHubActionsReleaseEvidenceGateway(
        repository="coreyheckel3/ml-platform",
        token=None,
        json_transport=json_transport,
        bytes_transport=lambda _url, _headers, _timeout: b"",
    )

    with pytest.raises(ReleaseEvidenceRetrievalError, match="was not found"):
        gateway.retrieve_latest_manifest()


def test_github_actions_gateway_requires_owner_repo_format() -> None:
    with pytest.raises(ReleaseEvidenceRetrievalError, match="owner/name"):
        GitHubActionsReleaseEvidenceGateway(repository="ml-platform", token=None)


def _manifest(
    *,
    artifact_names: tuple[str, ...] = ("openapi_contract",),
    quality_gates: tuple[str, ...] = ("backend_tests",),
) -> dict[str, Any]:
    return {
        "schema_version": "forgeml.release_manifest.v1",
        "release": {
            "version": "0.1.0",
            "created_at": "2026-08-05T00:00:00Z",
            "ci_run_url": "https://github.com/coreyheckel3/ml-platform/actions/runs/1",
        },
        "source": {"git_sha": "a" * 40, "git_branch": "main", "dirty": False},
        "artifacts": [{"name": name} for name in artifact_names],
        "quality_gates": [{"name": name, "required": True} for name in quality_gates],
        "images": [{"name": "backend"}, {"name": "frontend"}],
        "evidence": [{"kind": "ci_run"}],
    }


def _manifest_zip(manifest: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr("forgeml-release-manifest.json", json.dumps(manifest))
    return buffer.getvalue()
