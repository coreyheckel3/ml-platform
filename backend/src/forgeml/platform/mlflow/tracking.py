from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib import error, parse, request
from uuid import UUID

MLFLOW_TRACKING_SYNC_SCHEMA_VERSION = "forgeml.mlflow_tracking_sync.v1"
DEFAULT_MLFLOW_HTTP_TIMEOUT_SECONDS = 5.0
_TAG_KEY_PATTERN = re.compile(r"[^A-Za-z0-9_. /-]+")


@dataclass(frozen=True)
class MLflowArtifactReference:
    name: str
    artifact_type: str
    uri: str
    media_type: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class MLflowRunRecord:
    experiment_name: str
    run_name: str
    organization_id: UUID
    project_id: UUID
    experiment_id: UUID
    experiment_run_id: UUID
    training_run_id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    artifact_uri: str
    parameters: dict[str, str]
    metrics: dict[str, float]
    tags: dict[str, str]
    artifacts: tuple[MLflowArtifactReference, ...]


@dataclass(frozen=True)
class MLflowSyncResult:
    tracking_uri: str
    experiment_name: str
    run_id: str | None
    status: str
    logged_param_count: int
    logged_metric_count: int
    logged_artifact_count: int
    error_message: str | None = None
    created_at: datetime | None = None
    schema_version: str = MLFLOW_TRACKING_SYNC_SCHEMA_VERSION


class MLflowTrackingError(RuntimeError):
    pass


class MLflowRestError(MLflowTrackingError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class MLflowTrackingGateway(Protocol):
    def sync_training_run(self, record: MLflowRunRecord) -> MLflowSyncResult:
        raise NotImplementedError


class MLflowHttpTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str] | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        raise NotImplementedError


class DisabledMLflowTrackingGateway:
    def __init__(self, *, tracking_uri: str) -> None:
        self._tracking_uri = tracking_uri.strip()

    def sync_training_run(self, record: MLflowRunRecord) -> MLflowSyncResult:
        return MLflowSyncResult(
            tracking_uri=self._tracking_uri,
            experiment_name=record.experiment_name,
            run_id=None,
            status="disabled",
            logged_param_count=0,
            logged_metric_count=0,
            logged_artifact_count=0,
            created_at=_utcnow(),
        )


class InMemoryMLflowTrackingGateway:
    def __init__(self, *, tracking_uri: str = "memory://forgeml") -> None:
        self._tracking_uri = tracking_uri
        self._records: list[MLflowRunRecord] = []
        self._results: list[MLflowSyncResult] = []

    @property
    def records(self) -> tuple[MLflowRunRecord, ...]:
        return tuple(self._records)

    @property
    def results(self) -> tuple[MLflowSyncResult, ...]:
        return tuple(self._results)

    def sync_training_run(self, record: MLflowRunRecord) -> MLflowSyncResult:
        self._records.append(record)
        result = MLflowSyncResult(
            tracking_uri=self._tracking_uri,
            experiment_name=record.experiment_name,
            run_id=f"in-memory:{record.training_run_id}",
            status="synced",
            logged_param_count=len(record.parameters),
            logged_metric_count=len(record.metrics),
            logged_artifact_count=len(record.artifacts),
            created_at=_utcnow(),
        )
        self._results.append(result)
        return result


