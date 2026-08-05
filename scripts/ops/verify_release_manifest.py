from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.build_release_manifest import (  # noqa: E402
    RELEASE_EVIDENCE_TYPES,
    RELEASE_IMAGE_TARGETS,
    RELEASE_MANIFEST_SCHEMA_VERSION,
    REQUIRED_QUALITY_GATES,
    REQUIRED_RELEASE_ARTIFACTS,
)

RELEASE_MANIFEST_VERIFICATION_SCHEMA_VERSION = "forgeml.release_manifest_verification.v1"
RELEASE_MANIFEST_VERIFICATION_CONTRACT_VERSION = (
    "forgeml.release_manifest_verification_contract.v1"
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "release",
    "source",
    "artifacts",
    "images",
    "evidence",
    "quality_gates",
)
REQUIRED_RELEASE_FIELDS = ("version", "created_at", "ci_run_url")
REQUIRED_SOURCE_FIELDS = ("git_sha", "git_branch", "dirty")
REQUIRED_VERIFICATION_CHECKS = (
    "manifest_schema_version",
    "release_metadata_shape",
    "source_revision_shape",
    "artifact_hash_integrity",
    "dockerfile_hash_integrity",
    "image_digest_shape",
    "quality_gate_coverage",
    "ci_evidence_linkage",
    "release_smoke_evidence_integrity",
)


def build_release_manifest_verification_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_MANIFEST_VERIFICATION_CONTRACT_VERSION,
        "verification_schema_version": RELEASE_MANIFEST_VERIFICATION_SCHEMA_VERSION,
        "generated_from": [
            "scripts.ops.verify_release_manifest",
            "scripts.ops.build_release_manifest",
        ],
        "operator_command": (
            "PYTHONPATH=. python scripts/ops/verify_release_manifest.py "
            "--manifest /tmp/forgeml-release-manifest.json --require-ci-evidence"
        ),
        "required_cli_flags": [
            "--manifest",
            "--require-ci-evidence",
            "--require-image-digests",
        ],
        "required_checks": list(REQUIRED_VERIFICATION_CHECKS),
        "summary": {
            "required_check_count": len(REQUIRED_VERIFICATION_CHECKS),
            "required_artifact_count": len(REQUIRED_RELEASE_ARTIFACTS),
            "image_target_count": len(RELEASE_IMAGE_TARGETS),
            "quality_gate_count": len(REQUIRED_QUALITY_GATES),
        },
    }


def serialize_release_manifest_verification_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def serialize_release_manifest_verification_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def verify_release_manifest(
    *,
    repo_root: Path,
    manifest_path: Path,
    require_ci_evidence: bool = False,
    require_image_digests: bool = False,
) -> dict[str, Any]:
    root = repo_root.resolve()
    resolved_manifest_path = manifest_path.resolve()
    findings: list[dict[str, str]] = []
    manifest = _read_manifest(resolved_manifest_path, findings)

    if manifest is not None:
        _validate_top_level_shape(manifest, findings)
        release = _validate_release_metadata(manifest, findings, require_ci_evidence)
        _validate_source_metadata(manifest, findings)
        _validate_artifacts(manifest, root, findings)
        _validate_images(manifest, root, findings, require_image_digests)
        _validate_quality_gates(manifest, findings)
        _validate_evidence(manifest, root, findings, release, require_ci_evidence)

    return {
        "schema_version": RELEASE_MANIFEST_VERIFICATION_SCHEMA_VERSION,
        "manifest_path": _relative_path(root, resolved_manifest_path),
        "status": "passed" if not findings else "failed",
        "summary": {
            "artifact_count": _count_mapping_list(manifest, "artifacts"),
            "image_count": _count_mapping_list(manifest, "images"),
            "quality_gate_count": _count_mapping_list(manifest, "quality_gates"),
            "evidence_count": _count_mapping_list(manifest, "evidence"),
            "require_ci_evidence": require_ci_evidence,
            "require_image_digests": require_image_digests,
            "finding_count": len(findings),
        },
        "findings": findings,
    }


def verification_passed(report: Mapping[str, Any]) -> bool:
    return report.get("status") == "passed"


def _read_manifest(path: Path, findings: list[dict[str, str]]) -> dict[str, Any] | None:
    if not path.is_file():
        findings.append(_finding("manifest_missing", f"Release manifest does not exist: {path}"))
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(_finding("manifest_invalid_json", f"Manifest JSON is invalid: {exc}"))
        return None
    if not isinstance(payload, dict):
        findings.append(_finding("manifest_invalid_shape", "Manifest root must be an object."))
        return None
    return payload


