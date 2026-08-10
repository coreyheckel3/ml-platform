from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RELEASE_MANIFEST_SCHEMA_VERSION = "forgeml.release_manifest.v1"
RELEASE_MANIFEST_CONTRACT_VERSION = "forgeml.release_manifest_contract.v1"


@dataclass(frozen=True)
class ReleaseArtifactDefinition:
    name: str
    kind: str
    path: str
    required: bool


@dataclass(frozen=True)
class ReleaseImageTarget:
    name: str
    dockerfile: str
    context: str
    required: bool


@dataclass(frozen=True)
class GitMetadata:
    sha: str
    branch: str
    dirty: bool


class ReleaseManifestError(RuntimeError):
    pass


REQUIRED_RELEASE_ARTIFACTS: tuple[ReleaseArtifactDefinition, ...] = (
    ReleaseArtifactDefinition(
        name="openapi_contract",
        kind="api_contract",
        path="contracts/openapi/forgeml.v1.openapi.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="problem_details_contract",
        kind="api_contract",
        path="contracts/api/problem-details.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="api_authorization_contract",
        kind="security_contract",
        path="contracts/security/api-authorization.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="permission_catalog",
        kind="security_contract",
        path="contracts/security/permission-catalog.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="runtime_config_policy",
        kind="security_contract",
        path="contracts/security/runtime-config-policy.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="request_log_event_contract",
        kind="observability_contract",
        path="contracts/observability/request-log-event.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="alembic_migration_contract",
        kind="database_contract",
        path="contracts/database/alembic-migrations.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="sqlalchemy_schema_contract",
        kind="database_contract",
        path="contracts/database/sqlalchemy-schema.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="artifact_manifest_contract",
        kind="artifact_contract",
        path="contracts/artifacts/artifact-manifest.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="mlflow_tracking_contract",
        kind="integration_contract",
        path="contracts/mlflow/mlflow-tracking.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="release_smoke_contract",
        kind="operations_contract",
        path="contracts/ops/release-smoke.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="release_manifest_contract",
        kind="operations_contract",
        path="contracts/ops/release-manifest.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="release_evidence_workflow_contract",
        kind="operations_contract",
        path="contracts/ops/release-evidence-workflow.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="release_manifest_verification_contract",
        kind="operations_contract",
        path="contracts/ops/release-manifest-verification.v1.json",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="production_readiness_runbook",
        kind="runbook",
        path="docs/runbooks/production-readiness.md",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="github_actions_ci",
        kind="ci_workflow",
        path=".github/workflows/ci.yml",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="docker_compose",
        kind="deployment_config",
        path="infra/compose/docker-compose.yml",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="staging_terraform_main",
        kind="infrastructure_plan",
        path="infra/terraform/environments/staging/main.tf",
        required=True,
    ),
    ReleaseArtifactDefinition(
        name="staging_terraform_variables",
        kind="infrastructure_plan",
        path="infra/terraform/environments/staging/variables.tf",
        required=True,
    ),
)

RELEASE_IMAGE_TARGETS: tuple[ReleaseImageTarget, ...] = (
    ReleaseImageTarget(
        name="backend",
        dockerfile="infra/docker/backend.Dockerfile",
        context=".",
        required=True,
    ),
    ReleaseImageTarget(
        name="frontend",
        dockerfile="infra/docker/frontend.Dockerfile",
        context=".",
        required=True,
    ),
    ReleaseImageTarget(
        name="training",
        dockerfile="infra/docker/training.Dockerfile",
        context=".",
        required=True,
    ),
    ReleaseImageTarget(
        name="inference",
        dockerfile="infra/docker/inference.Dockerfile",
        context=".",
        required=True,
    ),
    ReleaseImageTarget(
        name="airflow",
        dockerfile="infra/docker/airflow.Dockerfile",
        context=".",
        required=True,
    ),
)

REQUIRED_QUALITY_GATES: tuple[str, ...] = (
    "backend_lint",
    "backend_tests",
    "example_training_smoke",
    "artifact_manifest_contract",
    "mlflow_tracking_contract",
    "frontend_lint",
    "frontend_tests",
    "frontend_e2e",
    "frontend_bundle_budget",
    "docker_build",
    "production_readiness",
    "release_smoke_contract",
    "release_manifest_contract",
    "release_evidence_workflow_contract",
    "release_manifest_verifier_contract",
)

