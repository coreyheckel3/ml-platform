import re

from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_SUPPORTED_FEATURE_TYPES = {"numeric", "categorical"}


def build_drift_profile_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Drift profile name must contain a letter or number.")
    return normalized[:80]


def validate_drift_profile_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Drift profile name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Drift profile name must be at most 120 characters.")


def validate_baseline_profile(baseline_profile: dict[str, object]) -> None:
    if len(baseline_profile) == 0:
        raise DomainValidationError("Drift baseline profile must include at least one feature.")
    if len(baseline_profile) > 200:
        raise DomainValidationError("Drift baseline profile cannot exceed 200 features.")
    for feature_name, config in baseline_profile.items():
        if not feature_name.strip():
            raise DomainValidationError("Drift baseline feature names cannot be empty.")
        if len(feature_name) > 128:
            raise DomainValidationError(
                "Drift baseline feature names cannot exceed 128 characters."
            )
        if not isinstance(config, dict):
            raise DomainValidationError("Drift baseline feature configs must be objects.")
        feature_type = str(config.get("type", "")).lower()
        if feature_type not in _SUPPORTED_FEATURE_TYPES:
            raise DomainValidationError(
                "Drift baseline feature type must be numeric or categorical."
            )
        threshold = float(config.get("threshold", 0.2))
        validate_drift_threshold(threshold)
        if feature_type == "numeric":
            _validate_numeric_feature_config(feature_name, config)
        else:
            _validate_categorical_feature_config(feature_name, config)


def validate_drift_threshold(threshold: float) -> None:
    if threshold < 0 or threshold > 1:
        raise DomainValidationError("Drift threshold must be between 0 and 1.")


def validate_drift_window(window_seconds: int) -> None:
    if window_seconds <= 0 or window_seconds > 86_400:
        raise DomainValidationError("Drift report windows must be between 1 second and 24 hours.")


def validate_sample_count(sample_count: int) -> None:
    if sample_count <= 0:
        raise DomainValidationError("Drift reports require at least one production sample.")


def _validate_numeric_feature_config(feature_name: str, config: dict[str, object]) -> None:
    if not isinstance(config.get("mean"), int | float):
        raise DomainValidationError(f"Numeric drift baseline for {feature_name} requires mean.")
    if not isinstance(config.get("std"), int | float):
        raise DomainValidationError(f"Numeric drift baseline for {feature_name} requires std.")
    if float(config["std"]) < 0:
        raise DomainValidationError(
            f"Numeric drift baseline std for {feature_name} cannot be negative."
        )


def _validate_categorical_feature_config(feature_name: str, config: dict[str, object]) -> None:
    distribution = config.get("distribution")
    if not isinstance(distribution, dict) or len(distribution) == 0:
        raise DomainValidationError(
            f"Categorical drift baseline for {feature_name} requires distribution."
        )
    for category, weight in distribution.items():
        if not str(category).strip():
            raise DomainValidationError("Categorical drift categories cannot be empty.")
        if not isinstance(weight, int | float) or float(weight) < 0:
            raise DomainValidationError(
                f"Categorical drift distribution for {feature_name} has invalid weights."
            )