def _validate_top_level_shape(
    manifest: Mapping[str, Any],
    findings: list[dict[str, str]],
) -> None:
    missing_fields = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in manifest]
    if missing_fields:
        findings.append(
            _finding(
                "manifest_missing_top_level_fields",
                f"Manifest is missing top-level fields: {missing_fields}",
            )
        )
    if manifest.get("schema_version") != RELEASE_MANIFEST_SCHEMA_VERSION:
        findings.append(
            _finding(
                "manifest_schema_mismatch",
                "Manifest schema_version must be "
                f"{RELEASE_MANIFEST_SCHEMA_VERSION}.",
            )
        )


def _validate_release_metadata(
    manifest: Mapping[str, Any],
    findings: list[dict[str, str]],
    require_ci_evidence: bool,
) -> Mapping[str, Any] | None:
    release = _as_mapping(manifest.get("release"), "release", findings)
    if release is None:
        return None

    missing_fields = [field for field in REQUIRED_RELEASE_FIELDS if field not in release]
    if missing_fields:
        findings.append(
            _finding(
                "release_missing_fields",
                f"Release metadata is missing fields: {missing_fields}",
            )
        )
    if not _non_empty_string(release.get("version")):
        findings.append(_finding("release_version_invalid", "Release version must be set."))
    created_at = release.get("created_at")
    if not _non_empty_string(created_at) or not _is_iso_timestamp(created_at):
        findings.append(
            _finding("release_created_at_invalid", "Release created_at must be ISO-8601.")
        )
    ci_run_url = release.get("ci_run_url")
    if require_ci_evidence and not _non_empty_string(ci_run_url):
        findings.append(
            _finding("release_ci_url_missing", "CI evidence requires release.ci_run_url.")
        )
    return release


def _validate_source_metadata(
    manifest: Mapping[str, Any],
    findings: list[dict[str, str]],
) -> None:
    source = _as_mapping(manifest.get("source"), "source", findings)
    if source is None:
        return

    missing_fields = [field for field in REQUIRED_SOURCE_FIELDS if field not in source]
    if missing_fields:
        findings.append(
            _finding(
                "source_missing_fields",
                f"Source metadata is missing fields: {missing_fields}",
            )
        )
    git_sha = source.get("git_sha")
    if not _non_empty_string(git_sha) or (
        git_sha != "unknown" and not GIT_SHA_PATTERN.match(git_sha)
    ):
        findings.append(
            _finding(
                "source_git_sha_invalid",
                "Source git_sha must be a full SHA-1 hex revision or unknown.",
            )
        )
    if not _non_empty_string(source.get("git_branch")):
        findings.append(_finding("source_git_branch_invalid", "Source git_branch must be set."))
    if not isinstance(source.get("dirty"), bool):
        findings.append(_finding("source_dirty_invalid", "Source dirty must be boolean."))


def _validate_artifacts(
    manifest: Mapping[str, Any],
    repo_root: Path,
    findings: list[dict[str, str]],
) -> None:
    artifact_records = _named_records(manifest.get("artifacts"), "artifacts", findings)
    expected = {artifact.name: artifact for artifact in REQUIRED_RELEASE_ARTIFACTS}
    missing = sorted(set(expected) - set(artifact_records))
    unexpected = sorted(set(artifact_records) - set(expected))
    if missing:
        findings.append(
            _finding("release_artifacts_missing", f"Manifest is missing artifacts: {missing}")
        )
    if unexpected:
        findings.append(
            _finding(
                "release_artifacts_unexpected",
                f"Manifest includes unexpected artifacts: {unexpected}",
            )
        )

    for name, definition in expected.items():
        record = artifact_records.get(name)
        if record is None:
            continue
        _expect_field(record, "kind", definition.kind, f"artifact_{name}_kind", findings)
        _expect_field(record, "path", definition.path, f"artifact_{name}_path", findings)
        _expect_field(
            record,
            "required",
            definition.required,
            f"artifact_{name}_required",
            findings,
        )
        artifact_path = repo_root / definition.path
        if not artifact_path.is_file():
            findings.append(
                _finding(
                    f"artifact_{name}_file_missing",
                    f"Required release artifact is missing: {definition.path}",
                )
            )
            continue
        _expect_field(
            record,
            "sha256",
            _sha256_file(artifact_path),
            f"artifact_{name}_sha256",
            findings,
        )
        _expect_field(
            record,
            "size_bytes",
            artifact_path.stat().st_size,
            f"artifact_{name}_size",
            findings,
        )


