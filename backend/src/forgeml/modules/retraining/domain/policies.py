import math
import re
from uuid import UUID

from forgeml.modules.retraining.domain.entities import (
    AlertRetrainingSignal,
    DriftRetrainingSignal,
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingTriggerType,
)
from forgeml.platform.domain.errors import DomainValidationError

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")
_METRIC_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:/-]*$")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_ALERT_SEVERITIES = {"info", "warning", "critical"}
_MAX_COOLDOWN_SECONDS = 604_800


def build_retraining_policy_slug(name: str) -> str:
    slug = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise DomainValidationError("Retraining policy name must contain letters or numbers.")
    return slug[:80]


def validate_retraining_policy_name(name: str) -> None:
    _validate_name(name, "Retraining policy name", 3, 120)


def parse_retraining_trigger_type(value: str) -> RetrainingTriggerType:
    try:
        return RetrainingTriggerType(value)
    except ValueError as exc:
        raise DomainValidationError("Retraining trigger type is unsupported.") from exc


def validate_retraining_cooldown_seconds(cooldown_seconds: int) -> None:
    if not isinstance(cooldown_seconds, int) or isinstance(cooldown_seconds, bool):
        raise DomainValidationError("Retraining cooldown must be an integer.")
    if cooldown_seconds < 0 or cooldown_seconds > _MAX_COOLDOWN_SECONDS:
        raise DomainValidationError("Retraining cooldown must be between 0 and 604800 seconds.")


def validate_retraining_max_runs_per_day(max_runs_per_day: int) -> None:
    if not isinstance(max_runs_per_day, int) or isinstance(max_runs_per_day, bool):
        raise DomainValidationError("Retraining max runs per day must be an integer.")
    if max_runs_per_day < 1 or max_runs_per_day > 50:
        raise DomainValidationError("Retraining max runs per day must be between 1 and 50.")


def normalize_trigger_config(
    trigger_type: RetrainingTriggerType,
    trigger_config: dict[str, object],
) -> dict[str, object]:
    if not isinstance(trigger_config, dict):
        raise DomainValidationError("Retraining trigger config must be an object.")
    if len(trigger_config) > 50:
        raise DomainValidationError("Retraining trigger config cannot exceed 50 keys.")
    if trigger_type == RetrainingTriggerType.DRIFT:
        return {
            "min_drift_score": _finite_float(
                trigger_config.get("min_drift_score", 0.2),
                "min_drift_score",
                minimum=0.0,
                maximum=1.0,
            ),
            "min_drifted_features": _non_negative_int(
                trigger_config.get("min_drifted_features", 1),
                "min_drifted_features",
            ),
        }
    if trigger_type == RetrainingTriggerType.ALERT:
        severities = trigger_config.get("severities", ["warning", "critical"])
        if not isinstance(severities, list) or not severities:
            raise DomainValidationError("Alert retraining severities must be a non-empty list.")
        normalized_severities = []
        for severity in severities:
            if not isinstance(severity, str) or severity not in _ALERT_SEVERITIES:
                raise DomainValidationError("Alert retraining severity is unsupported.")
            normalized_severities.append(severity)
        normalized: dict[str, object] = {"severities": normalized_severities}
        if "min_observed_value" in trigger_config:
            normalized["min_observed_value"] = _finite_float(
                trigger_config["min_observed_value"],
                "min_observed_value",
            )
        return normalized
    if trigger_type == RetrainingTriggerType.MANUAL:
        if trigger_config:
            raise DomainValidationError("Manual retraining trigger config must be empty.")
        return {}
    raise DomainValidationError("Retraining trigger type is unsupported.")


def normalize_training_template(training_template: dict[str, object]) -> dict[str, object]:
    if not isinstance(training_template, dict):
        raise DomainValidationError("Retraining training template must be an object.")
    if len(training_template) > 100:
        raise DomainValidationError("Retraining training template cannot exceed 100 keys.")
    experiment_id = _uuid_string(training_template.get("experiment_id"), "experiment_id")
    dataset_version_id = _optional_uuid_string(
        training_template.get("dataset_version_id"),
        "dataset_version_id",
    )
    feature_set_id = _optional_uuid_string(
        training_template.get("feature_set_id"),
        "feature_set_id",
    )
    if dataset_version_id is None and feature_set_id is None:
        raise DomainValidationError(
            "Retraining training template requires a dataset version or feature set."
        )

    run_name_prefix = _str_value(training_template.get("run_name_prefix"), "run_name_prefix")
    algorithm = _str_value(training_template.get("algorithm"), "algorithm")
    model_type = _str_value(training_template.get("model_type"), "model_type")
    objective_metric_name = _str_value(
        training_template.get("objective_metric_name"),
        "objective_metric_name",
    )
    hyperparameters = training_template.get("hyperparameters", {})
    if not isinstance(hyperparameters, dict):
        raise DomainValidationError("Retraining hyperparameters must be an object.")
    if len(hyperparameters) > 250:
        raise DomainValidationError("Retraining hyperparameters cannot exceed 250 keys.")
    for key in hyperparameters:
        _validate_metric_name(str(key), "Hyperparameter name")

    _validate_name(run_name_prefix, "Retraining run name prefix", 3, 96)
    _validate_name(algorithm, "Training algorithm", 2, 120)
    _validate_name(model_type, "Model type", 2, 64)
    _validate_metric_name(objective_metric_name, "Objective metric name")
    return {
        "experiment_id": experiment_id,
        "dataset_version_id": dataset_version_id,
        "feature_set_id": feature_set_id,
        "run_name_prefix": run_name_prefix.strip(),
        "algorithm": algorithm.strip(),
        "model_type": model_type.strip(),
        "objective_metric_name": objective_metric_name.strip(),
        "hyperparameters": {str(key): value for key, value in hyperparameters.items()},
    }


