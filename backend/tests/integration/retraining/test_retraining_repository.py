from datetime import timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.alerting.domain.entities import (
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from forgeml.modules.alerting.infrastructure.sqlalchemy_models import (
    AlertEventModel,
    AlertRuleModel,
)
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
    DeploymentEnvironment,
    DeploymentRevisionStatus,
    DeploymentStatus,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentModel,
    DeploymentRevisionModel,
)
from forgeml.modules.drift_detection.domain.entities import (
    DriftProfileStatus,
    DriftReportStatus,
)
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import (
    DriftFeatureResultModel,
    DriftProfileModel,
    DriftReportModel,
)
from forgeml.modules.experiments.domain.entities import ExperimentStatus
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import FeatureSetModel
from forgeml.modules.inference.domain.entities import InferenceEndpointStatus
from forgeml.modules.inference.infrastructure.sqlalchemy_models import InferenceEndpointModel
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.retraining.domain.entities import (
    RetrainingPolicy,
    RetrainingPolicyStatus,
    RetrainingRun,
    RetrainingRunStatus,
    RetrainingTriggerType,
)
from forgeml.modules.retraining.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyRetrainingRepository,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import (
    TrainingRunEventModel,
    TrainingRunModel,
)
from forgeml.platform.database.base import Base

_SQLALCHEMY_MODEL_DEPENDENCIES = (
    AlertEventModel,
    AlertRuleModel,
    DatasetModel,
    DatasetVersionModel,
    DriftFeatureResultModel,
    ExperimentModel,
    ExperimentRunModel,
    FeatureSetModel,
    ModelVersionModel,
    RegisteredModelModel,
    TrainingRunEventModel,
    TrainingRunModel,
)


def test_retraining_repository_round_trips_policies_runs_and_trigger_signals() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    dataset_version_id = uuid4()
    experiment_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    endpoint_id = uuid4()
    drift_profile_id = uuid4()
    drift_report_id = uuid4()
    alert_rule_id = uuid4()
    alert_event_id = uuid4()
    policy_id = uuid4()
    run_id = uuid4()

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
                model_version_id=uuid4(),
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
            DriftProfileModel(
                id=drift_profile_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Baseline",
                slug="fraud-baseline",
                description="",
                model_version_id=None,
                dataset_version_id=None,
                baseline_profile_json={"amount": {"type": "numeric", "mean": 100.0}},
                status=DriftProfileStatus.ACTIVE.value,
                created_by=user_id,
            )
        )
        session.add(
            DriftReportModel(
                id=drift_report_id,
                organization_id=organization_id,
                project_id=project_id,
                drift_profile_id=drift_profile_id,
                endpoint_id=endpoint_id,
                deployment_id=deployment_id,
                deployment_revision_id=revision_id,
                status=DriftReportStatus.COMPLETED.value,
                drift_score=0.42,
                drifted_feature_count=2,
                evaluated_feature_count=5,
                window_seconds=3600,
                drift_threshold=0.2,
                summary_json={"endpoint_name": "Fraud Risk Online"},
                report_uri="s3://forgeml/reports/drift/fraud/report.json",
                error_message=None,
            )
        )
        session.add(
            AlertRuleModel(
                id=alert_rule_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Error Rate",
                slug="fraud-error-rate",
                description="",
                severity=AlertSeverity.CRITICAL.value,
                metric=AlertMetric.INFERENCE_ERROR_RATE.value,
                operator=AlertOperator.GREATER_THAN.value,
                threshold=0.1,
                window_seconds=300,
                enabled=True,
                created_by=user_id,
            )
        )
        session.add(
            AlertEventModel(
                id=alert_event_id,
                organization_id=organization_id,
                project_id=project_id,
                alert_rule_id=alert_rule_id,
                endpoint_id=endpoint_id,
                severity=AlertSeverity.CRITICAL.value,
                status=AlertEventStatus.OPEN.value,
                message="Fraud endpoint error rate exceeded threshold.",
                observed_value=0.31,
                threshold=0.1,
                metadata_json={"route_path": "/inference/fraud-risk-online"},
                acknowledged_by=None,
                resolved_by=None,
            )
        )
        repository = SqlAlchemyRetrainingRepository(session)
        policy = repository.add_policy(
            RetrainingPolicy(
                id=policy_id,
                organization_id=organization_id,
                project_id=project_id,
                deployment_id=deployment_id,
                name="Fraud Drift Retraining",
                slug="fraud-drift-retraining",
                description="",
                trigger_type=RetrainingTriggerType.DRIFT,
                trigger_config={"min_drift_score": 0.2, "min_drifted_features": 1},
                training_template={
                    "experiment_id": str(experiment_id),
                    "dataset_version_id": str(dataset_version_id),
                    "feature_set_id": None,
                    "run_name_prefix": "fraud-retrain",
                    "algorithm": "xgboost",
                    "model_type": "xgboost",
                    "objective_metric_name": "auc",
                    "hyperparameters": {"max_depth": 6},
                },
                cooldown_seconds=3600,
                max_runs_per_day=3,
                approval_required=True,
                enabled=True,
                status=RetrainingPolicyStatus.ACTIVE,
                created_by=user_id,
            )
        )
        repository.add_run(
            RetrainingRun(
                id=run_id,
                organization_id=organization_id,
                project_id=project_id,
                policy_id=policy.id,
                deployment_id=deployment_id,
                trigger_type=RetrainingTriggerType.DRIFT,
                drift_report_id=drift_report_id,
                alert_event_id=None,
                training_run_id=None,
                status=RetrainingRunStatus.PENDING_APPROVAL,
                reason="Nightly drift evaluation.",
                training_config={"run_name": "fraud-retrain-drift-abcdef12"},
                decision_metadata={"drift_score": 0.42},
                requested_by=user_id,
                approved_by=None,
                rejected_by=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyRetrainingRepository(session)
        policies = repository.list_policies(organization_id, project_id)
        runs = repository.list_runs(organization_id, project_id)
        duplicate = repository.get_existing_run_for_trigger(policy_id, drift_report_id, None)
        latest_created_at = repository.latest_run_created_at(policy_id)
        daily_count = repository.count_runs_since(
            policy_id,
            runs[0].created_at - timedelta(seconds=1),
        )
        deployment_exists = repository.deployment_belongs_to_project(
            organization_id,
            project_id,
            deployment_id,
        )
        experiment_exists = repository.experiment_belongs_to_project(
            organization_id,
            project_id,
            experiment_id,
        )
        dataset_exists = repository.dataset_version_belongs_to_project(
            project_id,
            dataset_version_id,
        )
        drift_signal = repository.get_drift_signal(drift_report_id)
        alert_signal = repository.get_alert_signal(alert_event_id)

    assert policies[0].slug == "fraud-drift-retraining"
    assert runs[0].status == RetrainingRunStatus.PENDING_APPROVAL
    assert duplicate is not None
    assert latest_created_at is not None
    assert daily_count == 1
    assert deployment_exists
    assert experiment_exists
    assert dataset_exists
    assert drift_signal is not None
    assert drift_signal.drift_score == 0.42
    assert alert_signal is not None
    assert alert_signal.deployment_id == deployment_id
