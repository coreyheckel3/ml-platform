from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.ops.build_release_manifest import (
    RELEASE_IMAGE_TARGETS,
    REQUIRED_RELEASE_ARTIFACTS,
    build_release_manifest,
    write_release_manifest,
)
from scripts.ops.verify_release_manifest import (
    serialize_release_manifest_verification_report,
    verification_passed,
    verify_release_manifest,
)


def test_release_manifest_verifier_accepts_valid_manifest(tmp_path: Path) -> None:
    manifest_path = _write_valid_manifest(tmp_path)

    report = verify_release_manifest(
        repo_root=tmp_path,
        manifest_path=manifest_path,
        require_ci_evidence=True,
    )

    assert verification_passed(report)
    assert report["schema_version"] == "forgeml.release_manifest_verification.v1"
    assert report["summary"]["artifact_count"] == len(REQUIRED_RELEASE_ARTIFACTS)
    assert report["summary"]["finding_count"] == 0


def test_release_manifest_verifier_detects_tampered_artifact_hash(tmp_path: Path) -> None:
    manifest_path = _write_valid_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    openapi_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["name"] == "openapi_contract"
    )
    openapi_artifact["sha256"] = "sha256:" + "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = verify_release_manifest(
        repo_root=tmp_path,
        manifest_path=manifest_path,
        require_ci_evidence=True,
    )

    assert not verification_passed(report)
    assert _finding_codes(report) == {"artifact_openapi_contract_sha256"}


def test_release_manifest_verifier_detects_missing_quality_gate(tmp_path: Path) -> None:
    manifest_path = _write_valid_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["quality_gates"] = manifest["quality_gates"][1:]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = verify_release_manifest(repo_root=tmp_path, manifest_path=manifest_path)

    assert not verification_passed(report)
    assert "quality_gates_missing" in _finding_codes(report)


def test_release_manifest_verifier_requires_linked_ci_evidence(tmp_path: Path) -> None:
    manifest_path = _write_valid_manifest(tmp_path, ci_run_url=None)

    report = verify_release_manifest(
        repo_root=tmp_path,
        manifest_path=manifest_path,
        require_ci_evidence=True,
    )

    assert not verification_passed(report)
    assert "release_ci_url_missing" in _finding_codes(report)


def test_release_manifest_verifier_can_require_image_digests(tmp_path: Path) -> None:
    manifest_path = _write_valid_manifest(tmp_path, image_digest=None)

    report = verify_release_manifest(
        repo_root=tmp_path,
        manifest_path=manifest_path,
        require_image_digests=True,
    )

    assert not verification_passed(report)
    assert "image_backend_digest_missing" in _finding_codes(report)


def test_release_manifest_verification_report_serialization_is_deterministic(
    tmp_path: Path,
) -> None:
    manifest_path = _write_valid_manifest(tmp_path)
    report = verify_release_manifest(repo_root=tmp_path, manifest_path=manifest_path)

    assert serialize_release_manifest_verification_report(
        report
    ) == serialize_release_manifest_verification_report(report)


def _write_valid_manifest(
    repo_root: Path,
    *,
    ci_run_url: str | None = "https://github.com/coreyheckel3/ml-platform/actions/runs/1",
    image_digest: str | None = "sha256:" + "b" * 64,
) -> Path:
    pyproject_path = repo_root / "pyproject.toml"
    pyproject_path.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    for artifact in REQUIRED_RELEASE_ARTIFACTS:
        artifact_path = repo_root / artifact.path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(f"{artifact.name}\n", encoding="utf-8")
    for target in RELEASE_IMAGE_TARGETS:
        dockerfile_path = repo_root / target.dockerfile
        dockerfile_path.parent.mkdir(parents=True, exist_ok=True)
        dockerfile_path.write_text(
            f"FROM scratch\nLABEL forgeml.image=\"{target.name}\"\n",
            encoding="utf-8",
        )

    manifest = build_release_manifest(
        repo_root=repo_root,
        git_sha="a" * 40,
        git_branch="main",
        dirty=False,
        created_at="2026-08-05T00:00:00Z",
        ci_run_url=ci_run_url,
        image_digests=(
            {target.name: image_digest for target in RELEASE_IMAGE_TARGETS}
            if image_digest
            else {}
        ),
    )
    manifest_path = repo_root / "release-manifest.json"
    write_release_manifest(manifest, manifest_path)
    return manifest_path


def _finding_codes(report: Mapping[str, Any]) -> set[str]:
    return {finding["code"] for finding in report["findings"]}
