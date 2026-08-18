from uuid import UUID, uuid4

import pytest

from forgeml.modules.inference.domain.entities import DeploymentRevisionServingReference
from forgeml.modules.inference.infrastructure.runtime import (
    EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
    EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION,
    ExternalMovieRecommenderRuntime,
    ExternalMovieRecommenderServingConfig,
    LocalInferenceRuntime,
    RoutedInferenceRuntime,
)


def test_routed_inference_runtime_uses_external_movie_recommender_adapter() -> None:
    calls: list[tuple[str, str, dict[str, object] | None, float]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append((method, url, payload, timeout_seconds))
        return {
            "answer": "Try Toy Story and Paddington 2.",
            "agent_mode": "deterministic",
            "parsed_query": {"text": "family adventure"},
            "recommendations": [
                {
                    "movie_id": 1,
                    "title": "Toy Story (1995)",
                    "genres": ["Animation", "Comedy"],
                    "poster_url": None,
                    "score": 0.92,
                    "retrieval_score": 0.81,
                    "collaborative_score": 0.77,
                    "genre_score": 1.0,
                    "intent_score": 0.88,
                    "reason": "Matches family adventure intent.",
                }
            ],
            "trace": [{"action": "recommend"}],
        }

    runtime = _runtime(transport)
    reference = _serving_reference(
        revision_runtime_config={
            "serving_adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
            "external_base_url": "http://movie-rec.local",
            "timeout_seconds": 2.5,
        }
    )

    result = runtime.predict(
        reference,
        {
            "text": "family adventure",
            "user_id": 3,
            "liked_movie_ids": [1, 2],
            "limit": 3,
        },
    )

    assert calls == [
        (
            "POST",
            "http://movie-rec.local/api/recommend",
            {
                "message": "family adventure",
                "limit": 3,
                "user_id": 3,
                "liked_movie_ids": [1, 2],
            },
            2.5,
        )
    ]
    assert result.output_payload["schema_version"] == (
        EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION
    )
    assert result.output_payload["adapter"] == EXTERNAL_MOVIE_RECOMMENDER_ADAPTER
    assert result.output_payload["prediction_type"] == "recommendations"
    assert result.output_payload["model_artifact_uri"] == reference.model_artifact_uri
    assert result.output_payload["model_format"] == "joblib"
    assert result.output_payload["recommendations"][0]["title"] == "Toy Story (1995)"


def test_external_movie_recommender_health_probe_maps_upstream_status() -> None:
    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        assert method == "GET"
        assert url == "http://movie-rec.local/health"
        assert payload is None
        assert timeout_seconds == 2.5
        return {
            "status": "ok",
            "collaborative_model": "two_tower",
            "agent_mode": "langgraph",
        }

    runtime = _runtime(transport)
    reference = _serving_reference(
        revision_runtime_config={
            "serving_adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
            "external_base_url": "http://movie-rec.local",
            "timeout_seconds": 2.5,
        }
    )

    probe = runtime.health_probe(reference)

    assert probe.status == "healthy"
    assert probe.error_rate < 0.01
    assert probe.details["collaborative_model"] == "two_tower"
    assert probe.details["agent_mode"] == "langgraph"
    assert probe.details["model_artifact_uri"] == reference.model_artifact_uri


def test_external_movie_recommender_health_probe_returns_unhealthy_on_transport_failure() -> None:
    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        raise RuntimeError(f"{method} {url} failed in {timeout_seconds}s")

    runtime = _runtime(transport)
    reference = _serving_reference(
        revision_runtime_config={"serving_adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER}
    )

    probe = runtime.health_probe(reference)

    assert probe.status == "unhealthy"
    assert probe.error_rate == 1.0
    assert "failed" in str(probe.details["error"])


def test_routed_inference_runtime_falls_back_to_local_runtime_for_generic_models() -> None:
    calls: list[tuple[str, str, dict[str, object] | None, float]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        calls.append((method, url, payload, timeout_seconds))
        raise AssertionError("generic model should not call external transport")

    runtime = _runtime(transport)
    result = runtime.predict(_serving_reference(), {"amount": 128.45})

    assert calls == []
    assert 0 <= result.output_payload["score"] <= 1
    assert result.output_payload["features_seen"] == 1


def test_external_movie_recommender_adapter_requires_text_payload() -> None:
    runtime = _runtime(lambda *_args: {})
    reference = _serving_reference(
        revision_runtime_config={"serving_adapter": EXTERNAL_MOVIE_RECOMMENDER_ADAPTER}
    )

    with pytest.raises(ValueError, match="message, text, or query"):
        runtime.predict(reference, {"amount": 128.45})


def _runtime(transport) -> RoutedInferenceRuntime:
    return RoutedInferenceRuntime(
        default_runtime=LocalInferenceRuntime(),
        adapters=(
            ExternalMovieRecommenderRuntime(
                default_config=ExternalMovieRecommenderServingConfig(
                    base_url="http://default-movie-rec.local",
                    recommend_path="/api/recommend",
                    health_path="/health",
                    timeout_seconds=5.0,
                ),
                transport=transport,
            ),
        ),
    )


def _serving_reference(
    *,
    revision_runtime_config: dict[str, object] | None = None,
    revision_id: UUID | None = None,
) -> DeploymentRevisionServingReference:
    return DeploymentRevisionServingReference(
        deployment_id=uuid4(),
        deployment_revision_id=revision_id or uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        deployment_status="active",
        revision_status="healthy",
        revision_runtime_config=revision_runtime_config or {},
        traffic_percentage=100,
        model_version_id=uuid4(),
        model_artifact_uri=(
            "file:///artifacts/training-runs/run-1/"
            "conversational-movie-recommender/model/engine.joblib"
        ),
        model_format="joblib",
        model_signature={
            "inputs": [{"name": "message", "type": "string"}],
            "outputs": [{"name": "recommendations", "type": "array"}],
        },
    )
