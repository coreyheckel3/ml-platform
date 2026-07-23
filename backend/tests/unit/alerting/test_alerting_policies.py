import pytest

from forgeml.modules.alerting.domain.entities import (
    AlertMetric,
    AlertOperator,
    AlertRule,
    AlertSeverity,
    EndpointMetricSnapshotReference,
)
from forgeml.modules.alerting.domain.policies import (
    build_alert_rule_slug,
    condition_matches,
    observed_metric_value,
    validate_alert_rule_threshold,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_alerting_policies_evaluate_inference_error_rate() -> None:
    rule = _rule(
        metric=AlertMetric.INFERENCE_ERROR_RATE,
        operator=AlertOperator.GREATER_THAN,
        threshold=0.02,
    )
    snapshot = _snapshot(prediction_count=1000, error_count=35, p95_latency_ms=84.2)

    observed_value = observed_metric_value(rule, snapshot)

    assert build_alert_rule_slug("Fraud Error Rate") == "fraud-error-rate"
    assert observed_value == 0.035
    assert condition_matches(rule, observed_value)


def test_alerting_policies_reject_invalid_error_rate_threshold() -> None:
    with pytest.raises(DomainValidationError):
        validate_alert_rule_threshold(AlertMetric.INFERENCE_ERROR_RATE, 1.2)


def _rule(
    *,
    metric: AlertMetric,
    operator: AlertOperator,
    threshold: float,
) -> AlertRule:
    from uuid import uuid4

    return AlertRule(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        name="Fraud Error Rate",
        slug="fraud-error-rate",
        description="",
        severity=AlertSeverity.WARNING,
        metric=metric,
        operator=operator,
        threshold=threshold,
        window_seconds=300,
        enabled=True,
        created_by=uuid4(),
    )


def _snapshot(
    *,
    prediction_count: int,
    error_count: int,
    p95_latency_ms: float,
) -> EndpointMetricSnapshotReference:
    from uuid import uuid4

    return EndpointMetricSnapshotReference(
        endpoint_id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        endpoint_name="Fraud Risk Online",
        route_path="/inference/fraud-risk-online",
        window_seconds=300,
        prediction_count=prediction_count,
        error_count=error_count,
        p50_latency_ms=18.2,
        p95_latency_ms=p95_latency_ms,
    )