def retraining_policy_accepts_drift(
    policy: RetrainingPolicy,
    signal: DriftRetrainingSignal,
) -> tuple[bool, str]:
    if policy.trigger_type != RetrainingTriggerType.DRIFT:
        return False, "Policy is not configured for drift-triggered retraining."
    min_drift_score = float(policy.trigger_config["min_drift_score"])
    min_drifted_features = int(policy.trigger_config["min_drifted_features"])
    if signal.status != "completed":
        return False, "Drift report is not completed."
    if signal.drift_score < min_drift_score:
        return False, "Drift score is below the retraining threshold."
    if signal.drifted_feature_count < min_drifted_features:
        return False, "Not enough features exceeded drift thresholds."
    return True, "Drift report exceeds retraining policy thresholds."


def retraining_policy_accepts_alert(
    policy: RetrainingPolicy,
    signal: AlertRetrainingSignal,
) -> tuple[bool, str]:
    if policy.trigger_type != RetrainingTriggerType.ALERT:
        return False, "Policy is not configured for alert-triggered retraining."
    severities = {str(severity) for severity in policy.trigger_config["severities"]}
    if signal.status not in {"open", "acknowledged"}:
        return False, "Alert event is no longer active."
    if signal.severity not in severities:
        return False, "Alert severity does not match retraining policy."
    min_observed_value = policy.trigger_config.get("min_observed_value")
    if min_observed_value is not None and signal.observed_value < float(min_observed_value):
        return False, "Alert observed value is below the retraining policy threshold."
    return True, "Alert event matches retraining policy thresholds."


def retraining_policy_is_active(policy: RetrainingPolicy) -> tuple[bool, str]:
    if not policy.enabled:
        return False, "Retraining policy is disabled."
    if policy.status != RetrainingPolicyStatus.ACTIVE:
        return False, "Retraining policy is not active."
    return True, "Retraining policy is active."


def _validate_name(value: str, label: str, minimum: int, maximum: int) -> None:
    stripped = value.strip()
    if len(stripped) < minimum:
        raise DomainValidationError(f"{label} must be at least {minimum} characters.")
    if len(stripped) > maximum:
        raise DomainValidationError(f"{label} must be at most {maximum} characters.")
    if not _NAME_PATTERN.match(stripped):
        raise DomainValidationError(f"{label} contains unsupported characters.")


def _validate_metric_name(value: str, label: str) -> None:
    stripped = value.strip()
    if len(stripped) < 1 or len(stripped) > 120:
        raise DomainValidationError(f"{label} must be between 1 and 120 characters.")
    if not _METRIC_PATTERN.match(stripped):
        raise DomainValidationError(f"{label} contains unsupported characters.")


def _str_value(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise DomainValidationError(f"Retraining training template requires {field_name}.")
    return value


def _uuid_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise DomainValidationError(f"Retraining training template requires {field_name}.")
    try:
        UUID(value)
    except ValueError as exc:
        raise DomainValidationError(
            f"Retraining training template {field_name} is invalid."
        ) from exc
    return value


def _optional_uuid_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DomainValidationError(f"Retraining training template {field_name} is invalid.")
    try:
        UUID(value)
    except ValueError as exc:
        raise DomainValidationError(
            f"Retraining training template {field_name} is invalid."
        ) from exc
    return value


def _finite_float(
    value: object,
    field_name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise DomainValidationError(f"Retraining {field_name} must be numeric.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise DomainValidationError(f"Retraining {field_name} must be finite.")
    if minimum is not None and numeric < minimum:
        raise DomainValidationError(f"Retraining {field_name} is below the allowed range.")
    if maximum is not None and numeric > maximum:
        raise DomainValidationError(f"Retraining {field_name} exceeds the allowed range.")
    return numeric


def _non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(f"Retraining {field_name} must be an integer.")
    if value < 0:
        raise DomainValidationError(f"Retraining {field_name} must be non-negative.")
    return value
