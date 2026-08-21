import json
from pathlib import Path

from scripts.ci.check_release_evidence_notifications_contract import (
    build_release_evidence_notifications_contract,
    check_release_evidence_notifications_contract,
    serialize_release_evidence_notifications_contract,
    validate_release_evidence_notifications_definition,
    write_release_evidence_notifications_contract,
)


def test_release_evidence_notifications_definition_validates_assets() -> None:
    assert validate_release_evidence_notifications_definition(Path(".")) == ()


def test_release_evidence_notifications_contract_round_trip(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-notifications.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_notifications_contract.py\n",
        encoding="utf-8",
    )

    write_release_evidence_notifications_contract(contract_path)
    passed, detail = check_release_evidence_notifications_contract(
        contract_path,
        ci_path=ci_path,
        repo_root=Path("."),
    )

    assert passed, detail


def test_release_evidence_notifications_contract_detects_stale_contract(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-notifications.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_notifications_contract(contract_path)
    contract_path.write_text('{"schema_version":"stale"}\n', encoding="utf-8")
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_notifications_contract.py\n",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_notifications_contract(
        contract_path,
        ci_path=ci_path,
        repo_root=Path("."),
    )

    assert not passed
    assert "stale" in detail


def test_release_evidence_notifications_contract_requires_ci_wiring(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "release-evidence-notifications.v1.json"
    ci_path = tmp_path / "ci.yml"
    write_release_evidence_notifications_contract(contract_path)
    ci_path.write_text(
        "python scripts/ci/check_release_evidence_scheduled_refresh_contract.py\n",
        encoding="utf-8",
    )

    passed, detail = check_release_evidence_notifications_contract(
        contract_path,
        ci_path=ci_path,
        repo_root=Path("."),
    )

    assert not passed
    assert "not wired into CI" in detail


def test_checked_in_release_evidence_notifications_contract_matches_source() -> None:
    passed, detail = check_release_evidence_notifications_contract(
        Path("contracts/ops/release-evidence-notifications.v1.json")
    )

    assert passed, detail


def test_release_evidence_notifications_contract_shape() -> None:
    parsed = json_loads(
        serialize_release_evidence_notifications_contract(
            build_release_evidence_notifications_contract()
        )
    )

    assert parsed["schema_version"] == "forgeml.release_evidence_notifications_contract.v1"
    assert parsed["notification_payload"]["trigger_statuses"] == ["failed"]
    assert parsed["adapters"]["protocol"] == "ReleaseEvidenceNotificationGateway"
    assert "WebhookReleaseEvidenceNotificationGateway" in parsed["adapters"][
        "implementations"
    ]
    assert parsed["api"]["response_field"] == "notification_policy"
    assert "release_evidence.notification_failed" in parsed["audit"]["actions"]
    assert (
        parsed["release_manifest"]["quality_gate_name"]
        == "release_evidence_notifications_contract"
    )


def json_loads(payload: str) -> dict[str, object]:
    parsed = json.loads(payload)
    assert isinstance(parsed, dict)
    return parsed
