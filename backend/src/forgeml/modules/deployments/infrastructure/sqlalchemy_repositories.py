from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEnvironment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
    DeploymentRevisionStatus,
    DeploymentStatus,
    ModelVersionDeploymentReference,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentEventModel,
    DeploymentHealthCheckModel,
    DeploymentModel,
    DeploymentRevisionModel,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelVersionModel,
    RegisteredModelModel,
)


class SqlAlchemyDeploymentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_deployment(self, deployment: Deployment) -> Deployment:
        model = DeploymentModel(
            id=deployment.id,
            organization_id=deployment.organization_id,
            project_id=deployment.project_id,
            name=deployment.name,
            slug=deployment.slug,
            description=deployment.description,
            environment=deployment.environment.value,
            status=deployment.status.value,
            created_by=deployment.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _deployment_to_domain(model)

    def get_deployment(self, deployment_id: UUID) -> Deployment | None:
        model = self._session.get(DeploymentModel, deployment_id)
        return _deployment_to_domain(model) if model else None

    def list_deployments(self, organization_id: UUID, project_id: UUID) -> list[Deployment]:
        models = self._session.scalars(
            select(DeploymentModel)
            .where(
                DeploymentModel.organization_id == organization_id,
                DeploymentModel.project_id == project_id,
            )
            .order_by(DeploymentModel.name)
        ).all()
        return [_deployment_to_domain(model) for model in models]

    def deployment_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        return (
            self._session.scalar(
                select(DeploymentModel.id).where(
                    DeploymentModel.organization_id == organization_id,
                    DeploymentModel.project_id == project_id,
                    DeploymentModel.slug == slug,
                )
            )
            is not None
        )

    def get_model_version_reference(
        self,
        model_version_id: UUID,
    ) -> ModelVersionDeploymentReference | None:
        row = self._session.execute(
            select(ModelVersionModel, RegisteredModelModel)
            .join(
                RegisteredModelModel,
                RegisteredModelModel.id == ModelVersionModel.registered_model_id,
            )
            .where(ModelVersionModel.id == model_version_id)
        ).one_or_none()
        if row is None:
            return None
        version, registered_model = row
        return ModelVersionDeploymentReference(
            id=version.id,
            registered_model_id=version.registered_model_id,
            organization_id=registered_model.organization_id,
            project_id=registered_model.project_id,
            version=version.version,
            status=version.status,
            artifact_uri=version.artifact_uri,
            model_format=version.model_format,
        )

    def latest_revision_number(self, deployment_id: UUID) -> int:
        revisions = self._session.scalars(
            select(DeploymentRevisionModel.revision).where(
                DeploymentRevisionModel.deployment_id == deployment_id
            )
        ).all()
        return max(revisions, default=0)

    def add_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        model = DeploymentRevisionModel(
            id=revision.id,
            deployment_id=revision.deployment_id,
            model_version_id=revision.model_version_id,
            revision=revision.revision,
            serving_image=revision.serving_image,
            runtime_config_json=revision.runtime_config,
            traffic_percentage=revision.traffic_percentage,
            status=revision.status.value,
            orchestrator_deployment_id=revision.orchestrator_deployment_id,
            created_by=revision.created_by,
        )
        self._session.add(model)
        self._session.flush()
        return _revision_to_domain(model)

    def get_revision(self, revision_id: UUID) -> DeploymentRevision | None:
        model = self._session.get(DeploymentRevisionModel, revision_id)
        return _revision_to_domain(model) if model else None

    def list_revisions(self, deployment_id: UUID) -> list[DeploymentRevision]:
        models = self._session.scalars(
            select(DeploymentRevisionModel)
            .where(DeploymentRevisionModel.deployment_id == deployment_id)
            .order_by(DeploymentRevisionModel.revision.desc())
        ).all()
        return [_revision_to_domain(model) for model in models]

    def get_active_revision(self, deployment_id: UUID) -> DeploymentRevision | None:
        model = self._session.scalars(
            select(DeploymentRevisionModel)
            .where(
                DeploymentRevisionModel.deployment_id == deployment_id,
                DeploymentRevisionModel.traffic_percentage > 0,
            )
            .order_by(DeploymentRevisionModel.revision.desc())
        ).first()
        return _revision_to_domain(model) if model else None

    def update_revision(self, revision: DeploymentRevision) -> DeploymentRevision:
        model = self._session.get(DeploymentRevisionModel, revision.id)
        if model is None:
            raise ValueError("Deployment revision does not exist.")
        model.traffic_percentage = revision.traffic_percentage
        model.status = revision.status.value
        model.runtime_config_json = revision.runtime_config
        model.orchestrator_deployment_id = revision.orchestrator_deployment_id
        self._session.flush()
        return _revision_to_domain(model)

    def add_health_check(self, health_check: DeploymentHealthCheck) -> DeploymentHealthCheck:
        model = DeploymentHealthCheckModel(
            id=health_check.id,
            deployment_revision_id=health_check.deployment_revision_id,
            status=health_check.status.value,
            latency_ms=health_check.latency_ms,
            error_rate=health_check.error_rate,
            details_json=health_check.details,
        )
        self._session.add(model)
        self._session.flush()
        return _health_check_to_domain(model)

    def list_health_checks(self, revision_id: UUID) -> list[DeploymentHealthCheck]:
        models = self._session.scalars(
            select(DeploymentHealthCheckModel)
            .where(DeploymentHealthCheckModel.deployment_revision_id == revision_id)
            .order_by(DeploymentHealthCheckModel.created_at.desc())
        ).all()
        return [_health_check_to_domain(model) for model in models]

    def add_event(self, event: DeploymentEvent) -> DeploymentEvent:
        model = DeploymentEventModel(
            id=event.id,
            deployment_id=event.deployment_id,
            deployment_revision_id=event.deployment_revision_id,
            event_type=event.event_type,
            message=event.message,
            metadata_json=event.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _event_to_domain(model)

    def list_events(self, deployment_id: UUID) -> list[DeploymentEvent]:
        models = self._session.scalars(
            select(DeploymentEventModel)
            .where(DeploymentEventModel.deployment_id == deployment_id)
            .order_by(DeploymentEventModel.created_at.desc())
        ).all()
        return [_event_to_domain(model) for model in models]


def _deployment_to_domain(model: DeploymentModel) -> Deployment:
    return Deployment(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        environment=DeploymentEnvironment(model.environment),
        status=DeploymentStatus(model.status),
        created_by=model.created_by,
    )


def _revision_to_domain(model: DeploymentRevisionModel) -> DeploymentRevision:
    return DeploymentRevision(
        id=model.id,
        deployment_id=model.deployment_id,
        model_version_id=model.model_version_id,
        revision=model.revision,
        serving_image=model.serving_image,
        runtime_config=model.runtime_config_json,
        traffic_percentage=model.traffic_percentage,
        status=DeploymentRevisionStatus(model.status),
        orchestrator_deployment_id=model.orchestrator_deployment_id,
        created_by=model.created_by,
    )


def _health_check_to_domain(model: DeploymentHealthCheckModel) -> DeploymentHealthCheck:
    return DeploymentHealthCheck(
        id=model.id,
        deployment_revision_id=model.deployment_revision_id,
        status=DeploymentHealthStatus(model.status),
        latency_ms=float(model.latency_ms),
        error_rate=float(model.error_rate),
        details=model.details_json,
    )


def _event_to_domain(model: DeploymentEventModel) -> DeploymentEvent:
    return DeploymentEvent(
        id=model.id,
        deployment_id=model.deployment_id,
        deployment_revision_id=model.deployment_revision_id,
        event_type=model.event_type,
        message=model.message,
        metadata=model.metadata_json,
    )
