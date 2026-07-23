from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.alerting.domain.entities import AlertEventStatus
from forgeml.modules.alerting.infrastructure.sqlalchemy_models import (
    AlertEventModel,
    AlertRuleModel,
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
from forgeml.modules.inference.domain.entities import (
    InferenceEndpointStatus,
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
from forgeml.modules.monitoring.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyMonitoringRepository,
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


def test_monitoring_repository_summarizes_inference_metrics_and_alerts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    model_version_id = uuid4()
    endpoint_id = uuid4()
    rule_id = uuid4()

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
                prediction_count=1200,
                error_count=24,
                p50_latency_ms=18.2,
                p95_latency_ms=84.8,
            )
        )
        for index in range(3):
            session.add(
                InferenceRequestLogModel(
                    id=uuid4(),
                    endpoint_id=endpoint_id,
                    deployment_revision_id=revision_id,
                    request_id=f"req-{index}",
                    status=InferenceRequestStatus.SUCCEEDED.value,
                    latency_ms=18.0 + index,
                    input_payload_json={"amount": 128.45},
                    output_payload_json={"score": 0.81},
                    error_message=None,
                )
            )
        session.add(
            AlertRuleModel(
                id=rule_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Error Rate",
                slug="fraud-error-rate",
                description="",
                severity="warning",
                metric="inference_error_rate",
                operator="gt",
                threshold=0.01,
                window_seconds=300,
                enabled=True,
                created_by=user_id,
            )
        )
        session.add(
            AlertEventModel(
                id=uuid4(),
                organization_id=organization_id,
                project_id=project_id,
                alert_rule_id=rule_id,
                endpoint_id=endpoint_id,
                severity="warning",
                status=AlertEventStatus.OPEN.value,
                message="Fraud Error Rate triggered.",
                observed_value=0.02,
                threshold=0.01,
                metadata_json={"metric": "inference_error_rate"},
                acknowledged_by=None,
                resolved_by=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMonitoringRepository(session)
        summaries = repository.list_inference_endpoint_summaries(organization_id, project_id)
        active_alert_count = repository.count_active_alerts(organization_id, project_id)

    assert summaries[0].endpoint_name == "Fraud Risk Online"
    assert summaries[0].prediction_count == 1200
    assert summaries[0].request_count == 3
    assert summaries[0].error_rate == 0.02
    assert summaries[0].p95_latency_ms == 84.8
    assert active_alert_count == 1


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
