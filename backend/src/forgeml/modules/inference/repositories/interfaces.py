from typing import Protocol
from uuid import UUID

from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceEndpoint,
    InferenceMetricSnapshot,
    InferencePredictionResult,
    InferenceRequestLog,
)


class InferenceRepository(Protocol):
    def add_endpoint(self, endpoint: InferenceEndpoint) -> InferenceEndpoint:
        raise NotImplementedError

    def get_endpoint(self, endpoint_id: UUID) -> InferenceEndpoint | None:
        raise NotImplementedError

    def list_endpoints(self, organization_id: UUID, project_id: UUID) -> list[InferenceEndpoint]:
        raise NotImplementedError

    def route_path_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        route_path: str,
    ) -> bool:
        raise NotImplementedError

    def get_serving_reference(
        self,
        deployment_revision_id: UUID,
    ) -> DeploymentRevisionServingReference | None:
        raise NotImplementedError

    def add_request_log(self, request_log: InferenceRequestLog) -> InferenceRequestLog:
        raise NotImplementedError

    def list_request_logs(self, endpoint_id: UUID) -> list[InferenceRequestLog]:
        raise NotImplementedError

    def add_metric_snapshot(
        self,
        snapshot: InferenceMetricSnapshot,
    ) -> InferenceMetricSnapshot:
        raise NotImplementedError

    def list_metric_snapshots(self, endpoint_id: UUID) -> list[InferenceMetricSnapshot]:
        raise NotImplementedError


class InferenceRuntime(Protocol):
    def predict(
        self,
        reference: DeploymentRevisionServingReference,
        payload: dict[str, object],
    ) -> InferencePredictionResult:
        raise NotImplementedError
