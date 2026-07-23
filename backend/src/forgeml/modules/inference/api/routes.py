from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.inference.api.schemas import (
    CreateInferenceEndpointRequest,
    InferenceEndpointListResponse,
    InferenceEndpointResponse,
    InferenceMetricSnapshotListResponse,
    InferenceMetricSnapshotResponse,
    InferenceRequestLogListResponse,
    InferenceRequestLogResponse,
    PredictRequest,
    PredictResponse,
    RecordInferenceMetricSnapshotRequest,
)
from forgeml.modules.inference.application.services import (
    CreateInferenceEndpointCommand,
    InferenceService,
    PredictCommand,
    RecordInferenceMetricSnapshotCommand,
)
from forgeml.modules.inference.domain.entities import (
    InferenceEndpoint,
    InferenceMetricSnapshot,
    InferencePrediction,
    InferenceRequestLog,
)
from forgeml.modules.inference.infrastructure.runtime import LocalInferenceRuntime
from forgeml.modules.inference.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyInferenceRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["inference"])


def get_inference_service(
    session: Session = Depends(get_db_session),
) -> InferenceService:
    return InferenceService(
        repository=SqlAlchemyInferenceRepository(session),
        runtime=LocalInferenceRuntime(),
    )


@router.post(
    "/projects/{project_id}/inference-endpoints",
    response_model=InferenceEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inference_endpoint(
    project_id: UUID,
    request: CreateInferenceEndpointRequest,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceEndpointResponse:
    endpoint = service.create_endpoint(
        CreateInferenceEndpointCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            deployment_id=UUID(request.deployment_id),
            deployment_revision_id=UUID(request.deployment_revision_id),
            name=request.name,
            description=request.description,
            route_path=request.route_path,
            created_by=UUID(principal.user_id),
        ),
        principal,
    )
    return _endpoint_response(endpoint)


@router.get(
    "/projects/{project_id}/inference-endpoints",
    response_model=InferenceEndpointListResponse,
)
def list_inference_endpoints(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceEndpointListResponse:
    return InferenceEndpointListResponse(
        items=[
            _endpoint_response(endpoint)
            for endpoint in service.list_endpoints(project_id, principal)
        ]
    )


@router.get(
    "/inference-endpoints/{endpoint_id}",
    response_model=InferenceEndpointResponse,
)
def get_inference_endpoint(
    endpoint_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceEndpointResponse:
    return _endpoint_response(service.get_endpoint(endpoint_id, principal))


@router.post(
    "/inference-endpoints/{endpoint_id}/predict",
    response_model=PredictResponse,
)
def predict(
    endpoint_id: UUID,
    request: PredictRequest,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> PredictResponse:
    prediction = service.predict(
        PredictCommand(
            endpoint_id=endpoint_id,
            payload=request.payload,
            request_id=request.request_id,
        ),
        principal,
    )
    return _prediction_response(prediction)


@router.get(
    "/inference-endpoints/{endpoint_id}/requests",
    response_model=InferenceRequestLogListResponse,
)
def list_inference_requests(
    endpoint_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceRequestLogListResponse:
    return InferenceRequestLogListResponse(
        items=[
            _request_log_response(request_log)
            for request_log in service.list_request_logs(endpoint_id, principal)
        ]
    )


@router.post(
    "/inference-endpoints/{endpoint_id}/metric-snapshots",
    response_model=InferenceMetricSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_inference_metric_snapshot(
    endpoint_id: UUID,
    request: RecordInferenceMetricSnapshotRequest,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceMetricSnapshotResponse:
    snapshot = service.record_metric_snapshot(
        RecordInferenceMetricSnapshotCommand(
            endpoint_id=endpoint_id,
            window_seconds=request.window_seconds,
            prediction_count=request.prediction_count,
            error_count=request.error_count,
            p50_latency_ms=request.p50_latency_ms,
            p95_latency_ms=request.p95_latency_ms,
        ),
        principal,
    )
    return _metric_snapshot_response(snapshot)


@router.get(
    "/inference-endpoints/{endpoint_id}/metric-snapshots",
    response_model=InferenceMetricSnapshotListResponse,
)
def list_inference_metric_snapshots(
    endpoint_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: InferenceService = Depends(get_inference_service),
) -> InferenceMetricSnapshotListResponse:
    return InferenceMetricSnapshotListResponse(
        items=[
            _metric_snapshot_response(snapshot)
            for snapshot in service.list_metric_snapshots(endpoint_id, principal)
        ]
    )


def _endpoint_response(endpoint: InferenceEndpoint) -> InferenceEndpointResponse:
    return InferenceEndpointResponse(
        id=str(endpoint.id),
        organization_id=str(endpoint.organization_id),
        project_id=str(endpoint.project_id),
        deployment_id=str(endpoint.deployment_id),
        deployment_revision_id=str(endpoint.deployment_revision_id),
        name=endpoint.name,
        slug=endpoint.slug,
        route_path=endpoint.route_path,
        description=endpoint.description,
        status=endpoint.status.value,
        created_by=str(endpoint.created_by),
    )


def _prediction_response(prediction: InferencePrediction) -> PredictResponse:
    return PredictResponse(
        log_id=str(prediction.log_id),
        endpoint_id=str(prediction.endpoint_id),
        deployment_revision_id=str(prediction.deployment_revision_id),
        request_id=prediction.request_id,
        status=prediction.status.value,
        latency_ms=prediction.latency_ms,
        output_payload=prediction.output_payload,
    )


def _request_log_response(request_log: InferenceRequestLog) -> InferenceRequestLogResponse:
    return InferenceRequestLogResponse(
        id=str(request_log.id),
        endpoint_id=str(request_log.endpoint_id),
        deployment_revision_id=str(request_log.deployment_revision_id),
        request_id=request_log.request_id,
        status=request_log.status.value,
        latency_ms=request_log.latency_ms,
        input_payload=request_log.input_payload,
        output_payload=request_log.output_payload,
        error_message=request_log.error_message,
    )


def _metric_snapshot_response(
    snapshot: InferenceMetricSnapshot,
) -> InferenceMetricSnapshotResponse:
    return InferenceMetricSnapshotResponse(
        id=str(snapshot.id),
        endpoint_id=str(snapshot.endpoint_id),
        window_seconds=snapshot.window_seconds,
        prediction_count=snapshot.prediction_count,
        error_count=snapshot.error_count,
        p50_latency_ms=snapshot.p50_latency_ms,
        p95_latency_ms=snapshot.p95_latency_ms,
    )
