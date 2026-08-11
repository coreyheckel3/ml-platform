from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol
from urllib import error, parse, request

AIRFLOW_ORCHESTRATION_SCHEMA_VERSION = "forgeml.airflow_orchestration.v1"
DEFAULT_AIRFLOW_HTTP_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class AirflowDagRunRequest:
    dag_id: str
    dag_run_id: str
    conf: dict[str, object]
    note: str | None = None


@dataclass(frozen=True)
class AirflowDagRunRecord:
    dag_id: str
    dag_run_id: str
    state: str
    external_url: str | None
    conf: dict[str, object]
    metadata: dict[str, object]
    observed_at: datetime


class AirflowWorkflowError(RuntimeError):
    pass


class AirflowRestError(AirflowWorkflowError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class AirflowWorkflowGateway(Protocol):
    def trigger_dag_run(self, request: AirflowDagRunRequest) -> AirflowDagRunRecord:
        raise NotImplementedError

    def get_dag_run(self, *, dag_id: str, dag_run_id: str) -> AirflowDagRunRecord:
        raise NotImplementedError

    def cancel_dag_run(self, *, dag_id: str, dag_run_id: str, note: str) -> AirflowDagRunRecord:
        raise NotImplementedError


class AirflowHttpTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        raise NotImplementedError


class InMemoryAirflowWorkflowGateway:
    def __init__(self, *, base_url: str = "memory://airflow") -> None:
        self._base_url = base_url.rstrip("/")
        self._records: dict[tuple[str, str], AirflowDagRunRecord] = {}
        self.triggered_requests: list[AirflowDagRunRequest] = []
        self.canceled_runs: list[tuple[str, str, str]] = []

    def trigger_dag_run(self, request: AirflowDagRunRequest) -> AirflowDagRunRecord:
        self.triggered_requests.append(request)
        record = AirflowDagRunRecord(
            dag_id=request.dag_id,
            dag_run_id=request.dag_run_id,
            state="queued",
            external_url=_airflow_dag_run_url(self._base_url, request.dag_id, request.dag_run_id),
            conf=request.conf,
            metadata={"note": request.note or ""},
            observed_at=_utcnow(),
        )
        self._records[(request.dag_id, request.dag_run_id)] = record
        return record

    def get_dag_run(self, *, dag_id: str, dag_run_id: str) -> AirflowDagRunRecord:
        record = self._records.get((dag_id, dag_run_id))
        if record is None:
            raise AirflowWorkflowError("Airflow DAG run was not found.")
        return replace(record, observed_at=_utcnow())

    def cancel_dag_run(self, *, dag_id: str, dag_run_id: str, note: str) -> AirflowDagRunRecord:
        record = self.get_dag_run(dag_id=dag_id, dag_run_id=dag_run_id)
        canceled = replace(
            record,
            state="failed",
            metadata={**record.metadata, "cancel_note": note},
            observed_at=_utcnow(),
        )
        self._records[(dag_id, dag_run_id)] = canceled
        self.canceled_runs.append((dag_id, dag_run_id, note))
        return canceled


class UrllibAirflowHttpTransport:
    def __init__(
        self,
        *,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = DEFAULT_AIRFLOW_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._authorization_header = _basic_auth_header(username, password)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._authorization_header:
            headers["Authorization"] = self._authorization_header
        api_request = request.Request(  # noqa: S310
            f"{self._base_url}{path}",
            data=body,
            method=method.upper(),
            headers=headers,
        )
        try:
            with request.urlopen(api_request, timeout=self._timeout_seconds) as response:  # noqa: S310
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise AirflowRestError(exc.code, _http_error_message(exc)) from exc
        except OSError as exc:
            raise AirflowWorkflowError(str(exc)) from exc

        if not response_body:
            return {}
        parsed = json.loads(response_body)
        if not isinstance(parsed, dict):
            raise AirflowWorkflowError("Airflow REST response must be a JSON object.")
        return parsed


class AirflowHttpWorkflowGateway:
    def __init__(
        self,
        *,
        base_url: str,
        transport: AirflowHttpTransport | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = DEFAULT_AIRFLOW_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport or UrllibAirflowHttpTransport(
            base_url=self._base_url,
            username=username,
            password=password,
            timeout_seconds=timeout_seconds,
        )

    def trigger_dag_run(self, request: AirflowDagRunRequest) -> AirflowDagRunRecord:
        response = self._transport.request_json(
            "POST",
            _dag_run_collection_path(request.dag_id),
            payload={
                "dag_run_id": request.dag_run_id,
                "conf": request.conf,
                "note": request.note or "Triggered by ForgeML.",
            },
        )
        return _record_from_payload(response, base_url=self._base_url, fallback=request)

    def get_dag_run(self, *, dag_id: str, dag_run_id: str) -> AirflowDagRunRecord:
        response = self._transport.request_json(
            "GET",
            _dag_run_path(dag_id, dag_run_id),
        )
        return _record_from_payload(
            response,
            base_url=self._base_url,
            fallback=AirflowDagRunRequest(dag_id=dag_id, dag_run_id=dag_run_id, conf={}),
        )

    def cancel_dag_run(self, *, dag_id: str, dag_run_id: str, note: str) -> AirflowDagRunRecord:
        response = self._transport.request_json(
            "PATCH",
            _dag_run_path(dag_id, dag_run_id),
            payload={"state": "failed", "note": note},
        )
        return _record_from_payload(
            response,
            base_url=self._base_url,
            fallback=AirflowDagRunRequest(dag_id=dag_id, dag_run_id=dag_run_id, conf={}),
        )


def build_airflow_workflow_gateway(
    *,
    enabled: bool,
    base_url: str,
    username: str | None,
    password: str | None,
    timeout_seconds: float = DEFAULT_AIRFLOW_HTTP_TIMEOUT_SECONDS,
) -> AirflowWorkflowGateway | None:
    if not enabled:
        return None
    return AirflowHttpWorkflowGateway(
        base_url=base_url,
        username=username,
        password=password,
        timeout_seconds=timeout_seconds,
    )


def _record_from_payload(
    payload: Mapping[str, object],
    *,
    base_url: str,
    fallback: AirflowDagRunRequest,
) -> AirflowDagRunRecord:
    dag_id = str(payload.get("dag_id") or fallback.dag_id)
    dag_run_id = str(payload.get("dag_run_id") or fallback.dag_run_id)
    conf = payload.get("conf")
    return AirflowDagRunRecord(
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        state=str(payload.get("state") or "unknown"),
        external_url=_airflow_dag_run_url(base_url, dag_id, dag_run_id),
        conf=(
            {str(key): value for key, value in conf.items()}
            if isinstance(conf, Mapping)
            else fallback.conf
        ),
        metadata={
            "schema_version": AIRFLOW_ORCHESTRATION_SCHEMA_VERSION,
            "run_type": payload.get("run_type"),
            "logical_date": payload.get("logical_date"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "note": payload.get("note"),
        },
        observed_at=_utcnow(),
    )


def _dag_run_collection_path(dag_id: str) -> str:
    return f"/api/v1/dags/{parse.quote(dag_id, safe='')}/dagRuns"


def _dag_run_path(dag_id: str, dag_run_id: str) -> str:
    return f"{_dag_run_collection_path(dag_id)}/{parse.quote(dag_run_id, safe='')}"


def _airflow_dag_run_url(base_url: str, dag_id: str, dag_run_id: str) -> str:
    query = parse.urlencode({"dag_id": dag_id, "dag_run_id": dag_run_id})
    return f"{base_url.rstrip('/')}/dags/{parse.quote(dag_id, safe='')}/grid?{query}"


def _basic_auth_header(username: str | None, password: str | None) -> str | None:
    if not username or not password:
        return None
    credentials = f"{username}:{password}".encode()
    encoded = base64.b64encode(credentials).decode("ascii")
    return f"Basic {encoded}"


def _http_error_message(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except OSError:
        body = ""
    return body or f"Airflow REST request failed with status {exc.code}."


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
