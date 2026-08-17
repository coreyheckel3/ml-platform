import json
from pathlib import Path

from scripts.ci.check_release_evidence_drilldown_api_contract import (
    build_release_evidence_drilldown_api_contract,
    check_release_evidence_drilldown_api_contract,
    serialize_release_evidence_drilldown_api_contract,
    validate_release_evidence_drilldown_api_definition,
    write_release_evidence_drilldown_api_contract,
)


def test_release_evidence_drilldown_api_definition_validates_required_assets() -> None:
    assert validate_release_evidence_drilldown_api_definition(Path(".")) == ()


def test_release_evidence_drilldown_api_contract_write_and_check_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-drilldown-api.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_drilldown_api_contract.py\n",
        encoding="utf-8",
    )

    write_release_evidence_drilldown_api_contract(contract_path)

    passed, detail = check_release_evidence_drilldown_api_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert passed, detail


def test_release_evidence_drilldown_api_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-drilldown-api.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text(
        json.dumps({"schema_version": "stale"}) + "\n",
        encoding="utf-8",
    )
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_drilldown_api_contract.py\n",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_drilldown_api_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_release_evidence_drilldown_api_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-drilldown-api.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_drilldown_api_contract(contract_path)
    ci_path.write_text("python scripts/ci/check_release_evidence_ux_contract.py\n")

    passed, detail = check_release_evidence_drilldown_api_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_evidence_drilldown_api_contract_matches_source() -> None:
    passed, detail = check_release_evidence_drilldown_api_contract(
        Path("contracts/ops/release-evidence-drilldown-api.v1.json")
    )

    assert passed, detail


def test_release_evidence_drilldown_api_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_evidence_drilldown_api_contract(
            build_release_evidence_drilldown_api_contract()
        )
    )

    assert (
        parsed["schema_version"]
        == "forgeml.release_evidence_drilldown_api_contract.v1"
    )
    assert {
        (endpoint["method"], endpoint["path"])
        for endpoint in parsed["api"]["endpoints"]
    } == {
        ("GET", "/api/v1/admin/release-evidence/reports"),
        ("GET", "/api/v1/admin/release-evidence/reports/{report_id}"),
        ("POST", "/api/v1/admin/release-evidence/reports/retrieve"),
    }
    assert parsed["persistence"]["table"] == "release_evidence_reports"
    assert "admin:release_evidence:read" in parsed["rbac"]["permissions"]
    assert "admin:release_evidence:retrieve" in parsed["rbac"]["permissions"]
