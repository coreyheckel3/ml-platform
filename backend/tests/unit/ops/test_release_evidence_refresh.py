import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.ops.refresh_release_evidence import (
    RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION,
    build_cron_example,
    release_evidence_refresh_exit_code,
    run_release_evidence_refresh_once,
    serialize_release_evidence_refresh_report,
)


class FakeRefreshClient:
    def __init__(
        self,
        status: dict[str, object],
        *,
        retrieved_status: str = "passed",
    ) -> None:
        self.status = status
        self.retrieved_status = retrieved_status
        self.status_calls = 0
        self.retrieve_calls = 0

    def refresh_status(
        self,
        *,
        stale_after_seconds: int | None = None,
        refresh_interval_seconds: int | None = None,
    ) -> dict[str, object]:
        self.status_calls += 1
        return {
            **self.status,
            "stale_after_seconds": stale_after_seconds,
            "refresh_interval_seconds": refresh_interval_seconds,
        }

    def retrieve_report(self) -> dict[str, object]:
        self.retrieve_calls += 1
        return {
            "id": "release-evidence-report-2",
            "status": self.retrieved_status,
            "schema_version": "forgeml.release_evidence_retrieval.v1",
        }


def test_release_evidence_refresh_skips_fresh_evidence() -> None:
    client = FakeRefreshClient(
        {
            "status": "fresh",
            "stale": False,
            "recommended_action": "wait_until_next_refresh",
        }
    )

    report = run_release_evidence_refresh_once(
        client,
        stale_after_seconds=86_400,
        refresh_interval_seconds=3_600,
        checked_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )

    assert report["schema_version"] == RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION
    assert report["decision"] == "skipped"
    assert report["reason"] == "release_evidence_fresh"
    assert report["retrieved_report"] is None
    assert client.retrieve_calls == 0
    assert client.status_calls == 1


def test_release_evidence_refresh_retrieves_stale_evidence() -> None:
    client = FakeRefreshClient(
        {
            "status": "stale",
            "stale": True,
            "recommended_action": "retrieve_now",
        }
    )

    report = run_release_evidence_refresh_once(
        client,
        stale_after_seconds=86_400,
        refresh_interval_seconds=3_600,
        checked_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )

    assert report["decision"] == "retrieved"
    assert report["reason"] == "api_recommended_retrieve_now"
    assert report["retrieved_report"] == {
        "id": "release-evidence-report-2",
        "status": "passed",
        "schema_version": "forgeml.release_evidence_retrieval.v1",
    }
    assert report["status_after"] is not None
    assert client.retrieve_calls == 1
    assert client.status_calls == 2


def test_release_evidence_refresh_dry_run_does_not_retrieve() -> None:
    client = FakeRefreshClient(
        {
            "status": "attention",
            "stale": False,
            "recommended_action": "retrieve_now",
        }
    )

    report = run_release_evidence_refresh_once(
        client,
        dry_run=True,
        checked_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )

    assert report["decision"] == "dry_run"
    assert report["reason"] == "api_recommended_retrieve_now"
    assert report["retrieved_report"] is None
    assert report["status_after"] is None
    assert client.retrieve_calls == 0


def test_release_evidence_refresh_exit_code_flags_failed_retrieval() -> None:
    client = FakeRefreshClient(
        {
            "status": "attention",
            "stale": False,
            "recommended_action": "retrieve_now",
        },
        retrieved_status="failed",
    )

    report = run_release_evidence_refresh_once(
        client,
        checked_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )

    assert report["decision"] == "retrieved"
    assert release_evidence_refresh_exit_code(report) == 1


def test_release_evidence_refresh_exit_code_allows_skip_and_successful_refresh() -> None:
    skipped = {
        "schema_version": RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION,
        "decision": "skipped",
        "retrieved_report": None,
    }
    retrieved = {
        "schema_version": RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION,
        "decision": "retrieved",
        "retrieved_report": {"status": "passed"},
    }

    assert release_evidence_refresh_exit_code(skipped) == 0
    assert release_evidence_refresh_exit_code(retrieved) == 0


def test_release_evidence_refresh_serializes_report() -> None:
    payload = {
        "schema_version": RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION,
        "decision": "skipped",
    }

    serialized = serialize_release_evidence_refresh_report(payload)

    assert json.loads(serialized) == payload
    assert serialized.endswith("\n")


def test_release_evidence_refresh_builds_cron_example() -> None:
    command = build_cron_example(
        repo_root=Path("/workspace/ml-platform"),
        base_url="http://127.0.0.1:8001",
        stale_after_seconds=86_400,
    )

    assert command.startswith("*/30 * * * * cd /workspace/ml-platform")
    assert "scripts/ops/refresh_release_evidence.py" in command
    assert "--stale-after-seconds 86400" in command
