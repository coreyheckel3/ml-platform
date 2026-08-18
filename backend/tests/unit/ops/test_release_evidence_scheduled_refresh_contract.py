import json
from pathlib import Path

from scripts.ci.check_release_evidence_scheduled_refresh_contract import (
    build_release_evidence_scheduled_refresh_contract,
    check_release_evidence_scheduled_refresh_contract,
    serialize_release_evidence_scheduled_refresh_contract,
    validate_release_evidence_scheduled_refresh_definition,
    write_release_evidence_scheduled_refresh_contract,
)


def test_release_evidence_scheduled_refresh_definition_validates_assets() -> None:
    assert validate_release_evidence_scheduled_refresh_definition(Path(".")) == ()


def test_release_evidence_scheduled_refresh_contract_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-scheduled-refresh.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_scheduled_refresh_contract.py\n",
        encoding="utf-8",
    )

    write_release_evidence_scheduled_refresh_contract(contract_path)

    passed, detail = check_release_evidence_scheduled_refresh_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert passed, detail


def test_release_evidence_scheduled_refresh_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-scheduled-refresh.v1.json"
    ci_path = tmp_path / "ci.yml"
    contract_path.write_text(
        json.dumps({"schema_version": "stale"}) + "\n",
        encoding="utf-8",
    )
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_scheduled_refresh_contract.py\n",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_scheduled_refresh_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "stale" in detail


def test_release_evidence_scheduled_refresh_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-scheduled-refresh.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_scheduled_refresh_contract(contract_path)
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_drilldown_api_contract.py\n",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_scheduled_refresh_contract(
        contract_path,
        ci_path=ci_path,
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_evidence_scheduled_refresh_contract_matches_source() -> None:
    passed, detail = check_release_evidence_scheduled_refresh_contract(
        Path("contracts/ops/release-evidence-scheduled-refresh.v1.json")
    )

    assert passed, detail


def test_release_evidence_scheduled_refresh_contract_shape() -> None:
    parsed = json.loads(
        serialize_release_evidence_scheduled_refresh_contract(
            build_release_evidence_scheduled_refresh_contract()
        )
    )

    assert (
        parsed["schema_version"]
        == "forgeml.release_evidence_scheduled_refresh_contract.v1"
    )
    assert parsed["api"]["endpoints"] == [
        {
            "method": "GET",
            "path": "/api/v1/admin/release-evidence/refresh/status",
        }
    ]
    assert parsed["automation"]["script"] == "scripts/ops/refresh_release_evidence.py"
    assert "latest_report_failed" in parsed["stale_semantics"]["reasons"]
    assert (
        parsed["release_manifest"]["artifact_name"]
        == "release_evidence_scheduled_refresh_contract"
    )
