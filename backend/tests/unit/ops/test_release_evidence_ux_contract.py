import json
from pathlib import Path

from scripts.ci.check_release_evidence_ux_contract import (
    build_release_evidence_ux_contract,
    check_release_evidence_ux_contract,
    serialize_release_evidence_ux_contract,
    validate_release_evidence_ux_definition,
    write_release_evidence_ux_contract,
)


def test_release_evidence_ux_definition_validates_required_assets() -> None:
    assert validate_release_evidence_ux_definition(Path(".")) == ()


def test_release_evidence_ux_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-evidence-ux.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_ux_contract.py",
        encoding="utf-8",
    )

    write_release_evidence_ux_contract(contract_path)

    passed, detail = check_release_evidence_ux_contract(contract_path, ci_path=ci_path)
    assert passed
    assert str(contract_path) in detail


def test_release_evidence_ux_contract_detects_stale_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-evidence-ux.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_ux_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_ux_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "stale" in detail


def test_release_evidence_ux_contract_requires_ci_wiring(tmp_path: Path) -> None:
    contract_path = tmp_path / "release-evidence-ux.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_ux_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_release_evidence_ux_contract(contract_path, ci_path=ci_path)

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_evidence_ux_contract_matches_source() -> None:
    passed, detail = check_release_evidence_ux_contract(
        Path("contracts/ops/release-evidence-ux.v1.json")
    )

    assert passed, detail


def test_release_evidence_ux_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_evidence_ux_contract(build_release_evidence_ux_contract())
    )

    assert parsed["schema_version"] == "forgeml.release_evidence_ux_contract.v1"
    assert parsed["route"]["path"] == "/release-evidence"
    assert parsed["route"]["label"] == "Release Evidence"
    assert "frontend/src/modules/release_evidence/pages/ReleaseEvidencePage.tsx" in parsed[
        "required_source_assets"
    ]
    assert "Release Manifest" in parsed["required_ui_sections"]
    assert "Live Evidence Retrieval" in parsed["required_ui_sections"]
    assert "09-release-evidence.png" in parsed["required_release_signals"]
    assert "release_evidence_retrieval_contract" in parsed["required_release_signals"]
    assert "GitHubActionsReleaseEvidenceGateway" in parsed["required_release_signals"]
    assert "python scripts/ci/check_release_evidence_ux_contract.py" in parsed[
        "quality_gates"
    ]