RELEASE_EVIDENCE_TYPES: tuple[str, ...] = (
    "ci_run",
    "production_readiness_result",
    "release_smoke_result",
    "terraform_plan",
    "docker_image_digest",
)


def build_release_manifest(
    *,
    repo_root: Path,
    release_version: str | None = None,
    git_sha: str | None = None,
    git_branch: str | None = None,
    dirty: bool | None = None,
    created_at: str | None = None,
    ci_run_url: str | None = None,
    release_smoke_result_path: Path | None = None,
    image_digests: Mapping[str, str] | None = None,
    artifact_definitions: Sequence[ReleaseArtifactDefinition] = REQUIRED_RELEASE_ARTIFACTS,
    image_targets: Sequence[ReleaseImageTarget] = RELEASE_IMAGE_TARGETS,
) -> dict[str, Any]:
    root = repo_root.resolve()
    git_metadata = resolve_git_metadata(
        root,
        git_sha=git_sha,
        git_branch=git_branch,
        dirty=dirty,
    )
    resolved_ci_run_url = ci_run_url or _ci_run_url_from_environment()
    return {
        "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "release": {
            "version": release_version or read_project_version(root),
            "created_at": created_at or _utc_timestamp(),
            "ci_run_url": resolved_ci_run_url,
        },
        "source": {
            "git_sha": git_metadata.sha,
            "git_branch": git_metadata.branch,
            "dirty": git_metadata.dirty,
        },
        "artifacts": [
            _artifact_record(root, definition)
            for definition in sorted(artifact_definitions, key=lambda item: item.name)
        ],
        "images": [
            _image_record(root, target, image_digests or {})
            for target in sorted(image_targets, key=lambda item: item.name)
        ],
        "evidence": _evidence_records(
            root,
            ci_run_url=resolved_ci_run_url,
            release_smoke_result_path=release_smoke_result_path,
        ),
        "quality_gates": [
            {"name": gate, "required": True} for gate in sorted(REQUIRED_QUALITY_GATES)
        ],
    }


def build_release_manifest_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_MANIFEST_CONTRACT_VERSION,
        "manifest_schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "generated_from": ["scripts.ops.build_release_manifest"],
        "operator_command": (
            "PYTHONPATH=. python scripts/ops/build_release_manifest.py "
            "--output /tmp/forgeml-release-manifest.json "
            "--image-digest backend=sha256:BACKEND_IMAGE_DIGEST"
        ),
        "summary": {
            "required_artifact_count": len(REQUIRED_RELEASE_ARTIFACTS),
            "image_target_count": len(RELEASE_IMAGE_TARGETS),
            "quality_gate_count": len(REQUIRED_QUALITY_GATES),
            "evidence_type_count": len(RELEASE_EVIDENCE_TYPES),
        },
        "required_top_level_fields": [
            "schema_version",
            "release",
            "source",
            "artifacts",
            "images",
            "evidence",
            "quality_gates",
        ],
        "required_release_fields": ["version", "created_at", "ci_run_url"],
        "required_source_fields": ["git_sha", "git_branch", "dirty"],
        "artifact_definitions": [asdict(item) for item in REQUIRED_RELEASE_ARTIFACTS],
        "image_targets": [asdict(item) for item in RELEASE_IMAGE_TARGETS],
        "quality_gates": list(REQUIRED_QUALITY_GATES),
        "evidence_types": list(RELEASE_EVIDENCE_TYPES),
    }


def serialize_release_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def serialize_release_manifest_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_release_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_release_manifest(manifest), encoding="utf-8")


