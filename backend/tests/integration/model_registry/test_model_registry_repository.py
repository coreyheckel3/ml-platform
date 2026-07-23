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
    ModelApproval,
    ModelApprovalStatus,
    ModelLineage,
    ModelVersion,
    ModelVersionStatus,
    RegisteredModel,
    RegisteredModelStatus,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyModelRegistryRepository,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.training.domain.entities import TrainingRunStatus
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base


def test_model_registry_repository_round_trips_versions_approvals_and_lineage() -> None:
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
    model_id = uuid4()
    version_id = uuid4()

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
        repository = SqlAlchemyModelRegistryRepository(session)
        model = repository.add_registered_model(
            RegisteredModel(
                id=model_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Risk XGB",
                slug="fraud-risk-xgb",
                description="",
                task_type="classification",
                owner_user_id=user_id,
                status=RegisteredModelStatus.ACTIVE,
            )
        )
        version = repository.add_model_version(
            ModelVersion(
                id=version_id,
                registered_model_id=model.id,
                version=1,
                training_run_id=training_run_id,
                experiment_run_id=experiment_run_id,
                artifact_uri="s3://forgeml/training-runs/run-1",
                model_format="xgboost-booster",
                signature={"inputs": [{"name": "amount"}], "outputs": [{"name": "risk_score"}]},
                metrics={"auc": 0.94},
                status=ModelVersionStatus.CANDIDATE,
                created_by=user_id,
            )
        )
        repository.update_model_version(
            ModelVersion(
                id=version.id,
                registered_model_id=model.id,
                version=1,
                training_run_id=training_run_id,
                experiment_run_id=experiment_run_id,
                artifact_uri=version.artifact_uri,
                model_format=version.model_format,
                signature=version.signature,
                metrics=version.metrics,
                status=ModelVersionStatus.APPROVED,
                created_by=user_id,
            )
        )
        repository.add_approval(
            ModelApproval(
                id=uuid4(),
                model_version_id=version.id,
                status=ModelApprovalStatus.APPROVED,
                requested_by=user_id,
                reviewer_id=user_id,
                comment="Meets launch gate.",
                policy_snapshot={"requires_signature": True},
            )
        )
        repository.add_lineage(
            ModelLineage(
                id=uuid4(),
                model_version_id=version.id,
                source_type="training_run",
                source_id=str(training_run_id),
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyModelRegistryRepository(session)

        models = repository.list_registered_models(organization_id, project_id)
        versions = repository.list_model_versions(model_id)
        reference = repository.get_training_run_reference(training_run_id)
        approvals = repository.list_approvals(version_id)
        lineage = repository.list_lineage(version_id)

    assert models[0].slug == "fraud-risk-xgb"
    assert versions[0].status == ModelVersionStatus.APPROVED
    assert versions[0].metrics["auc"] == 0.94
    assert reference is not None
    assert reference.status == "succeeded"
    assert approvals[0].status == ModelApprovalStatus.APPROVED
    assert lineage[0].source_type == "training_run"
