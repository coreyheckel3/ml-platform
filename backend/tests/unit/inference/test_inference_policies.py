import pytest

from forgeml.modules.inference.domain.policies import (
    build_route_path,
    normalize_route_path,
    validate_metric_snapshot,
    validate_prediction_payload,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_inference_policies_build_routes_and_validate_payloads() -> None:
    assert build_route_path("Fraud Risk Production") == "/inference/fraud-risk-production"
    assert normalize_route_path("Inference/Fraud_Risk") == "/inference/fraud_risk"
    validate_prediction_payload({"amount": 128.45, "merchant_category": "travel"})


def test_inference_policies_reject_invalid_metric_snapshot() -> None:
    with pytest.raises(DomainValidationError):
        validate_metric_snapshot(
            window_seconds=300,
            prediction_count=10,
            error_count=11,
            p50_latency_ms=28.1,
            p95_latency_ms=52.4,
        )

    with pytest.raises(DomainValidationError):
        validate_metric_snapshot(
            window_seconds=300,
            prediction_count=10,
            error_count=1,
            p50_latency_ms=92.1,
            p95_latency_ms=52.4,
        )


def test_inference_policies_reject_oversized_payload() -> None:
    with pytest.raises(DomainValidationError):
        validate_prediction_payload({f"feature_{index}": index for index in range(201)})
