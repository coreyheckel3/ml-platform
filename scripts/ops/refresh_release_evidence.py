from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request

RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION = "forgeml.release_evidence_refresh.v1"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"


class ReleaseEvidenceRefreshError(RuntimeError):
    """Raised when the scheduled release evidence refresh cannot complete."""


class ReleaseEvidenceRefreshClient(Protocol):
    def refresh_status(
        self,
        *,
        stale_after_seconds: int | None = None,
        refresh_interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def retrieve_report(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class ForgeMLReleaseEvidenceRefreshClient:
    base_url: str
    access_token: str
    timeout_seconds: float = 5.0

    def refresh_status(
        self,
        *,
        stale_after_seconds: int | None = None,
        refresh_interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if stale_after_seconds is not None:
            params["stale_after_seconds"] = str(stale_after_seconds)
        if refresh_interval_seconds is not None:
            params["refresh_interval_seconds"] = str(refresh_interval_seconds)
        query = parse.urlencode(params)
        path = "/api/v1/admin/release-evidence/refresh/status"
        return self._request("GET", f"{path}?{query}" if query else path)

    def retrieve_report(self) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/admin/release-evidence/reports/retrieve",
            payload={},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = parse.urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.access_token}",
        }
        if body is not None:
            headers["content-type"] = "application/json"
        api_request = request.Request(  # noqa: S310
            url,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:  # noqa: S310
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            message = _http_error_message(exc)
            raise ReleaseEvidenceRefreshError(message) from exc
        except OSError as exc:
            raise ReleaseEvidenceRefreshError(str(exc)) from exc
        return _json_object(response_body)


def login(
    *,
    base_url: str,
    email: str,
    password: str,
    timeout_seconds: float,
) -> str:
    url = parse.urljoin(base_url.rstrip("/") + "/", "api/v1/auth/login")
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    api_request = request.Request(  # noqa: S310
        url,
        data=body,
        headers={"accept": "application/json", "content-type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(api_request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = _json_object(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        message = _http_error_message(exc)
        raise ReleaseEvidenceRefreshError(message) from exc
    except OSError as exc:
        raise ReleaseEvidenceRefreshError(str(exc)) from exc
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ReleaseEvidenceRefreshError("Login response did not include an access token.")
    return access_token


def run_release_evidence_refresh_once(
    client: ReleaseEvidenceRefreshClient,
    *,
    stale_after_seconds: int | None = None,
    refresh_interval_seconds: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    status_before = client.refresh_status(
        stale_after_seconds=stale_after_seconds,
        refresh_interval_seconds=refresh_interval_seconds,
    )
    should_retrieve, reason = _refresh_decision(status_before, force=force)
    retrieved_report: dict[str, Any] | None = None
    status_after: dict[str, Any] | None = None
    decision = "skipped"

    if should_retrieve and dry_run:
        decision = "dry_run"
    elif should_retrieve:
        retrieved_report = client.retrieve_report()
        status_after = client.refresh_status(
            stale_after_seconds=stale_after_seconds,
            refresh_interval_seconds=refresh_interval_seconds,
        )
        decision = "retrieved"

    return {
        "schema_version": RELEASE_EVIDENCE_REFRESH_SCHEMA_VERSION,
        "checked_at": (checked_at or datetime.now(UTC)).isoformat(),
        "decision": decision,
        "reason": reason,
        "forced": force,
        "dry_run": dry_run,
        "status_before": status_before,
        "retrieved_report": retrieved_report,
        "status_after": status_after,
    }


def serialize_release_evidence_refresh_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def release_evidence_refresh_exit_code(payload: dict[str, Any]) -> int:
    if payload.get("schema_version") == "forgeml.release_evidence_refresh_batch.v1":
        runs = payload.get("runs")
        if not isinstance(runs, list):
            return 1
        return 1 if any(_retrieved_report_failed(run) for run in runs) else 0
    return 1 if _retrieved_report_failed(payload) else 0


def build_cron_example(
    *,
    repo_root: Path,
    base_url: str,
    stale_after_seconds: int,
) -> str:
    command = (
        f"cd {repo_root} && PYTHONPATH=backend/src:. "
        "python scripts/ops/refresh_release_evidence.py "
        f"--base-url {base_url} --stale-after-seconds {stale_after_seconds}"
    )
    return f"*/30 * * * * {command}"


def _refresh_decision(
    status: dict[str, Any],
    *,
    force: bool,
) -> tuple[bool, str]:
    if force:
        return True, "force_requested"
    if status.get("recommended_action") == "retrieve_now":
        return True, "api_recommended_retrieve_now"
    if status.get("stale") is True:
        return True, "release_evidence_stale"
    if status.get("status") in {"missing", "attention", "stale"}:
        return True, f"release_evidence_{status.get('status')}"
    return False, "release_evidence_fresh"


def _retrieved_report_failed(report: object) -> bool:
    if not isinstance(report, dict):
        return True
    if report.get("decision") != "retrieved":
        return False
    retrieved_report = report.get("retrieved_report")
    if not isinstance(retrieved_report, dict):
        return True
    return retrieved_report.get("status") != "passed"


def _http_error_message(exc: error.HTTPError) -> str:
    response_body = exc.read().decode("utf-8", errors="replace")
    try:
        payload = _json_object(response_body)
    except ReleaseEvidenceRefreshError:
        return f"HTTP {exc.code}: {exc.reason}"
    detail = payload.get("detail")
    if isinstance(detail, str):
        return f"HTTP {exc.code}: {detail}"
    return f"HTTP {exc.code}: {exc.reason}"


def _json_object(response_body: str) -> dict[str, Any]:
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise ReleaseEvidenceRefreshError("API response was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ReleaseEvidenceRefreshError("API response was not a JSON object.")
    return payload


def _write_output(output_path: Path | None, payload: dict[str, Any]) -> None:
    output = serialize_release_evidence_refresh_report(payload)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh ForgeML release evidence through the admin API."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("FORGEML_API_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--email", default=os.environ.get("FORGEML_ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("FORGEML_ADMIN_PASSWORD"))
    parser.add_argument("--access-token", default=os.environ.get("FORGEML_ACCESS_TOKEN"))
    parser.add_argument("--stale-after-seconds", type=int)
    parser.add_argument("--refresh-interval-seconds", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=0)
    parser.add_argument("--max-runs", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-cron", action="store_true")
    args = parser.parse_args(argv)

    stale_after_seconds = args.stale_after_seconds or 86_400
    if args.print_cron:
        print(
            build_cron_example(
                repo_root=Path.cwd(),
                base_url=args.base_url,
                stale_after_seconds=stale_after_seconds,
            )
        )
        return 0

    access_token = args.access_token
    if not access_token:
        if not args.email or not args.password:
            parser.error("--access-token or both --email and --password are required")
        access_token = login(
            base_url=args.base_url,
            email=args.email,
            password=args.password,
            timeout_seconds=args.timeout_seconds,
        )

    interval_seconds = 0 if args.once else max(args.interval_seconds, 0)
    max_runs = 1 if args.once else max(args.max_runs, 1)
    client = ForgeMLReleaseEvidenceRefreshClient(
        base_url=args.base_url,
        access_token=access_token,
        timeout_seconds=args.timeout_seconds,
    )
    reports: list[dict[str, Any]] = []
    try:
        for run_index in range(max_runs):
            reports.append(
                run_release_evidence_refresh_once(
                    client,
                    stale_after_seconds=args.stale_after_seconds,
                    refresh_interval_seconds=args.refresh_interval_seconds,
                    force=args.force,
                    dry_run=args.dry_run,
                )
            )
            if interval_seconds <= 0 or run_index == max_runs - 1:
                break
            time.sleep(interval_seconds)
    except ReleaseEvidenceRefreshError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    payload = (
        reports[0]
        if len(reports) == 1
        else {
            "schema_version": "forgeml.release_evidence_refresh_batch.v1",
            "run_count": len(reports),
            "runs": reports,
        }
    )
    _write_output(args.output, payload)
    return release_evidence_refresh_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
