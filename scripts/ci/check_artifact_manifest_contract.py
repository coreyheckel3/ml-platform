from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend/src"
for import_path in (REPO_ROOT, BACKEND_SRC):
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)

from forgeml.platform.artifacts.manifest import ARTIFACT_MANIFEST_SCHEMA_VERSION  # noqa: E402

ARTIFACT_MANIFEST_CONTRACT_SCHEMA_VERSION = "forgeml.artifact_manifest_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/artifacts/artifact-manifest.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")


def build_artifact_manifest_contract() -> dict[str, Any]:
    return {
        "schema_version": ARTIFACT_MANIFEST_CONTRACT_SCHEMA_VERSION,
        "manifest_schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.artifacts.manifest",
            "forgeml.platform.artifacts.storage",
            "forgeml.modules.datasets.application.services",
            "forgeml.modules.model_registry.application.services",
        ],
        "storage_contract": {
            "gateway_protocol": "ArtifactStorageGateway",
            "required_methods": ["put_bytes", "get_bytes", "exists"],
            "writer_protocol": "ArtifactManifestWriter",
            "manifest_writer": "ArtifactManifestStore.put_manifest",
            "local_backend": "LocalArtifactStorageGateway",
            "test_backend": "InMemoryArtifactStorageGateway",
            "uri_scheme": "s3",
        },
        "required_manifest_fields": [
            "schema_version",
            "artifact_set_type",
            "artifact_set_id",
            "artifact_root_uri",
            "producer",
            "created_at",
            "artifacts",
            "lineage",
            "metadata",
        ],
        "required_artifact_fields": [
            "name",
            "artifact_type",
            "uri",
            "media_type",
            "size_bytes",
            "checksum_sha256",
            "metadata",
        ],
        "required_lineage_fields": ["source_type", "source_id", "relation"],
        "checksum_policy": {
            "algorithm": "sha256",
            "serialized_format": "sha256:<hex-digest>",
            "validation_functions": [
                "validate_artifact_manifest",
                "validate_payload_checksum",
            ],
        },
        "producers": [
            {
                "module": "datasets",
                "artifact_set_type": "dataset_version",
                "manifest_uri_column": "dataset_versions.artifact_manifest_uri",
                "manifest_hash_column": "dataset_versions.artifact_manifest_hash",
            },
            {
                "module": "model_registry",
                "artifact_set_type": "model_version",
                "manifest_uri_column": "model_versions.artifact_manifest_uri",
                "manifest_hash_column": "model_versions.artifact_manifest_hash",
            },
        ],
        "quality_gates": [
            "python scripts/ci/check_artifact_manifest_contract.py",
            "backend/tests/unit/platform/test_artifact_manifest.py",
            "backend/tests/unit/ops/test_artifact_manifest_contract.py",
        ],
    }


def serialize_artifact_manifest_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_artifact_manifest_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_artifact_manifest_contract(build_artifact_manifest_contract()),
        encoding="utf-8",
    )


def check_artifact_manifest_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_artifact_manifest_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Artifact manifest contract does not exist: {output_path}")
    else:
        expected = serialize_artifact_manifest_contract(build_artifact_manifest_contract())
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Artifact manifest contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_artifact_manifest_contract.py" not in ci_source:
            findings.append("Artifact manifest contract checker is not wired into CI.")

    if findings:
        return False, "Artifact manifest contract violations: " + "; ".join(findings)
    return True, f"Artifact manifest contract is current: {output_path}"


def validate_artifact_manifest_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/platform/artifacts/manifest.py",
        "backend/src/forgeml/platform/artifacts/storage.py",
        "backend/src/forgeml/modules/datasets/application/services.py",
        "backend/src/forgeml/modules/model_registry/application/services.py",
        "backend/src/forgeml/modules/training/infrastructure/execution.py",
        "backend/src/forgeml/modules/datasets/infrastructure/sqlalchemy_models.py",
        "backend/src/forgeml/modules/model_registry/infrastructure/sqlalchemy_models.py",
    ]
    findings = [
        f"Missing artifact manifest source file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    required_fragments = {
        "forgeml.artifact_manifest.v1": sources[
            "backend/src/forgeml/platform/artifacts/manifest.py"
        ],
        "build_dataset_artifact_manifest": sources[
            "backend/src/forgeml/platform/artifacts/manifest.py"
        ],
        "build_model_artifact_manifest": sources[
            "backend/src/forgeml/platform/artifacts/manifest.py"
        ],
        "validate_payload_checksum": sources[
            "backend/src/forgeml/platform/artifacts/manifest.py"
        ],
        "ArtifactStorageGateway": sources[
            "backend/src/forgeml/platform/artifacts/storage.py"
        ],
        "LocalArtifactStorageGateway": sources[
            "backend/src/forgeml/platform/artifacts/storage.py"
        ],
        "InMemoryArtifactStorageGateway": sources[
            "backend/src/forgeml/platform/artifacts/storage.py"
        ],
        "ArtifactManifestStore": sources[
            "backend/src/forgeml/platform/artifacts/storage.py"
        ],
        "ArtifactManifestWriter": sources[
            "backend/src/forgeml/platform/artifacts/storage.py"
        ],
        "dataset_artifact_manifest_key": sources[
            "backend/src/forgeml/modules/datasets/application/services.py"
        ],
        "model_artifact_manifest_key": sources[
            "backend/src/forgeml/modules/model_registry/application/services.py"
        ],
        "artifact_manifest_uri": sources[
            "backend/src/forgeml/modules/datasets/infrastructure/sqlalchemy_models.py"
        ],
        "artifact_manifest_hash": sources[
            "backend/src/forgeml/modules/model_registry/infrastructure/sqlalchemy_models.py"
        ],
        "sha256_uri": sources[
            "backend/src/forgeml/modules/training/infrastructure/execution.py"
        ],
    }
    missing_fragments = sorted(
        fragment
        for fragment, source in required_fragments.items()
        if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing artifact manifest fragments: {missing_fragments}")

    contract = build_artifact_manifest_contract()
    if contract["manifest_schema_version"] != ARTIFACT_MANIFEST_SCHEMA_VERSION:
        findings.append("Artifact manifest schema version is inconsistent.")
    if len(contract["producers"]) < 2:
        findings.append("Artifact manifest contract must include dataset and model producers.")
    if "checksum_sha256" not in contract["required_artifact_fields"]:
        findings.append("Artifact manifest contract must require artifact checksums.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML artifact manifest storage contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in artifact manifest contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in artifact manifest contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_artifact_manifest_contract(args.output)
        print(f"Wrote artifact manifest contract: {args.output}")
        return 0

    passed, detail = check_artifact_manifest_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
