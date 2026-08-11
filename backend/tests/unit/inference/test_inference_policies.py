import pytest

from forgeml.modules.inference.domain.entities import DeploymentRevisionServingReference
from forgeml.modules.inference.domain.policies import (
    build_route_path,
    normalize_route_path,
    select_serving_reference_for_request,
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


def test_select_serving_reference_for_request_uses_weighted_active_revisions() -> None:
    from uuid import uuid4

    deployment_id = uuid4()
    baseline_revision_id = uuid4()
    canary_revision_id = uuid4()
    references = [
        _serving_reference(
            deployment_id=deployment_id,
            revision_id=baseline_revision_id,
            traffic_percentage=0,
        ),
        _serving_reference(
            deployment_id=deployment_id,
            revision_id=canary_revision_id,
            traffic_percentage=100,
        ),
    ]

    selected = select_serving_reference_for_request(
        endpoint_revision_id=baseline_revision_id,
        references=references,
        routing_key="req-001",
    )

    assert selected.deployment_revision_id == canary_revision_id


def _serving_reference(
    *,
    deployment_id,
    revision_id,
    traffic_percentage: int,
) -> DeploymentRevisionServingReference:
    from uuid import uuid4

    return DeploymentRevisionServingReference(
        deployment_id=deployment_id,
        deployment_revision_id=revision_id,
        organization_id=uuid4(),
        project_id=uuid4(),
        deployment_status="active",
        revision_status="healthy",
        traffic_percentage=traffic_percentage,
        model_version_id=uuid4(),
        model_signature={"inputs": ["amount"], "outputs": ["score"]},
    )
