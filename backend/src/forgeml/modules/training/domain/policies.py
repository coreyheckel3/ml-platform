import math
import re

from forgeml.modules.training.domain.entities import TrainingRunStatus
from forgeml.platform.domain.errors import DomainValidationError

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")
_METRIC_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:/-]*$")
_LOG_LEVELS = {"debug", "info", "warning", "error"}
_ALLOWED_TERMINAL_STATUSES = {
    TrainingRunStatus.SUCCEEDED,
    TrainingRunStatus.FAILED,
    TrainingRunStatus.CANCELED,
}


def validate_training_run_request(
    *,
    algorithm: str,
    model_type: str,
    objective_metric_name: str,
    hyperparameters: dict[str, object],
    dataset_version_id: object | None,
    feature_set_id: object | None,
) -> None:
    _validate_name(algorithm, "Training algorithm", 2, 120)
    _validate_name(model_type, "Model type", 2, 64)
    validate_metric_name(objective_metric_name)
    if len(hyperparameters) > 250:
        raise DomainValidationError("Training hyperparameters cannot exceed 250 keys.")
    for key in hyperparameters:
        if len(key.strip()) < 1 or len(key.strip()) > 120:
            raise DomainValidationError(
                "Hyperparameter names must be between 1 and 120 characters."
            )
    if dataset_version_id is None and feature_set_id is None:
        raise DomainValidationError("Training requires a dataset version or feature set.")


def validate_run_name(run_name: str) -> None:
    _validate_name(run_name, "Training run name", 3, 160)


def validate_metric_name(metric_name: str) -> None:
    stripped = metric_name.strip()
    if len(stripped) < 1 or len(stripped) > 120:
        raise DomainValidationError("Metric name must be between 1 and 120 characters.")
    if not _METRIC_PATTERN.match(stripped):
        raise DomainValidationError("Metric name contains unsupported characters.")


def validate_metrics(metrics: dict[str, float]) -> None:
    if len(metrics) > 500:
        raise DomainValidationError("Training metrics cannot exceed 500 keys.")
    for key, value in metrics.items():
        validate_metric_name(key)
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise DomainValidationError("Training metrics must be numeric.")
        if not math.isfinite(float(value)):
            raise DomainValidationError("Training metrics must be finite.")


def validate_terminal_status(status: TrainingRunStatus) -> None:
    if status not in _ALLOWED_TERMINAL_STATUSES:
        raise DomainValidationError("Training result must use a terminal status.")


def validate_training_log(
    *,
    sequence: int,
    level: str,
    logger: str,
    message: str,
    metadata: dict[str, object],
) -> None:
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise DomainValidationError("Training log sequence must be a positive integer.")
    if level not in _LOG_LEVELS:
        raise DomainValidationError("Training log level is unsupported.")
    _validate_name(logger, "Training log logger", 1, 120)
    stripped_message = message.strip()
    if len(stripped_message) < 1:
        raise DomainValidationError("Training log message is required.")
    if len(stripped_message) > 4000:
        raise DomainValidationError("Training log message must be at most 4000 characters.")
    if not isinstance(metadata, dict):
        raise DomainValidationError("Training log metadata must be an object.")
    if len(metadata) > 100:
        raise DomainValidationError("Training log metadata cannot exceed 100 keys.")


def _validate_name(value: str, label: str, minimum: int, maximum: int) -> None:
    stripped = value.strip()
    if len(stripped) < minimum:
        raise DomainValidationError(f"{label} must be at least {minimum} characters.")
    if len(stripped) > maximum:
        raise DomainValidationError(f"{label} must be at most {maximum} characters.")
    if not _NAME_PATTERN.match(stripped):
        raise DomainValidationError(f"{label} contains unsupported characters.")
