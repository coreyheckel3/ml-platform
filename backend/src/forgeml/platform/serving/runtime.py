from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

SERVING_RUNTIME_SCHEMA_VERSION = "forgeml.serving_runtime.v1"


@dataclass(frozen=True)
class ServingDeploymentRequest:
    deployment_id: UUID
    deployment_revision_id: UUID
    model_version_id: UUID
    serving_image: str
    runtime_config: dict[str, object]
    traffic_percentage: int


@dataclass(frozen=True)
class ServingDeploymentRecord:
    deployment_id: UUID
    deployment_revision_id: UUID
    runtime_deployment_id: str
    status: str
    external_url: str | None
    metadata: dict[str, object]
    observed_at: datetime


@dataclass(frozen=True)
class ServingTrafficAllocation:
    deployment_revision_id: UUID
    traffic_percentage: int


@dataclass(frozen=True)
class ServingTrafficPlanRequest:
    deployment_id: UUID
    allocations: tuple[ServingTrafficAllocation, ...]


@dataclass(frozen=True)
class ServingTrafficPlanResult:
    deployment_id: UUID
    allocations: tuple[ServingTrafficAllocation, ...]
    metadata: dict[str, object]
    observed_at: datetime


@dataclass(frozen=True)
class ServingRollbackRequest:
    deployment_id: UUID
    target_revision_id: UUID
    previous_revision_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class ServingRollbackResult:
    deployment_id: UUID
    target_revision_id: UUID
    previous_revision_ids: tuple[UUID, ...]
    metadata: dict[str, object]
    observed_at: datetime


@dataclass(frozen=True)
class ServingHealthProbeRequest:
    deployment_id: UUID
    deployment_revision_id: UUID
    runtime_deployment_id: str
    runtime_config: dict[str, object]


@dataclass(frozen=True)
class ServingHealthProbeResult:
    deployment_id: UUID
    deployment_revision_id: UUID
    status: str
    latency_ms: float
    error_rate: float
    details: dict[str, object]
    observed_at: datetime


class ServingRuntimeGateway(Protocol):
    def deploy_revision(self, request: ServingDeploymentRequest) -> ServingDeploymentRecord:
        raise NotImplementedError

    def apply_traffic_plan(
        self,
        request: ServingTrafficPlanRequest,
    ) -> ServingTrafficPlanResult:
        raise NotImplementedError

    def rollback(self, request: ServingRollbackRequest) -> ServingRollbackResult:
        raise NotImplementedError

    def probe_revision(self, request: ServingHealthProbeRequest) -> ServingHealthProbeResult:
        raise NotImplementedError


