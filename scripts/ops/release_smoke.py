from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Literal, Protocol
from urllib import error, request
from urllib.parse import urlparse

RELEASE_SMOKE_SCHEMA_VERSION = "forgeml.release_smoke_result.v1"
RELEASE_SMOKE_CONTRACT_VERSION = "forgeml.release_smoke_contract.v1"

SmokeStatus = Literal["passed", "failed", "skipped"]
StageValidator = Callable[[Any], tuple[bool, str]]


@dataclass(frozen=True)
class ReleaseSmokeStage:
    code: str
    method: str
    path_template: str
    expected_status_code: int
    required: bool
    mutates_data: bool
    description: str


RELEASE_SMOKE_STAGE_DEFINITIONS: tuple[ReleaseSmokeStage, ...] = (
    ReleaseSmokeStage(
        code="health_ready",
        method="GET",
        path_template="/health/ready",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Confirms the API process is ready to serve traffic.",
    ),
    ReleaseSmokeStage(
        code="auth_login",
        method="POST",
        path_template="/api/v1/auth/login",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Authenticates the seeded smoke-test user and obtains an access token.",
    ),
    ReleaseSmokeStage(
        code="auth_identity",
        method="GET",
        path_template="/api/v1/auth/me",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies the issued token is accepted by a protected route.",
    ),
    ReleaseSmokeStage(
        code="project_inventory",
        method="GET",
        path_template="/api/v1/projects",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Lists projects and selects the target project context.",
    ),
    ReleaseSmokeStage(
        code="dataset_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/datasets",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies dataset registry access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="feature_store_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/feature-sets",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies feature store metadata access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="experiment_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/experiments",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies experiment tracking access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="training_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/training-runs",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies training run inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="training_logs_surface",
        method="GET",
        path_template="/api/v1/training-runs/{training_run_id}/logs",
        expected_status_code=200,
        required=False,
        mutates_data=False,
        description="Verifies training logs are readable when the project has a training run.",
    ),
    ReleaseSmokeStage(
        code="model_registry_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/models",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies registered model inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="deployment_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/deployments",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies deployment inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="inference_endpoint_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/inference-endpoints",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies inference endpoint inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="monitoring_summary",
        method="GET",
        path_template="/api/v1/projects/{project_id}/monitoring/summary",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies project monitoring summaries are available.",
    ),
    ReleaseSmokeStage(
        code="alert_rule_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/alert-rules",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies alert rule inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="alert_event_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/alert-events",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies alert event inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="drift_report_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/drift-reports",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies drift report inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="retraining_policy_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/retraining-policies",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies retraining policy inventory access for the selected project.",
    ),
    ReleaseSmokeStage(
        code="retraining_run_inventory",
        method="GET",
        path_template="/api/v1/projects/{project_id}/retraining-runs",
        expected_status_code=200,
        required=True,
        mutates_data=False,
        description="Verifies retraining run inventory access for the selected project.",
    ),
)

STAGES_BY_CODE = {stage.code: stage for stage in RELEASE_SMOKE_STAGE_DEFINITIONS}


@dataclass(frozen=True)
class SmokeHttpResponse:
    status_code: int
    payload: Any


@dataclass(frozen=True)
class SmokeStageResult:
    stage: str
    method: str
    path: str
    required: bool
    status: SmokeStatus
    status_code: int | None
    latency_ms: float
    detail: str


class SmokeTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        access_token: str | None = None,
    ) -> SmokeHttpResponse:
        """Send an HTTP request and return a normalized response."""


class SmokeTransportError(RuntimeError):
    pass


