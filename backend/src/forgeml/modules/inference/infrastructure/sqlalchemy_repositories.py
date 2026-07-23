from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentModel,
    DeploymentRevisionModel,
)
from forgeml.modules.inference.domain.entities import (
    DeploymentRevisionServingReference,
    InferenceEndpoint,
    InferenceEndpointStatus,
    InferenceMetricSnapshot,
    InferenceRequestLog,
    InferenceRequestStatus,
)
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
    InferenceRequestLogModel,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelVersionModel,
    RegisteredModelModel,
)


class SqlAlchemyInferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_endpoint(self, endpoint: InferenceEndpoint) -> InferenceEndpoint:
        model = InferenceEndpointModel(
            id=endpoint.id,
            organization_id=endpoint.organization_id,
            project_id=endpoint.project_id,
            deployment_id=endpoint.deployment_id,
            deployment_revision_id=endpoint.deployment_revision_id,
            name=endpoint.name,
            slug=endpoint.slug,
            route_path=endpoint.route_path,
            description=endpoint.description,
            status=endpoint.status.value,
            created_by=endpoint.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _endpoint_to_domain(model)

    def get_endpoint(self, endpoint_id: UUID) -> InferenceEndpoint | None:
        model = self._session.get(InferenceEndpointModel, endpoint_id)
        return _endpoint_to_domain(model) if model else None

    def list_endpoints(self, organization_id: UUID, project_id: UUID) -> list[InferenceEndpoint]:
        models = self._session.scalars(
            select(InferenceEndpointModel)
            .where(
                InferenceEndpointModel.organization_id == organization_id,
                InferenceEndpointModel.project_id == project_id,
            )
            .order_by(InferenceEndpointModel.name)
        ).all()
        return [_endpoint_to_domain(model) for model in models]

    def route_path_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        route_path: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(InferenceEndpointModel.id).where(
                    InferenceEndpointModel.organization_id == organization_id,
                    InferenceEndpointModel.project_id == project_id,
                    InferenceEndpointModel.route_path == route_path,
                )
            )
            is not None
        )

    def get_serving_reference(
        self,
        deployment_revision_id: UUID,
    ) -> DeploymentRevisionServingReference | None:
        row = self._session.execute(
            select(
                DeploymentModel,
                DeploymentRevisionModel,
                ModelVersionModel,
                RegisteredModelModel,
            )
            .join(
                DeploymentRevisionModel,
                DeploymentRevisionModel.deployment_id == DeploymentModel.id,
            )
            .join(
                ModelVersionModel,
                ModelVersionModel.id == DeploymentRevisionModel.model_version_id,
            )
            .join(
                RegisteredModelModel,
                RegisteredModelModel.id == ModelVersionModel.registered_model_id,
            )
            .where(DeploymentRevisionModel.id == deployment_revision_id)
        ).one_or_none()
        if row is None:
            return None
        deployment, revision, model_version, registered_model = row
        return DeploymentRevisionServingReference(
            deployment_id=deployment.id,
            deployment_revision_id=revision.id,
            organization_id=registered_model.organization_id,
            project_id=registered_model.project_id,
            deployment_status=deployment.status,
            revision_status=revision.status,
            traffic_percentage=revision.traffic_percentage,
            model_version_id=model_version.id,
            model_signature=model_version.signature_json,
        )

    def add_request_log(self, request_log: InferenceRequestLog) -> InferenceRequestLog:
        model = InferenceRequestLogModel(
            id=request_log.id,
            endpoint_id=request_log.endpoint_id,
            deployment_revision_id=request_log.deployment_revision_id,
            request_id=request_log.request_id,
            status=request_log.status.value,
            latency_ms=request_log.latency_ms,
            input_payload_json=request_log.input_payload,
            output_payload_json=request_log.output_payload,
            error_message=request_log.error_message,
        )
        self._session.add(model)
        self._session.flush()
        return _request_log_to_domain(model)

    def list_request_logs(self, endpoint_id: UUID) -> list[InferenceRequestLog]:
        models = self._session.scalars(
            select(InferenceRequestLogModel)
            .where(InferenceRequestLogModel.endpoint_id == endpoint_id)
            .order_by(InferenceRequestLogModel.created_at.desc())
        ).all()
        return [_request_log_to_domain(model) for model in models]

    def add_metric_snapshot(
        self,
        snapshot: InferenceMetricSnapshot,
    ) -> InferenceMetricSnapshot:
        model = InferenceMetricSnapshotModel(
            id=snapshot.id,
            endpoint_id=snapshot.endpoint_id,
            window_seconds=snapshot.window_seconds,
            prediction_count=snapshot.prediction_count,
            error_count=snapshot.error_count,
            p50_latency_ms=snapshot.p50_latency_ms,
            p95_latency_ms=snapshot.p95_latency_ms,
        )
        self._session.add(model)
        self._session.flush()
        return _metric_snapshot_to_domain(model)

    def list_metric_snapshots(self, endpoint_id: UUID) -> list[InferenceMetricSnapshot]:
        models = self._session.scalars(
            select(InferenceMetricSnapshotModel)
            .where(InferenceMetricSnapshotModel.endpoint_id == endpoint_id)
            .order_by(InferenceMetricSnapshotModel.created_at.desc())
        ).all()
        return [_metric_snapshot_to_domain(model) for model in models]


def _endpoint_to_domain(model: InferenceEndpointModel) -> InferenceEndpoint:
    return InferenceEndpoint(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        deployment_id=model.deployment_id,
        deployment_revision_id=model.deployment_revision_id,
        name=model.name,
        slug=model.slug,
        route_path=model.route_path,
        description=model.description,
        status=InferenceEndpointStatus(model.status),
        created_by=model.created_by,
    )


def _request_log_to_domain(model: InferenceRequestLogModel) -> InferenceRequestLog:
    return InferenceRequestLog(
        id=model.id,
        endpoint_id=model.endpoint_id,
        deployment_revision_id=model.deployment_revision_id,
        request_id=model.request_id,
        status=InferenceRequestStatus(model.status),
        latency_ms=float(model.latency_ms),
        input_payload=model.input_payload_json,
        output_payload=model.output_payload_json,
        error_message=model.error_message,
    )


def _metric_snapshot_to_domain(model: InferenceMetricSnapshotModel) -> InferenceMetricSnapshot:
    return InferenceMetricSnapshot(
        id=model.id,
        endpoint_id=model.endpoint_id,
        window_seconds=model.window_seconds,
        prediction_count=model.prediction_count,
        error_count=model.error_count,
        p50_latency_ms=float(model.p50_latency_ms),
        p95_latency_ms=float(model.p95_latency_ms),
    )
