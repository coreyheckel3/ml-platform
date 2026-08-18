import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from urllib import error, request
from urllib.parse import urljoin

from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceHealthProbeResult,
    InferencePredictionResult,
)

EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION = (
    "forgeml.external_movie_recommender_serving.v1"
)
EXTERNAL_MOVIE_RECOMMENDER_ADAPTER = "conversational-movie-recommender"

JsonTransport = Callable[[str, str, Mapping[str, object] | None, float], dict[str, object]]


@dataclass(frozen=True)
class ExternalMovieRecommenderServingConfig:
    base_url: str
    recommend_path: str
    health_path: str
    timeout_seconds: float


class RoutedInferenceRuntime:
    def __init__(
        self,
        *,
        default_runtime: "LocalInferenceRuntime",
        adapters: Sequence["ExternalMovieRecommenderRuntime"],
    ) -> None:
        self._default_runtime = default_runtime
        self._adapters = tuple(adapters)

    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        return self._runtime_for(reference).predict(reference, payload)

    def health_probe(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> InferenceHealthProbeResult:
        return self._runtime_for(reference).health_probe(reference)

    def _runtime_for(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> "LocalInferenceRuntime | ExternalMovieRecommenderRuntime":
        for adapter in self._adapters:
            if adapter.can_handle(reference):
                return adapter
        return self._default_runtime


def build_local_inference_runtime(
    *,
    movie_recommender_base_url: str = "http://127.0.0.1:8000",
    timeout_seconds: float = 5.0,
) -> RoutedInferenceRuntime:
    return RoutedInferenceRuntime(
        default_runtime=LocalInferenceRuntime(),
        adapters=(
            ExternalMovieRecommenderRuntime(
                default_config=ExternalMovieRecommenderServingConfig(
                    base_url=movie_recommender_base_url,
                    recommend_path="/api/recommend",
                    health_path="/health",
                    timeout_seconds=timeout_seconds,
                )
            ),
        ),
    )


class LocalInferenceRuntime:
    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        started_at = time.perf_counter()
        serialized_payload = json.dumps(payload, sort_keys=True, default=str).encode()
        fingerprint = hashlib.sha256(serialized_payload).hexdigest()
        score = int(fingerprint[:8], 16) / 0xFFFFFFFF
        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        return InferencePredictionResult(
            output_payload={
                "prediction_id": fingerprint[:16],
                "score": round(score, 6),
                "model_version_id": str(reference.model_version_id),
                "features_seen": len(payload),
                "signature": reference.model_signature,
            },
            latency_ms=latency_ms,
        )

    def health_probe(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> InferenceHealthProbeResult:
        started_at = time.perf_counter()
        status = "healthy" if reference.revision_status == "healthy" else "degraded"
        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        error_rate = 0.001 if status == "healthy" else 0.05
        return InferenceHealthProbeResult(
            status=status,
            latency_ms=latency_ms,
            error_rate=error_rate,
            details={
                "model_version_id": str(reference.model_version_id),
                "deployment_revision_id": str(reference.deployment_revision_id),
                "traffic_percentage": reference.traffic_percentage,
            },
        )


class ExternalMovieRecommenderRuntime:
    def __init__(
        self,
        *,
        default_config: ExternalMovieRecommenderServingConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        self._default_config = default_config
        self._transport = transport or _urllib_json_transport

    def can_handle(self, reference: DeploymentRevisionServingReference) -> bool:
        return _configured_adapter_name(reference) == EXTERNAL_MOVIE_RECOMMENDER_ADAPTER

    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        started_at = time.perf_counter()
        config = self._config_for(reference)
        request_payload = _movie_recommend_request_payload(payload)
        response_payload = self._transport(
            "POST",
            _joined_url(config.base_url, config.recommend_path),
            request_payload,
            config.timeout_seconds,
        )
        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        return InferencePredictionResult(
            output_payload=_movie_recommend_output_payload(
                reference=reference,
                request_payload=request_payload,
                response_payload=response_payload,
            ),
            latency_ms=latency_ms,
        )

    def health_probe(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> InferenceHealthProbeResult:
        started_at = time.perf_counter()
        config = self._config_for(reference)
        details: dict[str, object] = {
            "schema_version": EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION,
            "adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
            "base_url": config.base_url,
            "model_version_id": str(reference.model_version_id),
            "model_artifact_uri": reference.model_artifact_uri,
        }
        try:
            response_payload = self._transport(
                "GET",
                _joined_url(config.base_url, config.health_path),
                None,
                config.timeout_seconds,
            )
        except Exception as exc:
            latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
            return InferenceHealthProbeResult(
                status="unhealthy",
                latency_ms=latency_ms,
                error_rate=1.0,
                details={**details, "error": str(exc)},
            )

        latency_ms = max((time.perf_counter() - started_at) * 1000, 0.01)
        upstream_status = str(response_payload.get("status", "unknown")).lower()
        status = "healthy" if upstream_status in {"healthy", "ok"} else "degraded"
        return InferenceHealthProbeResult(
            status=status,
            latency_ms=latency_ms,
            error_rate=0.001 if status == "healthy" else 0.05,
            details={
                **details,
                "upstream": response_payload,
                "collaborative_model": response_payload.get("collaborative_model"),
                "agent_mode": response_payload.get("agent_mode"),
            },
        )

    def _config_for(
        self,
        reference: DeploymentRevisionServingReference,
    ) -> ExternalMovieRecommenderServingConfig:
        config = reference.revision_runtime_config
        return ExternalMovieRecommenderServingConfig(
            base_url=_string_config(config, "external_base_url", self._default_config.base_url),
            recommend_path=_string_config(
                config,
                "recommend_path",
                self._default_config.recommend_path,
            ),
            health_path=_string_config(config, "health_path", self._default_config.health_path),
            timeout_seconds=_float_config(
                config,
                "timeout_seconds",
                self._default_config.timeout_seconds,
            ),
        )


def _configured_adapter_name(reference: DeploymentRevisionServingReference) -> str:
    candidates = (
        reference.revision_runtime_config.get("serving_adapter"),
        reference.revision_runtime_config.get("adapter"),
        reference.model_signature.get("serving_adapter"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower().replace("_", "-")
    return ""


def _movie_recommend_request_payload(payload: Mapping[str, object]) -> dict[str, object]:
    message = _optional_string(payload, "message")
    if message is None:
        message = _optional_string(payload, "text")
    if message is None:
        message = _optional_string(payload, "query")
    if message is None:
        raise ValueError(
            "Movie recommender inference requires a non-empty message, text, or query field."
        )

    request_payload: dict[str, object] = {
        "message": message,
        "limit": _int_config(payload, "limit", 5, minimum=1, maximum=20),
    }
    for field in ("user_id", "user_age"):
        value = payload.get(field)
        if value is not None:
            request_payload[field] = _integer(value, field)
    chat_summary = _optional_string(payload, "chat_summary")
    if chat_summary is not None:
        request_payload["chat_summary"] = chat_summary
    liked_movie_ids = payload.get("liked_movie_ids")
    if liked_movie_ids is not None:
        request_payload["liked_movie_ids"] = _integer_list(liked_movie_ids, "liked_movie_ids")
    history = payload.get("history")
    if history is not None:
        request_payload["history"] = _chat_history(history)
    return request_payload


def _movie_recommend_output_payload(
    *,
    reference: DeploymentRevisionServingReference,
    request_payload: Mapping[str, object],
    response_payload: Mapping[str, object],
) -> dict[str, object]:
    recommendations = response_payload.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = []
    return {
        "schema_version": EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION,
        "adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
        "prediction_type": "recommendations",
        "model_version_id": str(reference.model_version_id),
        "model_artifact_uri": reference.model_artifact_uri,
        "model_format": reference.model_format,
        "request": {
            "message": request_payload["message"],
            "limit": request_payload["limit"],
            "user_id": request_payload.get("user_id"),
            "liked_movie_ids": request_payload.get("liked_movie_ids", []),
        },
        "answer": response_payload.get("answer", ""),
        "agent_mode": response_payload.get("agent_mode", "unknown"),
        "parsed_query": response_payload.get("parsed_query", {}),
        "recommendations": [_recommendation_item(item) for item in recommendations],
        "needs_clarification": bool(response_payload.get("needs_clarification", False)),
        "clarification_question": response_payload.get("clarification_question"),
        "suggestions": response_payload.get("suggestions", []),
        "guardrail": response_payload.get("guardrail"),
        "trace": response_payload.get("trace", []),
    }


def _recommendation_item(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {
        "movie_id": value.get("movie_id"),
        "title": value.get("title"),
        "genres": value.get("genres", []),
        "poster_url": value.get("poster_url"),
        "score": value.get("score"),
        "retrieval_score": value.get("retrieval_score"),
        "collaborative_score": value.get("collaborative_score"),
        "genre_score": value.get("genre_score"),
        "intent_score": value.get("intent_score"),
        "ann_score": value.get("ann_score", 0.0),
        "reason": value.get("reason", ""),
    }


def _urllib_json_transport(
    method: str,
    url: str,
    payload: Mapping[str, object] | None,
    timeout_seconds: float,
) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    api_request = request.Request(  # noqa: S310
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    try:
        with request.urlopen(api_request, timeout=timeout_seconds) as response:  # noqa: S310
            decoded = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"External movie recommender returned {exc.code}: {body}") from exc
    if not decoded.strip():
        return {}
    parsed = json.loads(decoded)
    if not isinstance(parsed, dict):
        raise RuntimeError("External movie recommender returned a non-object JSON payload.")
    return {str(key): value for key, value in parsed.items()}


def _joined_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _string_config(config: Mapping[str, object], key: str, default: str) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _float_config(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric.")
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"{key} must be greater than zero.")
    return numeric


def _int_config(
    config: Mapping[str, object],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = config.get(key, default)
    integer = _integer(value, key)
    if integer < minimum or integer > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return integer


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _integer(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    return value


def _integer_list(value: object, field_name: str) -> list[int]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of integers.")
    return [_integer(item, field_name) for item in value]


def _chat_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("history must be a list of chat messages.")
    messages: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("history entries must be objects.")
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError("history entries require role and content strings.")
        messages.append({"role": role, "content": content})
    return messages
