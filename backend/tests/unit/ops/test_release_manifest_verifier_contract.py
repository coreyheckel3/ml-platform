import json
from pathlib import Path

from scripts.ci.check_release_manifest_verifier_contract import (
    check_release_manifest_verifier_contract,
    serialize_release_manifest_verification_contract,
    validate_release_manifest_verifier_definition,
    write_release_manifest_verification_contract,
)
from scripts.ops.verify_release_manifest import build_release_manifest_verification_contract

VALID_RELEASE_MANIFEST_VERIFIER_CI = """
jobs:
  backend:
    steps:
      - name: Check release manifest verifier contract
        run: python scripts/ci/check_release_manifest_verifier_contract.py
  release-evidence:
    steps:
      - name: Verify release manifest
        run: >
          python scripts/ops/verify_release_manifest.py
          --manifest dist/release/forgeml-release-manifest.json
          --require-ci-evidence
"""


def test_release_manifest_verifier_definition_validates_required_checks() -> None:
    assert validate_release_manifest_verifier_definition(Path(".")) == ()


def test_release_manifest_verifier_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-manifest-verification.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(VALID_RELEASE_MANIFEST_VERIFIER_CI, encoding="utf-8")

    write_release_manifest_verification_contract(contract_path)

    passed, detail = check_release_manifest_verifier_contract(
        contract_path,
        ci_path=ci_path,
    )
    assert passed
    assert str(contract_path) in detail


def test_release_manifest_verifier_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-manifest-verification.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(VALID_RELEASE_MANIFEST_VERIFIER_CI, encoding="utf-8")

    passed, detail = check_release_manifest_verifier_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_release_manifest_verifier_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-manifest-verification.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_manifest_verification_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_release_manifest_verifier_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not fully wired into CI" in detail


def test_checked_in_release_manifest_verifier_contract_matches_source() -> None:
    passed, detail = check_release_manifest_verifier_contract(
        Path("contracts/ops/release-manifest-verification.v1.json")
    )

    assert passed, detail


def test_release_manifest_verifier_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_manifest_verification_contract(
            build_release_manifest_verification_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.release_manifest_verification_contract.v1"
    assert parsed["verification_schema_version"] == "forgeml.release_manifest_verification.v1"
    assert "--require-ci-evidence" in parsed["operator_command"]
    assert "artifact_hash_integrity" in parsed["required_checks"]
    assert "dockerfile_hash_integrity" in parsed["required_checks"]
    assert parsed["summary"]["required_check_count"] >= 8
