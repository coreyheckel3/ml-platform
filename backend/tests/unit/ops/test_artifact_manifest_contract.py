import json
from pathlib import Path

from scripts.ci.check_artifact_manifest_contract import (
    build_artifact_manifest_contract,
    check_artifact_manifest_contract,
    serialize_artifact_manifest_contract,
    validate_artifact_manifest_definition,
    write_artifact_manifest_contract,
)


def test_artifact_manifest_definition_validates_sources() -> None:
    assert validate_artifact_manifest_definition(Path(".")) == ()


def test_artifact_manifest_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "artifact-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("python scripts/ci/check_artifact_manifest_contract.py", encoding="utf-8")

    write_artifact_manifest_contract(contract_path)

    passed, detail = check_artifact_manifest_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_artifact_manifest_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "artifact-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text("python scripts/ci/check_artifact_manifest_contract.py", encoding="utf-8")

    passed, detail = check_artifact_manifest_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_artifact_manifest_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "artifact-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_artifact_manifest_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_artifact_manifest_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_artifact_manifest_contract_matches_source() -> None:
    passed, detail = check_artifact_manifest_contract(
        Path("contracts/artifacts/artifact-manifest.v1.json")
    )

    assert passed, detail


def test_artifact_manifest_contract_shape() -> None:
    parsed = json.loads(serialize_artifact_manifest_contract(build_artifact_manifest_contract()))
    producer_types = {producer["artifact_set_type"] for producer in parsed["producers"]}

    assert parsed["schema_version"] == "forgeml.artifact_manifest_contract.v1"
    assert parsed["manifest_schema_version"] == "forgeml.artifact_manifest.v1"
    assert "checksum_sha256" in parsed["required_artifact_fields"]
    assert "ArtifactStorageGateway" == parsed["storage_contract"]["gateway_protocol"]
    assert "ArtifactManifestWriter" == parsed["storage_contract"]["writer_protocol"]
    assert {"dataset_version", "model_version"}.issubset(producer_types)
