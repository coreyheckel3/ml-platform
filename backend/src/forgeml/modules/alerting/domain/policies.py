import re

from forgeml.modules.alerting.domain.entities import (
    AlertMetric,
    AlertOperator,
    AlertRule,
    AlertSeverity,
    EndpointMetricSnapshotReference,
)
from forgeml.platform.domain.errors import DomainValidationError

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def build_alert_rule_slug(name: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not normalized:
        raise DomainValidationError("Alert rule name must contain a letter or number.")
    return normalized[:80]


def parse_alert_severity(severity: str) -> AlertSeverity:
    try:
        return AlertSeverity(severity.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AlertSeverity)
        raise DomainValidationError(f"Alert severity must be one of: {allowed}.") from exc


def parse_alert_metric(metric: str) -> AlertMetric:
    try:
        return AlertMetric(metric.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AlertMetric)
        raise DomainValidationError(f"Alert metric must be one of: {allowed}.") from exc


def parse_alert_operator(operator: str) -> AlertOperator:
    try:
        return AlertOperator(operator.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AlertOperator)
        raise DomainValidationError(f"Alert operator must be one of: {allowed}.") from exc


def validate_alert_rule_name(name: str) -> None:
    stripped = name.strip()
    if len(stripped) < 3:
        raise DomainValidationError("Alert rule name must be at least 3 characters.")
    if len(stripped) > 120:
        raise DomainValidationError("Alert rule name must be at most 120 characters.")


def validate_alert_rule_threshold(metric: AlertMetric, threshold: float) -> None:
    if threshold < 0:
        raise DomainValidationError("Alert threshold cannot be negative.")
    if metric == AlertMetric.INFERENCE_ERROR_RATE and threshold > 1:
        raise DomainValidationError("Inference error-rate thresholds must be between 0 and 1.")


def validate_alert_rule_window(window_seconds: int) -> None:
    if window_seconds <= 0 or window_seconds > 86_400:
        raise DomainValidationError("Alert rule windows must be between 1 second and 24 hours.")


def observed_metric_value(
    rule: AlertRule,
    snapshot: EndpointMetricSnapshotReference,
) -> float:
    if rule.metric == AlertMetric.INFERENCE_ERROR_RATE:
        return _safe_rate(snapshot.error_count, snapshot.prediction_count)
    if rule.metric == AlertMetric.INFERENCE_P95_LATENCY_MS:
        return snapshot.p95_latency_ms
    return float(snapshot.prediction_count)


def condition_matches(rule: AlertRule, observed_value: float) -> bool:
    if not rule.enabled:
        return False
    if rule.operator == AlertOperator.GREATER_THAN:
        return observed_value > rule.threshold
    if rule.operator == AlertOperator.GREATER_THAN_OR_EQUAL:
        return observed_value >= rule.threshold
    if rule.operator == AlertOperator.LESS_THAN:
        return observed_value < rule.threshold
    return observed_value <= rule.threshold


def build_alert_message(
    rule: AlertRule,
    snapshot: EndpointMetricSnapshotReference,
    observed_value: float,
) -> str:
    return (
        f"{rule.name} triggered for {snapshot.endpoint_name}: "
        f"{rule.metric.value} observed {observed_value:.4g} "
        f"{rule.operator.value} {rule.threshold:.4g}."
    )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