def _validate_images(
    manifest: Mapping[str, Any],
    repo_root: Path,
    findings: list[dict[str, str]],
    require_image_digests: bool,
) -> None:
    image_records = _named_records(manifest.get("images"), "images", findings)
    expected = {target.name: target for target in RELEASE_IMAGE_TARGETS}
    missing = sorted(set(expected) - set(image_records))
    unexpected = sorted(set(image_records) - set(expected))
    if missing:
        findings.append(
            _finding("release_images_missing", f"Manifest is missing images: {missing}")
        )
    if unexpected:
        findings.append(
            _finding(
                "release_images_unexpected",
                f"Manifest includes unexpected images: {unexpected}",
            )
        )

    for name, target in expected.items():
        record = image_records.get(name)
        if record is None:
            continue
        _expect_field(record, "dockerfile", target.dockerfile, f"image_{name}_dockerfile", findings)
        _expect_field(record, "context", target.context, f"image_{name}_context", findings)
        _expect_field(record, "required", target.required, f"image_{name}_required", findings)
        digest = record.get("digest")
        if digest is not None and (
            not isinstance(digest, str) or DIGEST_PATTERN.match(digest) is None
        ):
            findings.append(
                _finding(
                    f"image_{name}_digest_invalid",
                    f"Image digest for {name} must use sha256:<64 hex chars>.",
                )
            )
        if require_image_digests and target.required and not _non_empty_string(digest):
            findings.append(
                _finding(
                    f"image_{name}_digest_missing",
                    f"Image digest for required image {name} must be set.",
                )
            )
        dockerfile_path = repo_root / target.dockerfile
        if not dockerfile_path.is_file():
            findings.append(
                _finding(
                    f"image_{name}_dockerfile_missing",
                    f"Required Dockerfile is missing: {target.dockerfile}",
                )
            )
            continue
        _expect_field(
            record,
            "dockerfile_sha256",
            _sha256_file(dockerfile_path),
            f"image_{name}_dockerfile_sha256",
            findings,
        )
        _expect_field(
            record,
            "dockerfile_size_bytes",
            dockerfile_path.stat().st_size,
            f"image_{name}_dockerfile_size",
            findings,
        )


def _validate_quality_gates(
    manifest: Mapping[str, Any],
    findings: list[dict[str, str]],
) -> None:
    quality_gate_records = _named_records(manifest.get("quality_gates"), "quality_gates", findings)
    expected = set(REQUIRED_QUALITY_GATES)
    missing = sorted(expected - set(quality_gate_records))
    unexpected = sorted(set(quality_gate_records) - expected)
    if missing:
        findings.append(
            _finding("quality_gates_missing", f"Manifest is missing quality gates: {missing}")
        )
    if unexpected:
        findings.append(
            _finding(
                "quality_gates_unexpected",
                f"Manifest includes unexpected quality gates: {unexpected}",
            )
        )
    for name in expected:
        record = quality_gate_records.get(name)
        if record is not None and record.get("required") is not True:
            findings.append(
                _finding(
                    f"quality_gate_{name}_not_required",
                    f"Quality gate {name} must be marked required.",
                )
            )


def _validate_evidence(
    manifest: Mapping[str, Any],
    repo_root: Path,
    findings: list[dict[str, str]],
    release: Mapping[str, Any] | None,
    require_ci_evidence: bool,
) -> None:
    evidence_records = _mapping_records(manifest.get("evidence"), "evidence", findings)
    known_types = set(RELEASE_EVIDENCE_TYPES)
    ci_run_url = release.get("ci_run_url") if release is not None else None
    ci_records = []

    for index, record in enumerate(evidence_records):
        kind = record.get("kind")
        if not isinstance(kind, str):
            findings.append(
                _finding(f"evidence_{index}_kind_invalid", "Evidence kind must be set.")
            )
            continue
        if kind not in known_types:
            findings.append(
                _finding(
                    f"evidence_{index}_kind_unknown",
                    f"Evidence kind is not part of the release contract: {kind}",
                )
            )
        if kind == "ci_run":
            ci_records.append(record)
        if kind == "release_smoke_result":
            _validate_release_smoke_evidence(record, repo_root, index, findings)

    if require_ci_evidence:
        if not _non_empty_string(ci_run_url):
            return
        if not any(record.get("url") == ci_run_url for record in ci_records):
            findings.append(
                _finding(
                    "ci_evidence_not_linked",
                    "Manifest evidence must include a ci_run record matching release.ci_run_url.",
                )
            )


