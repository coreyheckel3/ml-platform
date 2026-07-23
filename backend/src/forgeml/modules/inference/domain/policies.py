import re

from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceEndpointStatus,
    InferenceRequestStatus,
)
from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_ROUTE_PATTERN = re.compile(r"^/[a-z0-9][a-z0-9/_-]*$")
_SERVABLE_REVISION_STATUSES = {"healthy", "degraded"}


def build_endpoint_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Inference endpoint name must contain a letter or number.")
    return normalized[:80]


def build_route_path(name: str) -> str:
    return f"/inference/{build_endpoint_slug(name)}"


def validate_endpoint_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Inference endpoint name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Inference endpoint name must be at most 120 characters.")


def normalize_route_path(route_path: str) -> str:
    normalized = route_path.strip().lower()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if len(normalized) < 3 or len(normalized) > 160:
        raise DomainValidationError("Inference route path must be between 3 and 160 characters.")
    if not _ROUTE_PATTERN.match(normalized):
        raise DomainValidationError(
            "Inference route path may only contain lowercase letters, numbers, dashes, "
            "underscores, and slashes."
        )
    return normalized


def validate_prediction_payload(payload: dict[str, object]) -> None:
    if len(payload) > 200:
        raise DomainValidationError("Inference payload cannot exceed 200 top-level fields.")
    for key in payload:
        if len(key.strip()) == 0:
            raise DomainValidationError("Inference payload field names cannot be empty.")
        if len(key) > 128:
            raise DomainValidationError(
                "Inference payload field names cannot exceed 128 characters."
            )


def validate_serving_reference(reference: DeploymentRevisionServingReference) -> None:
    if reference.deployment_status != "active":
        raise DomainValidationError("Inference endpoints can only target active deployments.")
    if reference.revision_status not in _SERVABLE_REVISION_STATUSES:
        raise DomainValidationError(
            "Inference endpoints can only target healthy or degraded revisions."
        )
    if reference.traffic_percentage <= 0:
        raise DomainValidationError("Inference endpoints require a revision with active traffic.")


def validate_endpoint_status(status: InferenceEndpointStatus) -> None:
    if status != InferenceEndpointStatus.ACTIVE:
        raise DomainValidationError("Inference endpoint is not active.")


def validate_request_log(
    *,
    status: InferenceRequestStatus,
    latency_ms: float,
    error_message: str | None,
) -> None:
    if latency_ms < 0:
        raise DomainValidationError("Inference latency cannot be negative.")
    if status == InferenceRequestStatus.SUCCEEDED and error_message:
        raise DomainValidationError("Succeeded inference requests cannot include an error message.")
    if status != InferenceRequestStatus.SUCCEEDED and not error_message:
        raise DomainValidationError(
            "Failed or rejected inference requests must include an error message."
        )


def validate_metric_snapshot(
    *,
    window_seconds: int,
    prediction_count: int,
    error_count: int,
    p50_latency_ms: float,
    p95_latency_ms: float,
) -> None:
    if window_seconds <= 0 or window_seconds > 86_400:
        raise DomainValidationError(
            "Inference metric windows must be between 1 second and 24 hours."
        )
    if prediction_count < 0:
        raise DomainValidationError("Inference prediction count cannot be negative.")
    if error_count < 0:
        raise DomainValidationError("Inference error count cannot be negative.")
    if error_count > prediction_count:
        raise DomainValidationError("Inference error count cannot exceed prediction count.")
    if p50_latency_ms < 0 or p95_latency_ms < 0:
        raise DomainValidationError("Inference latency percentiles cannot be negative.")
    if p95_latency_ms < p50_latency_ms:
        raise DomainValidationError("Inference p95 latency cannot be lower than p50 latency.")
