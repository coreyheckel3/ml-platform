from dataclasses import dataclass
from uuid import UUID, uuid4

from forgeml.modules.inference.domain.entities import (
    InferenceEndpoint,
    InferenceEndpointStatus,
    InferenceMetricSnapshot,
    InferencePrediction,
    InferenceRequestLog,
    InferenceRequestStatus,
)
from forgeml.modules.inference.domain.policies import (
    build_endpoint_slug,
    build_route_path,
    normalize_route_path,
    validate_endpoint_name,
    validate_endpoint_status,
    validate_metric_snapshot,
    validate_prediction_payload,
    validate_request_log,
    validate_serving_reference,
)
from forgeml.modules.inference.repositories.interfaces import InferenceRepository, InferenceRuntime
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateInferenceEndpointCommand:
    organization_id: UUID
    project_id: UUID
    deployment_id: UUID
    deployment_revision_id: UUID
    name: str
    description: str
    route_path: str | None
    created_by: UUID


@dataclass(frozen=True)
class PredictCommand:
    endpoint_id: UUID
    payload: dict[str, object]
    request_id: str | None = None


@dataclass(frozen=True)
class RecordInferenceMetricSnapshotCommand:
    endpoint_id: UUID
    window_seconds: int
    prediction_count: int
    error_count: int
    p50_latency_ms: float
    p95_latency_ms: float


class InferenceService:
    def __init__(
        self,
        *,
        repository: InferenceRepository,
        runtime: InferenceRuntime,
    ) -> None:
        self._repository = repository
        self._runtime = runtime

    def create_endpoint(
        self,
        command: CreateInferenceEndpointCommand,
        principal: Principal,
    ) -> InferenceEndpoint:
        self._require(principal, "inference_endpoints:create")
        self._require_same_organization(command.organization_id, principal)
        validate_endpoint_name(command.name)
        slug = build_endpoint_slug(command.name)
        route_path = normalize_route_path(command.route_path or build_route_path(command.name))
        if self._repository.route_path_exists(
            command.organization_id,
            command.project_id,
            route_path,
        ):
            raise ConflictError("An inference endpoint already uses this route path.")

        reference = self._repository.get_serving_reference(command.deployment_revision_id)
        if reference is None:
            raise ResourceNotFoundError("Deployment revision was not found.")
        if reference.deployment_id != command.deployment_id:
            raise ResourceNotFoundError("Deployment revision was not found.")
        if reference.organization_id != command.organization_id:
            raise ResourceNotFoundError("Deployment revision was not found.")
        if reference.project_id != command.project_id:
            raise ResourceNotFoundError("Deployment revision was not found.")
        validate_serving_reference(reference)

        endpoint = InferenceEndpoint(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            deployment_id=command.deployment_id,
            deployment_revision_id=command.deployment_revision_id,
            name=command.name.strip(),
            slug=slug,
            route_path=route_path,
            description=command.description.strip(),
            status=InferenceEndpointStatus.ACTIVE,
            created_by=command.created_by,
        )
        return self._repository.add_endpoint(endpoint)

    def list_endpoints(self, project_id: UUID, principal: Principal) -> list[InferenceEndpoint]:
        self._require(principal, "inference_endpoints:read")
        return self._repository.list_endpoints(UUID(principal.organization_id), project_id)

    def get_endpoint(self, endpoint_id: UUID, principal: Principal) -> InferenceEndpoint:
        self._require(principal, "inference_endpoints:read")
        return self._get_scoped_endpoint(endpoint_id, principal)

    def predict(self, command: PredictCommand, principal: Principal) -> InferencePrediction:
        self._require(principal, "inference:predict")
        endpoint = self._get_scoped_endpoint(command.endpoint_id, principal)
        request_id = command.request_id or str(uuid4())
        validate_prediction_payload(command.payload)
        try:
            validate_endpoint_status(endpoint.status)
            reference = self._repository.get_serving_reference(endpoint.deployment_revision_id)
            if reference is None:
                raise ResourceNotFoundError("Deployment revision was not found.")
            validate_serving_reference(reference)
            result = self._runtime.predict(reference, command.payload)
        except Exception as exc:
            self._record_request_log(
                endpoint=endpoint,
                request_id=request_id,
                status=InferenceRequestStatus.REJECTED,
                latency_ms=0.0,
                input_payload=command.payload,
                output_payload={},
                error_message=str(exc),
            )
            raise

        request_log = self._record_request_log(
            endpoint=endpoint,
            request_id=request_id,
            status=InferenceRequestStatus.SUCCEEDED,
            latency_ms=result.latency_ms,
            input_payload=command.payload,
            output_payload=result.output_payload,
            error_message=None,
        )
        return InferencePrediction(
            log_id=request_log.id,
            endpoint_id=endpoint.id,
            deployment_revision_id=endpoint.deployment_revision_id,
            request_id=request_log.request_id,
            status=request_log.status,
            latency_ms=request_log.latency_ms,
            output_payload=request_log.output_payload,
        )

    def list_request_logs(
        self,
        endpoint_id: UUID,
        principal: Principal,
    ) -> list[InferenceRequestLog]:
        self._require(principal, "inference_endpoints:read")
        endpoint = self._get_scoped_endpoint(endpoint_id, principal)
        return self._repository.list_request_logs(endpoint.id)

    def record_metric_snapshot(
        self,
        command: RecordInferenceMetricSnapshotCommand,
        principal: Principal,
    ) -> InferenceMetricSnapshot:
        self._require(principal, "inference_metrics:write")
        endpoint = self._get_scoped_endpoint(command.endpoint_id, principal)
        validate_metric_snapshot(
            window_seconds=command.window_seconds,
            prediction_count=command.prediction_count,
            error_count=command.error_count,
            p50_latency_ms=command.p50_latency_ms,
            p95_latency_ms=command.p95_latency_ms,
        )
        return self._repository.add_metric_snapshot(
            InferenceMetricSnapshot(
                id=uuid4(),
                endpoint_id=endpoint.id,
                window_seconds=command.window_seconds,
                prediction_count=command.prediction_count,
                error_count=command.error_count,
                p50_latency_ms=float(command.p50_latency_ms),
                p95_latency_ms=float(command.p95_latency_ms),
            )
        )

    def list_metric_snapshots(
        self,
        endpoint_id: UUID,
        principal: Principal,
    ) -> list[InferenceMetricSnapshot]:
        self._require(principal, "inference_endpoints:read")
        endpoint = self._get_scoped_endpoint(endpoint_id, principal)
        return self._repository.list_metric_snapshots(endpoint.id)

    def _record_request_log(
        self,
        *,
        endpoint: InferenceEndpoint,
        request_id: str,
        status: InferenceRequestStatus,
        latency_ms: float,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
        error_message: str | None,
    ) -> InferenceRequestLog:
        validate_request_log(status=status, latency_ms=latency_ms, error_message=error_message)
        return self._repository.add_request_log(
            InferenceRequestLog(
                id=uuid4(),
                endpoint_id=endpoint.id,
                deployment_revision_id=endpoint.deployment_revision_id,
                request_id=request_id,
                status=status,
                latency_ms=latency_ms,
                input_payload=input_payload,
                output_payload=output_payload,
                error_message=error_message,
            )
        )

    def _get_scoped_endpoint(
        self,
        endpoint_id: UUID,
        principal: Principal,
    ) -> InferenceEndpoint:
        endpoint = self._repository.get_endpoint(endpoint_id)
        if endpoint is None or str(endpoint.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Inference endpoint was not found.")
        return endpoint

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError("You do not have permission to manage inference.")

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage inference in another organization.")
