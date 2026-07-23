from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.domain.entities import (
    DatasetSourceType,
    DatasetStatus,
    DatasetVersionStatus,
)
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.deployments.domain.entities import (
    Deployment,
    DeploymentEnvironment,
    DeploymentEvent,
    DeploymentHealthCheck,
    DeploymentHealthStatus,
    DeploymentRevision,
    DeploymentRevisionStatus,
    DeploymentStatus,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDeploymentRepository,
)
from forgeml.modules.experiments.domain.entities import (
    ExperimentRunStatus,
    ExperimentStatus,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.domain.entities import FeatureSetStatus
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.model_registry.domain.entities import (
    ModelVersionStatus,
    RegisteredModelStatus,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.training.domain.entities import TrainingRunStatus
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base


def test_deployment_repository_round_trips_revisions_health_events_and_model_reference() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    dataset_version_id = uuid4()
    feature_set_id = uuid4()
    experiment_id = uuid4()
    experiment_run_id = uuid4()
    training_run_id = uuid4()
    registered_model_id = uuid4()
    model_version_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()

    with Session(engine) as session:
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
        session.add(
            DatasetModel(
                id=dataset_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Transactions",
                slug="transactions",
                description="",
                source_type=DatasetSourceType.UPLOAD.value,
                status=DatasetStatus.ACTIVE.value,
            )
        )
        session.add(
            DatasetVersionModel(
                id=dataset_version_id,
                dataset_id=dataset_id,
                version=1,
                object_uri="s3://forgeml/transactions.csv",
                content_hash="sha256:abc",
                row_count=10,
                size_bytes=128,
                status=DatasetVersionStatus.VALIDATED.value,
                created_by=user_id,
            )
        )
        session.add(
            FeatureSetModel(
                id=feature_set_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Merchant Signals",
                slug="merchant-signals",
                description="",
                entity_key="merchant_id",
                status=FeatureSetStatus.ACTIVE.value,
            )
        )
        session.add(
            ExperimentModel(
                id=experiment_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk Baseline",
                slug="fraud-risk-baseline",
                description="",
                owner_user_id=user_id,
                status=ExperimentStatus.ACTIVE.value,
            )
        )
        session.add(
            ExperimentRunModel(
                id=experiment_run_id,
                experiment_id=experiment_id,
                project_id=project_id,
                run_name="xgb-depth-6",
                status=ExperimentRunStatus.SUCCEEDED.value,
                model_type="xgboost",
                started_by=user_id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                parameters_json={"max_depth": 6},
                metrics_json={"auc": 0.94},
                artifact_uri="s3://forgeml/training-runs/run-1",
                evaluation_report_json={},
                error_message=None,
            )
        )
        session.add(
            TrainingRunModel(
                id=training_run_id,
                organization_id=organization_id,
                project_id=project_id,
                experiment_id=experiment_id,
                experiment_run_id=experiment_run_id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                algorithm="xgboost",
                model_type="xgboost",
                objective_metric_name="auc",
                hyperparameters_json={"max_depth": 6},
                status=TrainingRunStatus.SUCCEEDED.value,
                requested_by=user_id,
                artifact_uri="s3://forgeml/training-runs/run-1",
                orchestrator_run_id="workflow-1",
                metrics_json={"auc": 0.94},
                error_message=None,
            )
        )
        session.add(
            RegisteredModelModel(
                id=registered_model_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk XGB",
                slug="fraud-risk-xgb",
                description="",
                task_type="classification",
                owner_user_id=user_id,
                status=RegisteredModelStatus.ACTIVE.value,
            )
        )
        session.add(
            ModelVersionModel(
                id=model_version_id,
                registered_model_id=registered_model_id,
                version=1,
                training_run_id=training_run_id,
                experiment_run_id=experiment_run_id,
                artifact_uri="s3://forgeml/training-runs/run-1",
                model_format="xgboost-booster",
                signature_json={"inputs": [], "outputs": []},
                metrics_json={"auc": 0.94},
                status=ModelVersionStatus.APPROVED.value,
                created_by=user_id,
            )
        )
        repository = SqlAlchemyDeploymentRepository(session)
        deployment = repository.add_deployment(
            Deployment(
                id=deployment_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk Production",
                slug="fraud-risk-production",
                description="",
                environment=DeploymentEnvironment.PRODUCTION,
                status=DeploymentStatus.ACTIVE,
                created_by=user_id,
            )
        )
        revision = repository.add_revision(
            DeploymentRevision(
                id=revision_id,
                deployment_id=deployment.id,
                model_version_id=model_version_id,
                revision=1,
                serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
                runtime_config={"replicas": 3},
                traffic_percentage=10,
                status=DeploymentRevisionStatus.DEPLOYING,
                orchestrator_deployment_id="local-serving-1",
                created_by=user_id,
            )
        )
        repository.update_revision(
            DeploymentRevision(
                id=revision.id,
                deployment_id=deployment.id,
                model_version_id=model_version_id,
                revision=1,
                serving_image=revision.serving_image,
                runtime_config=revision.runtime_config,
                traffic_percentage=100,
                status=DeploymentRevisionStatus.HEALTHY,
                orchestrator_deployment_id=revision.orchestrator_deployment_id,
                created_by=user_id,
            )
        )
        repository.add_health_check(
            DeploymentHealthCheck(
                id=uuid4(),
                deployment_revision_id=revision.id,
                status=DeploymentHealthStatus.HEALTHY,
                latency_ms=18.2,
                error_rate=0.001,
                details={"window": "5m"},
            )
        )
        repository.add_event(
            DeploymentEvent(
                id=uuid4(),
                deployment_id=deployment.id,
                deployment_revision_id=revision.id,
                event_type="revision_created",
                message="Deployment revision was created.",
                metadata={"traffic_percentage": 10},
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyDeploymentRepository(session)

        deployments = repository.list_deployments(organization_id, project_id)
        revisions = repository.list_revisions(deployment_id)
        health_checks = repository.list_health_checks(revision_id)
        events = repository.list_events(deployment_id)
        model_reference = repository.get_model_version_reference(model_version_id)
        active_revision = repository.get_active_revision(deployment_id)

    assert deployments[0].slug == "fraud-risk-production"
    assert revisions[0].status == DeploymentRevisionStatus.HEALTHY
    assert health_checks[0].status == DeploymentHealthStatus.HEALTHY
    assert events[0].event_type == "revision_created"
    assert model_reference is not None
    assert model_reference.status == "approved"
    assert active_revision is not None
    assert active_revision.traffic_percentage == 100