def resolve_git_metadata(
    repo_root: Path,
    *,
    git_sha: str | None = None,
    git_branch: str | None = None,
    dirty: bool | None = None,
) -> GitMetadata:
    return GitMetadata(
        sha=git_sha or os.environ.get("GITHUB_SHA") or _git_value(repo_root, "rev-parse", "HEAD"),
        branch=(
            git_branch
            or os.environ.get("GITHUB_REF_NAME")
            or _git_value(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
        ),
        dirty=_is_dirty(repo_root) if dirty is None else dirty,
    )


def read_project_version(repo_root: Path) -> str:
    project_data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    version = project_data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ReleaseManifestError("pyproject.toml does not define a project version.")
    return version


def parse_image_digest_args(values: Sequence[str]) -> dict[str, str]:
    image_digests: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ReleaseManifestError(
                f"Image digest must use name=digest format, received: {value}"
            )
        name, digest = value.split("=", 1)
        if not name or not digest:
            raise ReleaseManifestError(
                f"Image digest must include both name and digest, received: {value}"
            )
        image_digests[name] = digest
    return image_digests


def _artifact_record(repo_root: Path, definition: ReleaseArtifactDefinition) -> dict[str, Any]:
    artifact_path = repo_root / definition.path
    if not artifact_path.is_file():
        if definition.required:
            raise ReleaseManifestError(f"Required release artifact is missing: {definition.path}")
        return {
            **asdict(definition),
            "sha256": None,
            "size_bytes": None,
        }
    return {
        **asdict(definition),
        "sha256": _sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
    }


def _image_record(
    repo_root: Path,
    target: ReleaseImageTarget,
    image_digests: Mapping[str, str],
) -> dict[str, Any]:
    dockerfile_path = repo_root / target.dockerfile
    if not dockerfile_path.is_file():
        if target.required:
            raise ReleaseManifestError(f"Required Dockerfile is missing: {target.dockerfile}")
        return {
            **asdict(target),
            "digest": image_digests.get(target.name),
            "dockerfile_sha256": None,
            "dockerfile_size_bytes": None,
        }
    return {
        **asdict(target),
        "digest": image_digests.get(target.name),
        "dockerfile_sha256": _sha256_file(dockerfile_path),
        "dockerfile_size_bytes": dockerfile_path.stat().st_size,
    }


def _evidence_records(
    repo_root: Path,
    *,
    ci_run_url: str | None,
    release_smoke_result_path: Path | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if ci_run_url:
        records.append({"kind": "ci_run", "url": ci_run_url, "required": True})
    if release_smoke_result_path:
        smoke_path = release_smoke_result_path.resolve()
        if not smoke_path.is_file():
            raise ReleaseManifestError(
                f"Release smoke result does not exist: {release_smoke_result_path}"
            )
        smoke_payload = json.loads(smoke_path.read_text(encoding="utf-8"))
        records.append(
            {
                "kind": "release_smoke_result",
                "path": _relative_path(repo_root, smoke_path),
                "required": True,
                "schema_version": smoke_payload.get("schema_version"),
                "status": smoke_payload.get("status"),
                "sha256": _sha256_file(smoke_path),
                "size_bytes": smoke_path.stat().st_size,
            }
        )
    return records


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _utc_timestamp() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ci_run_url_from_environment() -> str | None:
    server_url = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server_url and repository and run_id:
        return f"{server_url}/{repository}/actions/runs/{run_id}"
    return None


def _git_value(repo_root: Path, *args: str) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        return "unknown"
    result = subprocess.run(  # noqa: S603
        [git_executable, *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _is_dirty(repo_root: Path) -> bool:
    return bool(_git_value(repo_root, "status", "--short"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a ForgeML release provenance manifest."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--release-version")
    parser.add_argument("--git-sha")
    parser.add_argument("--git-branch")
    parser.add_argument("--created-at")
    parser.add_argument("--ci-run-url")
    parser.add_argument("--release-smoke-result", type=Path)
    parser.add_argument("--image-digest", action="append", default=[])
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = build_release_manifest(
            repo_root=args.repo_root,
            release_version=args.release_version,
            git_sha=args.git_sha,
            git_branch=args.git_branch,
            created_at=args.created_at,
            ci_run_url=args.ci_run_url,
            release_smoke_result_path=args.release_smoke_result,
            image_digests=parse_image_digest_args(args.image_digest),
        )
    except ReleaseManifestError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    if args.require_clean and manifest["source"]["dirty"]:
        print("FAIL Release manifest requires a clean git worktree.", file=sys.stderr)
        return 1

    if args.output:
        write_release_manifest(manifest, args.output)
        print(f"Wrote release manifest: {args.output}")
    else:
        print(serialize_release_manifest(manifest), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