class HttpSmokeTransport:
    def __init__(self, base_url: str, *, timeout_seconds: float = 15.0) -> None:
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("ForgeML smoke base URL must resolve to an http or https URL.")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        access_token: str | None = None,
    ) -> SmokeHttpResponse:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"accept": "application/json"}
        if body is not None:
            headers["content-type"] = "application/json"
        if access_token:
            headers["authorization"] = f"Bearer {access_token}"

        api_request = request.Request(  # noqa: S310
            f"{self._base_url}/{path.lstrip('/')}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(api_request, timeout=self._timeout_seconds) as response:  # noqa: S310
                return SmokeHttpResponse(
                    status_code=response.status,
                    payload=_decode_response(response.read()),
                )
        except error.HTTPError as exc:
            return SmokeHttpResponse(
                status_code=exc.code,
                payload=_decode_response(exc.read()),
            )
        except error.URLError as exc:
            raise SmokeTransportError(str(exc.reason)) from exc


def run_release_smoke(
    *,
    base_url: str,
    email: str,
    password: str,
    project_id: str | None = None,
    timeout_seconds: float = 15.0,
    transport: SmokeTransport | None = None,
) -> dict[str, Any]:
    smoke_transport = transport or HttpSmokeTransport(
        base_url,
        timeout_seconds=timeout_seconds,
    )
    results: list[SmokeStageResult] = []
    access_token: str | None = None
    selected_project_id: str | None = project_id
    selected_training_run_id: str | None = None

    def run_stage(
        code: str,
        *,
        path_values: Mapping[str, str] | None = None,
        payload: Mapping[str, Any] | None = None,
        validator: StageValidator | None = None,
        authenticated: bool = True,
    ) -> Any:
        stage = STAGES_BY_CODE[code]
        path = _format_stage_path(stage, path_values or {})
        started_at = perf_counter()
        try:
            response = smoke_transport.request(
                stage.method,
                path,
                payload=payload,
                access_token=access_token if authenticated else None,
            )
        except SmokeTransportError as exc:
            latency_ms = round((perf_counter() - started_at) * 1000, 3)
            results.append(
                SmokeStageResult(
                    stage=stage.code,
                    method=stage.method,
                    path=path,
                    required=stage.required,
                    status="failed",
                    status_code=None,
                    latency_ms=latency_ms,
                    detail=f"Transport error: {exc}",
                )
            )
            return {}

        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        status_matches = response.status_code == stage.expected_status_code
        validation_passed, validation_detail = (
            validator(response.payload) if validator else (True, "response accepted")
        )
        passed = status_matches and validation_passed
        if not status_matches:
            validation_detail = _failure_detail(response.payload, stage.expected_status_code)
        result_status: SmokeStatus = "passed" if passed else "failed"
        if not passed and not stage.required and response.status_code == 404:
            result_status = "skipped"
            validation_detail = f"optional stage unavailable: {validation_detail}"
        results.append(
            SmokeStageResult(
                stage=stage.code,
                method=stage.method,
                path=path,
                required=stage.required,
                status=result_status,
                status_code=response.status_code,
                latency_ms=latency_ms,
                detail=validation_detail,
            )
        )
        return response.payload

    run_stage("health_ready", authenticated=False, validator=_validate_ready)
    login_payload = run_stage(
        "auth_login",
        payload={"email": email, "password": password},
        authenticated=False,
        validator=_validate_access_token,
    )
    access_token = _access_token(login_payload)
    if not access_token:
        return _build_report(base_url, results, selected_project_id)

    run_stage("auth_identity")
    projects_payload = run_stage("project_inventory")
    selected_project_id = selected_project_id or _first_item_id(projects_payload)
    if not selected_project_id:
        results.append(
            _context_failure(
                STAGES_BY_CODE["project_inventory"],
                "No project context is available. Seed the API or pass --project-id.",
            )
        )
        return _build_report(base_url, results, selected_project_id)

    project_context = {"project_id": selected_project_id}
    for code in (
        "dataset_inventory",
        "feature_store_inventory",
        "experiment_inventory",
    ):
        run_stage(code, path_values=project_context)

    training_payload = run_stage("training_inventory", path_values=project_context)
    selected_training_run_id = _first_item_id(training_payload)
    if selected_training_run_id:
        run_stage(
            "training_logs_surface",
            path_values={"training_run_id": selected_training_run_id},
        )
    else:
        results.append(
            _skipped_stage(
                STAGES_BY_CODE["training_logs_surface"],
                "No training run was available for the optional logs probe.",
            )
        )

    for code in (
        "model_registry_inventory",
        "deployment_inventory",
        "inference_endpoint_inventory",
        "monitoring_summary",
        "alert_rule_inventory",
        "alert_event_inventory",
        "drift_report_inventory",
        "retraining_policy_inventory",
        "retraining_run_inventory",
    ):
        run_stage(code, path_values=project_context)

    return _build_report(base_url, results, selected_project_id)


def build_release_smoke_contract() -> dict[str, Any]:
    return {
        "schema_version": RELEASE_SMOKE_CONTRACT_VERSION,
        "generated_from": ["scripts.ops.release_smoke"],
        "summary": {
            "stage_count": len(RELEASE_SMOKE_STAGE_DEFINITIONS),
            "required_stage_count": sum(
                1 for stage in RELEASE_SMOKE_STAGE_DEFINITIONS if stage.required
            ),
            "mutating_stage_count": sum(
                1 for stage in RELEASE_SMOKE_STAGE_DEFINITIONS if stage.mutates_data
            ),
        },
        "runtime_requirements": {
            "requires_running_api": True,
            "requires_seeded_user": True,
            "requires_project_context": True,
            "mutates_data": False,
        },
        "operator_command": (
            "PYTHONPATH=. python scripts/ops/release_smoke.py "
            "--base-url http://127.0.0.1:8001"
        ),
        "stages": [asdict(stage) for stage in RELEASE_SMOKE_STAGE_DEFINITIONS],
    }


def serialize_release_smoke_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def _build_report(
    base_url: str,
    results: list[SmokeStageResult],
    selected_project_id: str | None,
) -> dict[str, Any]:
    failed_required = [
        result for result in results if result.required and result.status == "failed"
    ]
    status: SmokeStatus = "failed" if failed_required else "passed"
    return {
        "schema_version": RELEASE_SMOKE_SCHEMA_VERSION,
        "status": status,
        "base_url": base_url.rstrip("/"),
        "selected_project_id": selected_project_id,
        "summary": {
            "stage_count": len(results),
            "passed_count": sum(1 for result in results if result.status == "passed"),
            "failed_count": sum(1 for result in results if result.status == "failed"),
            "skipped_count": sum(1 for result in results if result.status == "skipped"),
        },
        "checks": [asdict(result) for result in results],
    }


def _format_stage_path(stage: ReleaseSmokeStage, path_values: Mapping[str, str]) -> str:
    return stage.path_template.format(**path_values)


def _context_failure(stage: ReleaseSmokeStage, detail: str) -> SmokeStageResult:
    return SmokeStageResult(
        stage=f"{stage.code}_context",
        method="CONTEXT",
        path=stage.path_template,
        required=True,
        status="failed",
        status_code=None,
        latency_ms=0.0,
        detail=detail,
    )


def _skipped_stage(stage: ReleaseSmokeStage, detail: str) -> SmokeStageResult:
    return SmokeStageResult(
        stage=stage.code,
        method=stage.method,
        path=stage.path_template,
        required=stage.required,
        status="skipped",
        status_code=None,
        latency_ms=0.0,
        detail=detail,
    )


def _validate_ready(payload: Any) -> tuple[bool, str]:
    if isinstance(payload, dict) and payload.get("status") == "ready":
        return True, "readiness status is ready"
    return False, "readiness response did not report ready"


def _validate_access_token(payload: Any) -> tuple[bool, str]:
    if _access_token(payload):
        return True, "access token issued"
    return False, "login response did not include an access token"


def _access_token(payload: Any) -> str | None:
    if isinstance(payload, dict) and isinstance(payload.get("access_token"), str):
        return payload["access_token"]
    return None


def _first_item_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return None
    first_item = items[0]
    if isinstance(first_item, dict) and isinstance(first_item.get("id"), str):
        return first_item["id"]
    return None


def _failure_detail(payload: Any, expected_status_code: int) -> str:
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if detail:
        return str(detail)
    return f"expected HTTP {expected_status_code}"


def _decode_response(raw_body: bytes) -> Any:
    if not raw_body:
        return {}
    text = raw_body.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_body": text}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a non-mutating ForgeML release-candidate smoke check."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--email", default="admin@forgeml.dev")
    parser.add_argument("--password", default="forgeml-local-admin")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    args = parser.parse_args(argv)

    report = run_release_smoke(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        project_id=args.project_id,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