class InMemoryServingRuntimeGateway:
    def __init__(self, *, base_url: str = "memory://serving") -> None:
        self._base_url = base_url.rstrip("/")
        self._records: dict[UUID, ServingDeploymentRecord] = {}
        self.deployment_requests: list[ServingDeploymentRequest] = []
        self.traffic_plan_requests: list[ServingTrafficPlanRequest] = []
        self.rollback_requests: list[ServingRollbackRequest] = []
        self.probe_requests: list[ServingHealthProbeRequest] = []

    def deploy_revision(self, request: ServingDeploymentRequest) -> ServingDeploymentRecord:
        self.deployment_requests.append(request)
        record = ServingDeploymentRecord(
            deployment_id=request.deployment_id,
            deployment_revision_id=request.deployment_revision_id,
            runtime_deployment_id=_runtime_deployment_id(request),
            status="deploying",
            external_url=_serving_revision_url(
                self._base_url,
                request.deployment_id,
                request.deployment_revision_id,
            ),
            metadata={
                "schema_version": SERVING_RUNTIME_SCHEMA_VERSION,
                "serving_image": request.serving_image,
                "traffic_percentage": request.traffic_percentage,
            },
            observed_at=_utcnow(),
        )
        self._records[request.deployment_revision_id] = record
        return record

    def apply_traffic_plan(
        self,
        request: ServingTrafficPlanRequest,
    ) -> ServingTrafficPlanResult:
        self.traffic_plan_requests.append(request)
        for allocation in request.allocations:
            record = self._records.get(allocation.deployment_revision_id)
            if record is not None:
                self._records[allocation.deployment_revision_id] = replace(
                    record,
                    metadata={
                        **record.metadata,
                        "traffic_percentage": allocation.traffic_percentage,
                    },
                    observed_at=_utcnow(),
                )
        return ServingTrafficPlanResult(
            deployment_id=request.deployment_id,
            allocations=request.allocations,
            metadata={
                "schema_version": SERVING_RUNTIME_SCHEMA_VERSION,
                "allocation_count": len(request.allocations),
                "total_traffic_percentage": sum(
                    allocation.traffic_percentage for allocation in request.allocations
                ),
            },
            observed_at=_utcnow(),
        )

    def rollback(self, request: ServingRollbackRequest) -> ServingRollbackResult:
        self.rollback_requests.append(request)
        allocations = [
            ServingTrafficAllocation(request.target_revision_id, 100),
            *[
                ServingTrafficAllocation(previous_revision_id, 0)
                for previous_revision_id in request.previous_revision_ids
            ],
        ]
        self.apply_traffic_plan(
            ServingTrafficPlanRequest(
                deployment_id=request.deployment_id,
                allocations=tuple(allocations),
            )
        )
        return ServingRollbackResult(
            deployment_id=request.deployment_id,
            target_revision_id=request.target_revision_id,
            previous_revision_ids=request.previous_revision_ids,
            metadata={
                "schema_version": SERVING_RUNTIME_SCHEMA_VERSION,
                "drained_revision_count": len(request.previous_revision_ids),
            },
            observed_at=_utcnow(),
        )

    def probe_revision(self, request: ServingHealthProbeRequest) -> ServingHealthProbeResult:
        self.probe_requests.append(request)
        record = self._records.get(request.deployment_revision_id)
        configured_status = request.runtime_config.get("probe_status")
        status = (
            str(configured_status)
            if configured_status in {"healthy", "degraded", "unhealthy"}
            else "healthy"
        )
        if record is None:
            status = "unhealthy"
        latency_ms = _deterministic_latency_ms(request.deployment_revision_id)
        error_rate = _error_rate_for_probe_status(status)
        return ServingHealthProbeResult(
            deployment_id=request.deployment_id,
            deployment_revision_id=request.deployment_revision_id,
            status=status,
            latency_ms=latency_ms,
            error_rate=error_rate,
            details={
                "schema_version": SERVING_RUNTIME_SCHEMA_VERSION,
                "runtime_deployment_id": request.runtime_deployment_id,
                "external_url": record.external_url if record else None,
                "traffic_percentage": (
                    record.metadata.get("traffic_percentage") if record else None
                ),
            },
            observed_at=_utcnow(),
        )


def build_serving_traffic_plan(
    *,
    deployment_id: UUID,
    allocations: Sequence[ServingTrafficAllocation],
) -> ServingTrafficPlanRequest:
    ordered_allocations = tuple(
        sorted(allocations, key=lambda allocation: str(allocation.deployment_revision_id))
    )
    return ServingTrafficPlanRequest(
        deployment_id=deployment_id,
        allocations=ordered_allocations,
    )


def _runtime_deployment_id(request: ServingDeploymentRequest) -> str:
    return f"local-serving://{request.deployment_id}/{request.deployment_revision_id}"


def _serving_revision_url(base_url: str, deployment_id: UUID, revision_id: UUID) -> str:
    return f"{base_url}/deployments/{deployment_id}/revisions/{revision_id}"


def _deterministic_latency_ms(revision_id: UUID) -> float:
    digest = hashlib.sha256(str(revision_id).encode("utf-8")).hexdigest()
    return round(12.0 + (int(digest[:4], 16) % 300) / 10, 3)


def _error_rate_for_probe_status(status: str) -> float:
    if status == "healthy":
        return 0.001
    if status == "degraded":
        return 0.05
    return 1.0


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
