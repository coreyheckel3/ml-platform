import json
from pathlib import Path

from scripts.ci.check_release_manifest_contract import (
    build_release_manifest_contract,
    check_release_manifest_contract,
    serialize_release_manifest_contract,
    validate_release_manifest_definition,
    write_release_manifest_contract,
)


def test_release_manifest_definition_validates_required_artifacts() -> None:
    assert validate_release_manifest_definition(Path(".")) == ()


def test_release_manifest_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("python scripts/ci/check_release_manifest_contract.py", encoding="utf-8")

    write_release_manifest_contract(contract_path)

    passed, detail = check_release_manifest_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_release_manifest_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text("python scripts/ci/check_release_manifest_contract.py", encoding="utf-8")

    passed, detail = check_release_manifest_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_release_manifest_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-manifest.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_manifest_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_release_manifest_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_manifest_contract_matches_source() -> None:
    passed, detail = check_release_manifest_contract(
        Path("contracts/ops/release-manifest.v1.json")
    )

    assert passed, detail


def test_release_manifest_contract_shape() -> None:
    parsed = json.loads(serialize_release_manifest_contract(build_release_manifest_contract()))
    artifact_paths = {artifact["path"] for artifact in parsed["artifact_definitions"]}
    image_names = {image["name"] for image in parsed["image_targets"]}

    assert parsed["schema_version"] == "forgeml.release_manifest_contract.v1"
    assert parsed["manifest_schema_version"] == "forgeml.release_manifest.v1"
    assert "sha256" in parsed["operator_command"]
    assert "contracts/openapi/forgeml.v1.openapi.json" in artifact_paths
    assert "contracts/artifacts/artifact-manifest.v1.json" in artifact_paths
    assert "contracts/ops/release-smoke.v1.json" in artifact_paths
    assert "contracts/ops/release-evidence-workflow.v1.json" in artifact_paths
    assert "contracts/ops/release-manifest-verification.v1.json" in artifact_paths
    assert {"backend", "frontend", "training", "inference", "airflow"}.issubset(image_names)
    assert "release_evidence_workflow_contract" in parsed["quality_gates"]
    assert "release_manifest_verifier_contract" in parsed["quality_gates"]
    assert "artifact_manifest_contract" in parsed["quality_gates"]