def _validate_release_smoke_evidence(
    record: Mapping[str, Any],
    repo_root: Path,
    index: int,
    findings: list[dict[str, str]],
) -> None:
    if record.get("schema_version") != "forgeml.release_smoke_result.v1":
        findings.append(
            _finding(
                f"evidence_{index}_smoke_schema_invalid",
                "Release smoke evidence must use forgeml.release_smoke_result.v1.",
            )
        )
    if record.get("status") != "passed":
        findings.append(
            _finding(
                f"evidence_{index}_smoke_status_invalid",
                "Release smoke evidence status must be passed.",
            )
        )
    path_value = record.get("path")
    if not isinstance(path_value, str) or not path_value:
        findings.append(
            _finding(f"evidence_{index}_smoke_path_invalid", "Release smoke path must be set.")
        )
        return
    evidence_path = Path(path_value)
    if not evidence_path.is_absolute():
        evidence_path = repo_root / evidence_path
    if not evidence_path.is_file():
        if record.get("required") is True:
            findings.append(
                _finding(
                    f"evidence_{index}_smoke_file_missing",
                    f"Release smoke evidence file is missing: {path_value}",
                )
            )
        return
    _expect_field(
        record,
        "sha256",
        _sha256_file(evidence_path),
        f"evidence_{index}_smoke_sha256",
        findings,
    )
    _expect_field(
        record,
        "size_bytes",
        evidence_path.stat().st_size,
        f"evidence_{index}_smoke_size",
        findings,
    )


def _named_records(
    value: Any,
    label: str,
    findings: list[dict[str, str]],
) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(_mapping_records(value, label, findings)):
        name = record.get("name")
        if not isinstance(name, str) or not name:
            findings.append(_finding(f"{label}_{index}_name_invalid", f"{label} name is invalid."))
            continue
        if name in records:
            findings.append(
                _finding(f"{label}_{name}_duplicate", f"Duplicate {label} name: {name}")
            )
            continue
        records[name] = record
    return records


def _mapping_records(
    value: Any,
    label: str,
    findings: list[dict[str, str]],
) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        findings.append(_finding(f"{label}_invalid", f"{label} must be a list."))
        return []
    records: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            findings.append(
                _finding(f"{label}_{index}_invalid", f"{label} entry must be an object.")
            )
            continue
        records.append(item)
    return records


def _as_mapping(
    value: Any,
    label: str,
    findings: list[dict[str, str]],
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        findings.append(_finding(f"{label}_invalid", f"{label} must be an object."))
        return None
    return value


def _expect_field(
    record: Mapping[str, Any],
    field: str,
    expected: object,
    code: str,
    findings: list[dict[str, str]],
) -> None:
    actual = record.get(field)
    if actual != expected:
        findings.append(
            _finding(
                code,
                f"Expected {field}={expected!r}, received {actual!r}.",
            )
        )


def _count_mapping_list(manifest: Mapping[str, Any] | None, field: str) -> int:
    if manifest is None:
        return 0
    value = manifest.get(field)
    return len(value) if isinstance(value, list) else 0


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


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


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "error", "message": message}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a ForgeML release provenance manifest."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-ci-evidence", action="store_true")
    parser.add_argument("--require-image-digests", action="store_true")
    args = parser.parse_args(argv)

    report = verify_release_manifest(
        repo_root=args.repo_root,
        manifest_path=args.manifest,
        require_ci_evidence=args.require_ci_evidence,
        require_image_digests=args.require_image_digests,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            serialize_release_manifest_verification_report(report),
            encoding="utf-8",
        )

    if verification_passed(report):
        print(f"PASS Release manifest verification passed: {args.manifest}")
        if args.output:
            print(f"Wrote release manifest verification report: {args.output}")
        return 0

    print(
        "FAIL Release manifest verification failed: "
        f"{report['summary']['finding_count']} finding(s)",
        file=sys.stderr,
    )
    for finding in report["findings"]:
        print(f"- {finding['code']}: {finding['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
