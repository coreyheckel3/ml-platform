from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from scripts.ops.build_release_manifest import (
    ReleaseArtifactDefinition,
    ReleaseImageTarget,
    ReleaseManifestError,
    build_release_manifest,
    parse_image_digest_args,
    serialize_release_manifest,
)


def test_release_manifest_records_artifact_and_image_provenance(tmp_path: Path) -> None:
    contract_path = tmp_path / "contracts/api/openapi.json"
    dockerfile_path = tmp_path / "infra/docker/backend.Dockerfile"
    pyproject_path = tmp_path / "pyproject.toml"
    contract_path.parent.mkdir(parents=True)
    dockerfile_path.parent.mkdir(parents=True)
    contract_path.write_text('{"openapi":"3.1.0"}\n', encoding="utf-8")
    dockerfile_path.write_text("FROM python:3.12-slim\n", encoding="utf-8")
    pyproject_path.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    manifest = build_release_manifest(
        repo_root=tmp_path,
        git_sha="a" * 40,
        git_branch="main",
        dirty=False,
        created_at="2026-08-05T00:00:00Z",
        ci_run_url="https://github.com/coreyheckel3/ml-platform/actions/runs/1",
        artifact_definitions=(
            ReleaseArtifactDefinition(
                name="openapi",
                kind="api_contract",
                path="contracts/api/openapi.json",
                required=True,
            ),
        ),
        image_targets=(
            ReleaseImageTarget(
                name="backend",
                dockerfile="infra/docker/backend.Dockerfile",
                context=".",
                required=True,
            ),
        ),
        image_digests={"backend": "sha256:" + "b" * 64},
    )

    artifact = manifest["artifacts"][0]
    image = manifest["images"][0]

    assert manifest["schema_version"] == "forgeml.release_manifest.v1"
    assert manifest["source"] == {"git_sha": "a" * 40, "git_branch": "main", "dirty": False}
    assert artifact["sha256"] == _digest(contract_path)
    assert image["digest"] == "sha256:" + "b" * 64
    assert image["dockerfile_sha256"] == _digest(dockerfile_path)


def test_release_manifest_includes_release_smoke_evidence(tmp_path: Path) -> None:
    artifact_path = tmp_path / "contracts/ops/release-smoke.v1.json"
    dockerfile_path = tmp_path / "infra/docker/backend.Dockerfile"
    smoke_result_path = tmp_path / "outputs/release-smoke.json"
    pyproject_path = tmp_path / "pyproject.toml"
    artifact_path.parent.mkdir(parents=True)
    dockerfile_path.parent.mkdir(parents=True)
    smoke_result_path.parent.mkdir(parents=True)
    artifact_path.write_text('{"schema_version":"contract"}\n', encoding="utf-8")
    dockerfile_path.write_text("FROM python:3.12-slim\n", encoding="utf-8")
    smoke_result_path.write_text(
        json.dumps(
            {
                "schema_version": "forgeml.release_smoke_result.v1",
                "status": "passed",
            }
        ),
        encoding="utf-8",
    )
    pyproject_path.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    manifest = build_release_manifest(
        repo_root=tmp_path,
        git_sha="a" * 40,
        git_branch="main",
        dirty=False,
        created_at="2026-08-05T00:00:00Z",
        release_smoke_result_path=smoke_result_path,
        artifact_definitions=(
            ReleaseArtifactDefinition(
                name="release_smoke",
                kind="operations_contract",
                path="contracts/ops/release-smoke.v1.json",
                required=True,
            ),
        ),
        image_targets=(
            ReleaseImageTarget(
                name="backend",
                dockerfile="infra/docker/backend.Dockerfile",
                context=".",
                required=True,
            ),
        ),
    )

    evidence = manifest["evidence"][0]

    assert evidence["kind"] == "release_smoke_result"
    assert evidence["status"] == "passed"
    assert evidence["schema_version"] == "forgeml.release_smoke_result.v1"
    assert evidence["sha256"] == _digest(smoke_result_path)


def test_release_manifest_fails_when_required_artifact_is_missing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    with pytest.raises(ReleaseManifestError, match="Required release artifact"):
        build_release_manifest(
            repo_root=tmp_path,
            git_sha="a" * 40,
            git_branch="main",
            dirty=False,
            artifact_definitions=(
                ReleaseArtifactDefinition(
                    name="openapi",
                    kind="api_contract",
                    path="contracts/openapi.json",
                    required=True,
                ),
            ),
            image_targets=(),
        )


def test_image_digest_arguments_require_name_value_pairs() -> None:
    assert parse_image_digest_args(("backend=sha256:abc",)) == {"backend": "sha256:abc"}

    with pytest.raises(ReleaseManifestError, match="name=digest"):
        parse_image_digest_args(("sha256:abc",))


def test_release_manifest_serialization_is_deterministic(tmp_path: Path) -> None:
    artifact_path = tmp_path / "contracts/api/openapi.json"
    pyproject_path = tmp_path / "pyproject.toml"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{}", encoding="utf-8")
    pyproject_path.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    manifest = build_release_manifest(
        repo_root=tmp_path,
        git_sha="a" * 40,
        git_branch="main",
        dirty=False,
        created_at="2026-08-05T00:00:00Z",
        artifact_definitions=(
            ReleaseArtifactDefinition(
                name="openapi",
                kind="api_contract",
                path="contracts/api/openapi.json",
                required=True,
            ),
        ),
        image_targets=(),
    )

    assert serialize_release_manifest(manifest) == serialize_release_manifest(manifest)


def _digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
