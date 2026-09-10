from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetVersionModel,
)
from forgeml.modules.evaluation.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyEvaluationComparisonRepository,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelApprovalModel,
    ModelLineageModel,
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base


def test_evaluation_repository_loads_rankable_cross_module_snapshot() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    with Session(engine) as session:
        seeded = _seed_evaluation_context(session, organization_id, project_id, user_id)
        _seed_evaluation_context(session, uuid4(), uuid4(), uuid4(), project_name="Other Org")
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyEvaluationComparisonRepository(session)
        snapshot = repository.load_snapshot(organization_id, project_id)

    assert snapshot is not None
    assert snapshot.project_id == project_id
    assert snapshot.project_name == "Fraud Detection"
    assert len(snapshot.candidates) == 2
    candidates_by_run = {candidate.run_name: candidate for candidate in snapshot.candidates}
    assert candidates_by_run["xgb-depth-8"].metrics["auc"] == 0.96
    assert candidates_by_run["xgb-depth-8"].model_version == 2
    assert candidates_by_run["xgb-depth-8"].approval_status == "approved"
    assert candidates_by_run["xgb-depth-4"].model_version is None
    assert len(snapshot.model_evidence) == 1
    assert snapshot.model_evidence[0].model_version_id == seeded["model_version_id"]
    assert snapshot.model_evidence[0].lineage_sources == (
        f"dataset_version:{seeded['dataset_version_id']}",
        f"feature_set:{seeded['feature_set_id']}",
    )


def test_evaluation_repository_returns_none_for_cross_organization_project() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()

    with Session(engine) as session:
        _seed_evaluation_context(session, organization_id, project_id, uuid4())
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyEvaluationComparisonRepository(session)
        snapshot = repository.load_snapshot(uuid4(), project_id)

    assert snapshot is None


def _seed_evaluation_context(
    session: Session,
    organization_id,
    project_id,
    user_id,
    *,
    project_name: str = "Fraud Detection",
) -> dict[str, object]:
    experiment_id = uuid4()
    baseline_run_id = uuid4()
    champion_run_id = uuid4()
    baseline_training_id = uuid4()
    champion_training_id = uuid4()
    dataset_id = uuid4()
    dataset_version_id = uuid4()
    feature_set_id = uuid4()
    registered_model_id = uuid4()
    model_version_id = uuid4()
    slug = project_name.lower().replace(" ", "-")

    session.add(OrganizationModel(id=organization_id, name=project_name, slug=slug))
    session.add(
        UserModel(
            id=user_id,
            organization_id=organization_id,
            email=f"{slug}@example.com",
            display_name="Owner",
            password_hash="hash",
            permissions_csv="*",
        )
    )
    session.add(
        ProjectModel(
            id=project_id,
            organization_id=organization_id,
            name=project_name,
            slug=slug,
            owner_user_id=user_id,
        )
    )
    session.add(
        DatasetModel(
            id=dataset_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Features",
            slug=f"{slug}-features",
            description="",
            source_type="upload",
            status="active",
        )
    )
    session.add(
        DatasetVersionModel(
            id=dataset_version_id,
            dataset_id=dataset_id,
            version=1,
            object_uri="s3://forgeml/datasets/fraud/v1/features.csv",
            content_hash="sha256:dataset",
            row_count=1000,
            size_bytes=2048,
            status="validated",
            created_by=user_id,
        )
    )
    session.add(
        FeatureSetModel(
            id=feature_set_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Merchant Signals",
            slug=f"{slug}-merchant-signals",
            description="",
            entity_key="merchant_id",
            status="active",
        )
    )
    session.add(
        ExperimentModel(
            id=experiment_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Risk Baseline",
            slug=f"{slug}-baseline",
            description="",
            owner_user_id=user_id,
            status="active",
        )
    )
    for run_id, run_name, auc, log_loss in (
        (baseline_run_id, "xgb-depth-4", 0.91, 0.24),
        (champion_run_id, "xgb-depth-8", 0.96, 0.18),
    ):
        session.add(
            ExperimentRunModel(
                id=run_id,
                experiment_id=experiment_id,
                project_id=project_id,
                run_name=run_name,
                status="succeeded",
                model_type="binary_classifier",
                started_by=user_id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                parameters_json={"max_depth": 8 if run_id == champion_run_id else 4},
                metrics_json={"auc": auc, "log_loss": log_loss},
                artifact_uri=f"s3://forgeml/training-runs/{run_name}",
                evaluation_report_json={"slice_metrics": {"amount_high": {"auc": auc}}},
                error_message=None,
            )
        )
    for training_run_id, experiment_run_id, auc in (
        (baseline_training_id, baseline_run_id, 0.91),
        (champion_training_id, champion_run_id, 0.96),
    ):
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
                model_type="binary_classifier",
                objective_metric_name="auc",
                hyperparameters_json={"max_depth": 8},
                status="succeeded",
                requested_by=user_id,
                artifact_uri=f"s3://forgeml/training-runs/{training_run_id}",
                orchestrator_run_id=f"training-{training_run_id}",
                metrics_json={"auc": auc},
                error_message=None,
            )
        )
    session.add(
        RegisteredModelModel(
            id=registered_model_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Risk XGB",
            slug=f"{slug}-xgb",
            description="",
            task_type="classification",
            owner_user_id=user_id,
            status="active",
        )
    )
    session.add(
        ModelVersionModel(
            id=model_version_id,
            registered_model_id=registered_model_id,
            version=2,
            training_run_id=champion_training_id,
            experiment_run_id=champion_run_id,
            artifact_uri="s3://forgeml/models/fraud-risk-xgb/v2",
            artifact_manifest_uri="s3://forgeml/models/fraud-risk-xgb/v2/manifest.json",
            artifact_manifest_hash="sha256:model-manifest",
            model_format="xgboost-booster",
            signature_json={
                "inputs": [{"name": "amount"}],
                "outputs": [{"name": "risk_score"}],
            },
            metrics_json={"auc": 0.96, "log_loss": 0.18},
            status="approved",
            created_by=user_id,
        )
    )
    session.add(
        ModelApprovalModel(
            id=uuid4(),
            model_version_id=model_version_id,
            status="approved",
            requested_by=user_id,
            reviewer_id=user_id,
            comment="Meets launch gate.",
            policy_snapshot_json={"requires_signature": True},
        )
    )
    session.add_all(
        [
            ModelLineageModel(
                id=uuid4(),
                model_version_id=model_version_id,
                source_type="dataset_version",
                source_id=str(dataset_version_id),
            ),
            ModelLineageModel(
                id=uuid4(),
                model_version_id=model_version_id,
                source_type="feature_set",
                source_id=str(feature_set_id),
            ),
        ]
    )
    return {
        "dataset_version_id": dataset_version_id,
        "feature_set_id": feature_set_id,
        "model_version_id": model_version_id,
    }
