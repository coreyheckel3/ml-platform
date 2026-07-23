import math
import re

from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")
_ALLOWED_MODEL_TYPES = {
    "custom",
    "lightgbm",
    "pytorch",
    "semantic-search",
    "sklearn",
    "xgboost",
}


def build_experiment_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Experiment name must contain at least one letter or number.")
    return normalized[:80]


def validate_experiment_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Experiment name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Experiment name must be at most 120 characters.")


def validate_run_name(run_name: str) -> None:
    stripped = run_name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Experiment run name must be at least 3 characters.")
    if len(stripped) > 160:
        raise DomainValidationError("Experiment run name must be at most 160 characters.")
    if not _RUN_NAME_PATTERN.match(stripped):
        raise DomainValidationError("Experiment run name contains unsupported characters.")


def validate_model_type(model_type: str) -> None:
    normalized = model_type.strip().lower()
    if normalized not in _ALLOWED_MODEL_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_MODEL_TYPES))
        raise DomainValidationError(f"Model type must be one of: {allowed}.")


def normalize_model_type(model_type: str) -> str:
    validate_model_type(model_type)
    return model_type.strip().lower()


def validate_tracking_payload(
    parameters: dict[str, object],
    metrics: dict[str, float] | None = None,
) -> None:
    if len(parameters) > 250:
        raise DomainValidationError("Experiment parameters cannot exceed 250 keys.")
    for key in parameters:
        _validate_tracking_key(key, "Parameter")

    for key, value in (metrics or {}).items():
        _validate_tracking_key(key, "Metric")
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise DomainValidationError("Experiment metrics must be numeric.")
        if not math.isfinite(float(value)):
            raise DomainValidationError("Experiment metrics must be finite.")


def validate_artifact(name: str, artifact_type: str, uri: str) -> None:
    if len(name.strip()) < 1 or len(name.strip()) > 120:
        raise DomainValidationError("Artifact name must be between 1 and 120 characters.")
    if len(artifact_type.strip()) < 2 or len(artifact_type.strip()) > 64:
        raise DomainValidationError("Artifact type must be between 2 and 64 characters.")
    stripped_uri = uri.strip()
    if len(stripped_uri) < 3 or len(stripped_uri) > 2048:
        raise DomainValidationError("Artifact URI must be between 3 and 2048 characters.")


def _validate_tracking_key(key: str, label: str) -> None:
    if len(key.strip()) < 1 or len(key.strip()) > 120:
        raise DomainValidationError(f"{label} names must be between 1 and 120 characters.")