class UrllibMLflowHttpTransport:
    def __init__(
        self,
        *,
        tracking_uri: str,
        timeout_seconds: float = DEFAULT_MLFLOW_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        self._tracking_uri = tracking_uri.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str] | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        url = self._url(path, query)
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        api_request = request.Request(  # noqa: S310
            url,
            data=body,
            method=method.upper(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(  # noqa: S310
                api_request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise MLflowRestError(exc.code, _http_error_message(exc)) from exc
        except OSError as exc:
            raise MLflowTrackingError(str(exc)) from exc

        if not response_body:
            return {}
        parsed = json.loads(response_body)
        if not isinstance(parsed, dict):
            raise MLflowTrackingError("MLflow REST response must be a JSON object.")
        return parsed

    def _url(self, path: str, query: Mapping[str, str] | None) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        if not query:
            return f"{self._tracking_uri}{normalized_path}"
        return (
            f"{self._tracking_uri}{normalized_path}?"
            f"{parse.urlencode({key: value for key, value in query.items()})}"
        )


class MLflowHttpTrackingGateway:
    def __init__(
        self,
        *,
        tracking_uri: str,
        transport: MLflowHttpTransport | None = None,
        timeout_seconds: float = DEFAULT_MLFLOW_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        self._tracking_uri = tracking_uri.rstrip("/")
        self._transport = transport or UrllibMLflowHttpTransport(
            tracking_uri=self._tracking_uri,
            timeout_seconds=timeout_seconds,
        )

    def sync_training_run(self, record: MLflowRunRecord) -> MLflowSyncResult:
        experiment_id = self._get_or_create_experiment_id(record.experiment_name)
        run_id = self._create_run(experiment_id, record)
        self._log_batch(run_id, record)
        self._update_run_status(run_id, record)
        return MLflowSyncResult(
            tracking_uri=self._tracking_uri,
            experiment_name=record.experiment_name,
            run_id=run_id,
            status="synced",
            logged_param_count=len(record.parameters),
            logged_metric_count=len(record.metrics),
            logged_artifact_count=len(record.artifacts),
            created_at=_utcnow(),
        )

    def _get_or_create_experiment_id(self, experiment_name: str) -> str:
        try:
            response = self._transport.request_json(
                "GET",
                "/api/2.0/mlflow/experiments/get-by-name",
                query={"experiment_name": experiment_name},
            )
        except MLflowRestError as exc:
            if exc.status_code != 404:
                raise
            response = {}

        experiment = response.get("experiment")
        if isinstance(experiment, Mapping) and experiment.get("experiment_id") is not None:
            return str(experiment["experiment_id"])

        created = self._transport.request_json(
            "POST",
            "/api/2.0/mlflow/experiments/create",
            payload={"name": experiment_name},
        )
        experiment_id = created.get("experiment_id")
        if experiment_id is None:
            raise MLflowTrackingError("MLflow experiment creation did not return an id.")
        return str(experiment_id)

    def _create_run(self, experiment_id: str, record: MLflowRunRecord) -> str:
        response = self._transport.request_json(
            "POST",
            "/api/2.0/mlflow/runs/create",
            payload={
                "experiment_id": experiment_id,
                "start_time": _epoch_millis(record.started_at or _utcnow()),
                "tags": _mlflow_tags(
                    {
                        **record.tags,
                        "mlflow.runName": record.run_name,
                        "mlflow.source.name": "ForgeML",
                    }
                ),
            },
        )
        run = response.get("run")
        if not isinstance(run, Mapping):
            raise MLflowTrackingError("MLflow run creation did not return run metadata.")
        info = run.get("info")
        if not isinstance(info, Mapping) or info.get("run_id") is None:
            raise MLflowTrackingError("MLflow run creation did not return a run id.")
        return str(info["run_id"])

    def _log_batch(self, run_id: str, record: MLflowRunRecord) -> None:
        timestamp = _epoch_millis(record.completed_at or _utcnow())
        self._transport.request_json(
            "POST",
            "/api/2.0/mlflow/runs/log-batch",
            payload={
                "run_id": run_id,
                "params": [
                    {"key": key, "value": value}
                    for key, value in sorted(record.parameters.items())
                ],
                "metrics": [
                    {
                        "key": key,
                        "value": value,
                        "timestamp": timestamp,
                        "step": 0,
                    }
                    for key, value in sorted(record.metrics.items())
                ],
                "tags": _mlflow_tags(
                    {
                        **record.tags,
                        **_artifact_reference_tags(record.artifacts),
                    }
                ),
            },
        )

    def _update_run_status(self, run_id: str, record: MLflowRunRecord) -> None:
        self._transport.request_json(
            "POST",
            "/api/2.0/mlflow/runs/update",
            payload={
                "run_id": run_id,
                "status": _mlflow_run_status(record.status),
                "end_time": _epoch_millis(record.completed_at or _utcnow()),
            },
        )


def build_mlflow_tracking_gateway(
    *,
    enabled: bool,
    tracking_uri: str,
    timeout_seconds: float = DEFAULT_MLFLOW_HTTP_TIMEOUT_SECONDS,
) -> MLflowTrackingGateway | None:
    if not enabled:
        return None
    return MLflowHttpTrackingGateway(
        tracking_uri=tracking_uri,
        timeout_seconds=timeout_seconds,
    )


def build_training_run_mlflow_record(
    *,
    experiment_prefix: str,
    organization_id: UUID,
    project_id: UUID,
    experiment_id: UUID,
    experiment_run_id: UUID,
    training_run_id: UUID,
    run_name: str,
    status: str,
    started_at: datetime | None,
    completed_at: datetime | None,
    artifact_uri: str,
    algorithm: str,
    model_type: str,
    objective_metric_name: str,
    parameters: Mapping[str, object],
    metrics: Mapping[str, float],
    evaluation_report: Mapping[str, object],
) -> MLflowRunRecord:
    mlflow_parameters = _string_parameters(
        {
            "algorithm": algorithm,
            "model_type": model_type,
            "objective_metric_name": objective_metric_name,
            **{str(key): value for key, value in parameters.items()},
        }
    )
    return MLflowRunRecord(
        experiment_name=_experiment_name(
            experiment_prefix=experiment_prefix,
            organization_id=organization_id,
            project_id=project_id,
            experiment_id=experiment_id,
        ),
        run_name=run_name.strip() or f"training-run-{training_run_id}",
        organization_id=organization_id,
        project_id=project_id,
        experiment_id=experiment_id,
        experiment_run_id=experiment_run_id,
        training_run_id=training_run_id,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        artifact_uri=artifact_uri,
        parameters=mlflow_parameters,
        metrics=_finite_metrics(metrics),
        tags={
            "forgeml.organization_id": str(organization_id),
            "forgeml.project_id": str(project_id),
            "forgeml.experiment_id": str(experiment_id),
            "forgeml.experiment_run_id": str(experiment_run_id),
            "forgeml.training_run_id": str(training_run_id),
            "forgeml.status": status,
            "forgeml.artifact_uri": artifact_uri,
        },
        artifacts=_artifact_references(evaluation_report),
    )


def mlflow_sync_result_payload(result: MLflowSyncResult) -> dict[str, object]:
    return {
        "schema_version": result.schema_version,
        "tracking_uri": result.tracking_uri,
        "experiment_name": result.experiment_name,
        "run_id": result.run_id,
        "status": result.status,
        "logged_param_count": result.logged_param_count,
        "logged_metric_count": result.logged_metric_count,
        "logged_artifact_count": result.logged_artifact_count,
        "error_message": result.error_message,
        "created_at": (result.created_at or _utcnow()).isoformat(),
    }


def failed_mlflow_sync_result(
    *,
    tracking_uri: str,
    experiment_name: str,
    error_message: str,
) -> MLflowSyncResult:
    return MLflowSyncResult(
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_id=None,
        status="failed",
        logged_param_count=0,
        logged_metric_count=0,
        logged_artifact_count=0,
        error_message=error_message,
        created_at=_utcnow(),
    )


def _artifact_references(
    evaluation_report: Mapping[str, object],
) -> tuple[MLflowArtifactReference, ...]:
    training_execution = evaluation_report.get("training_execution")
    if not isinstance(training_execution, Mapping):
        return ()
    raw_artifacts = training_execution.get("artifacts")
    if not isinstance(raw_artifacts, list):
        return ()

    artifacts: list[MLflowArtifactReference] = []
    for index, raw_artifact in enumerate(raw_artifacts):
        if not isinstance(raw_artifact, Mapping):
            continue
        name = str(raw_artifact.get("name") or f"artifact-{index}")
        uri = str(raw_artifact.get("uri") or "").strip()
        if not uri:
            continue
        metadata = raw_artifact.get("metadata")
        artifacts.append(
            MLflowArtifactReference(
                name=name,
                artifact_type=str(raw_artifact.get("artifact_type") or "artifact"),
                uri=uri,
                media_type=str(raw_artifact.get("media_type") or "application/octet-stream"),
                metadata=(
                    {str(key): value for key, value in metadata.items()}
                    if isinstance(metadata, Mapping)
                    else {}
                ),
            )
        )
    return tuple(artifacts)


def _artifact_reference_tags(
    artifacts: tuple[MLflowArtifactReference, ...],
) -> dict[str, str]:
    tags = {"forgeml.artifact.count": str(len(artifacts))}
    for artifact in artifacts:
        prefix = f"forgeml.artifact.{_clean_mlflow_key(artifact.name)}"
        tags[f"{prefix}.uri"] = artifact.uri
        tags[f"{prefix}.type"] = artifact.artifact_type
        tags[f"{prefix}.media_type"] = artifact.media_type
        if artifact.metadata.get("sha256") is not None:
            tags[f"{prefix}.sha256"] = str(artifact.metadata["sha256"])
        if artifact.metadata.get("size_bytes") is not None:
            tags[f"{prefix}.size_bytes"] = str(artifact.metadata["size_bytes"])
    return tags


def _mlflow_tags(tags: Mapping[str, str]) -> list[dict[str, str]]:
    return [
        {"key": _clean_mlflow_key(key), "value": value}
        for key, value in sorted(tags.items())
        if key.strip()
    ]


def _string_parameters(parameters: Mapping[str, object]) -> dict[str, str]:
    return {
        _clean_mlflow_key(str(key)): _string_value(value)
        for key, value in sorted(parameters.items())
        if str(key).strip()
    }


def _finite_metrics(metrics: Mapping[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        metric_value = float(value)
        if math.isfinite(metric_value):
            normalized[_clean_mlflow_key(str(key))] = metric_value
    return normalized


def _string_value(value: object) -> str:
    if isinstance(value, (bool, int, float, list, tuple, dict)) or value is None:
        return json.dumps(value, sort_keys=True)
    return str(value)


def _experiment_name(
    *,
    experiment_prefix: str,
    organization_id: UUID,
    project_id: UUID,
    experiment_id: UUID,
) -> str:
    prefix = experiment_prefix.strip().strip("/")
    if not prefix:
        prefix = "forgeml"
    return (
        f"{prefix}/organizations/{organization_id}/projects/{project_id}"
        f"/experiments/{experiment_id}"
    )


def _clean_mlflow_key(value: str) -> str:
    normalized = _TAG_KEY_PATTERN.sub("_", value.strip())
    return normalized[:250] or "forgeml_key"


def _mlflow_run_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "succeeded":
        return "FINISHED"
    if normalized == "canceled":
        return "KILLED"
    return "FAILED"


def _epoch_millis(value: datetime) -> int:
    timestamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return int(timestamp.timestamp() * 1000)


def _http_error_message(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except OSError:
        body = ""
    return body or f"MLflow REST request failed with status {exc.code}."


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
