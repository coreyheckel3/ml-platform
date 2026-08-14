import json
from pathlib import Path

from scripts.ci.check_release_evidence_retrieval_contract import (
    build_release_evidence_retrieval_contract,
    check_release_evidence_retrieval_contract,
    serialize_release_evidence_retrieval_contract,
    validate_release_evidence_retrieval_definition,
    write_release_evidence_retrieval_contract,
)


def test_release_evidence_retrieval_definition_validates_required_assets() -> None:
    assert validate_release_evidence_retrieval_definition(Path(".")) == ()


def test_release_evidence_retrieval_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-retrieval.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_retrieval_contract.py",
        encoding="utf-8",
    )

    write_release_evidence_retrieval_contract(contract_path)

    passed, detail = check_release_evidence_retrieval_contract(
        contract_path,
        ci_path=ci_path,
    )
    assert passed
    assert str(contract_path) in detail


def test_release_evidence_retrieval_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-retrieval.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text("{}", encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_retrieval_contract.py",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_retrieval_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_release_evidence_retrieval_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-retrieval.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_retrieval_contract(contract_path)
    ci_path.write_text("pytest backend/tests", encoding="utf-8")

    passed, detail = check_release_evidence_retrieval_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_evidence_retrieval_contract_matches_source() -> None:
    passed, detail = check_release_evidence_retrieval_contract(
        Path("contracts/ops/release-evidence-retrieval.v1.json")
    )

    assert passed, detail


def test_release_evidence_retrieval_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_evidence_retrieval_contract(
            build_release_evidence_retrieval_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.release_evidence_retrieval_contract.v1"
    assert parsed["retrieval_schema_version"] == "forgeml.release_evidence_retrieval.v1"
    assert parsed["retrieval_boundary"]["gateway_protocol"] == "ReleaseEvidenceGateway"
    assert parsed["retrieval_boundary"]["github_gateway"] == (
        "GitHubActionsReleaseEvidenceGateway"
    )
    assert parsed["retrieval_boundary"]["artifact_name"] == "forgeml-release-manifest"
    assert "manifest_schema_version" in parsed["required_comparison_checks"]
    assert "main_branch_source" in parsed["required_comparison_checks"]
    assert "scripts/ops/retrieve_release_evidence.py --repo" in parsed[
        "required_release_signals"
    ]
    assert "python scripts/ci/check_release_evidence_retrieval_contract.py" in parsed[
        "quality_gates"
    ]
