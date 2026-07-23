from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.alerting.domain.entities import (
    AlertEvent,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertRule,
    AlertSeverity,
)
from forgeml.modules.alerting.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyAlertingRepository,
)
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.deployments.domain.entities import (
    DeploymentEnvironment,
    DeploymentRevisionStatus,
    DeploymentStatus,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentModel,
    DeploymentRevisionModel,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.inference.domain.entities import InferenceEndpointStatus
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base

_SQLALCHEMY_MODEL_DEPENDENCIES = (
    DatasetModel,
    DatasetVersionModel,
    ExperimentModel,
    ExperimentRunModel,
    FeatureSetModel,
    ModelVersionModel,
    RegisteredModelModel,
    TrainingRunModel,
)


def test_alerting_repository_round_trips_rules_events_and_snapshot_reference() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    model_version_id = uuid4()
    endpoint_id = uuid4()

    with Session(engine) as session:
        _seed_project(session, organization_id, project_id, user_id)
        session.add(
            DeploymentModel(
                id=deployment_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk Production",
                slug="fraud-risk-production",
                description="",
                environment=DeploymentEnvironment.PRODUCTION.value,
                status=DeploymentStatus.ACTIVE.value,
                created_by=user_id,
            )
        )
        session.add(
            DeploymentRevisionModel(
                id=revision_id,
                deployment_id=deployment_id,
                model_version_id=model_version_id,
                revision=1,
                serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
                runtime_config_json={"replicas": 3},
                traffic_percentage=100,
                status=DeploymentRevisionStatus.HEALTHY.value,
                orchestrator_deployment_id="local-serving-1",
                created_by=user_id,
            )
        )
        session.add(
            InferenceEndpointModel(
                id=endpoint_id,
                organization_id=organization_id,
                project_id=project_id,
                deployment_id=deployment_id,
                deployment_revision_id=revision_id,
                name="Fraud Risk Online",
                slug="fraud-risk-online",
                route_path="/inference/fraud-risk-online",
                description="",
                status=InferenceEndpointStatus.ACTIVE.value,
                created_by=user_id,
            )
        )
        session.add(
            InferenceMetricSnapshotModel(
                id=uuid4(),
                endpoint_id=endpoint_id,
                window_seconds=300,
                prediction_count=1000,
                error_count=45,
                p50_latency_ms=18.2,
                p95_latency_ms=96.4,
            )
        )
        repository = SqlAlchemyAlertingRepository(session)
        rule = repository.add_rule(
            AlertRule(
                id=uuid4(),
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Error Rate",
                slug="fraud-error-rate",
                description="",
                severity=AlertSeverity.CRITICAL,
                metric=AlertMetric.INFERENCE_ERROR_RATE,
                operator=AlertOperator.GREATER_THAN,
                threshold=0.02,
                window_seconds=300,
                enabled=True,
                created_by=user_id,
            )
        )
        event = repository.add_event(
            AlertEvent(
                id=uuid4(),
                organization_id=organization_id,
                project_id=project_id,
                alert_rule_id=rule.id,
                endpoint_id=endpoint_id,
                severity=AlertSeverity.CRITICAL,
                status=AlertEventStatus.OPEN,
                message="Fraud Error Rate triggered.",
                observed_value=0.045,
                threshold=0.02,
                metadata={"metric": "inference_error_rate"},
                acknowledged_by=None,
                resolved_by=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyAlertingRepository(session)
        rules = repository.list_rules(organization_id, project_id)
        events = repository.list_events(organization_id, project_id)
        open_event = repository.get_open_event(rule.id, endpoint_id)
        snapshot = repository.get_endpoint_snapshot_reference(endpoint_id)
        acknowledged = repository.update_event(
            AlertEvent(
                id=event.id,
                organization_id=organization_id,
                project_id=project_id,
                alert_rule_id=rule.id,
                endpoint_id=endpoint_id,
                severity=AlertSeverity.CRITICAL,
                status=AlertEventStatus.ACKNOWLEDGED,
                message=event.message,
                observed_value=event.observed_value,
                threshold=event.threshold,
                metadata=event.metadata,
                acknowledged_by=user_id,
                resolved_by=None,
            )
        )

    assert rules[0].slug == "fraud-error-rate"
    assert events[0].status == AlertEventStatus.OPEN
    assert open_event is not None
    assert snapshot is not None
    assert snapshot.error_count == 45
    assert acknowledged.status == AlertEventStatus.ACKNOWLEDGED
    assert acknowledged.acknowledged_by == user_id


def _seed_project(session: Session, organization_id, project_id, user_id) -> None:
    session.add(OrganizationModel(id=organization_id, name="ForgeML", slug="forgeml"))
    session.add(
        UserModel(
            id=user_id,
            organization_id=organization_id,
            email="owner@example.com",
            display_name="Owner",
            password_hash="hash",
            permissions_csv="*",
        )
    )
    session.add(
        ProjectModel(
            id=project_id,
            organization_id=organization_id,
            name="Fraud",
            slug="fraud",
            owner_user_id=user_id,
        )
    )
