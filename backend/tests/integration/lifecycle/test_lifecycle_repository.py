from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.alerting.infrastructure.sqlalchemy_models import (
    AlertEventModel,
    AlertRuleModel,
)
from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import (
    DatasetModel,
    DatasetValidationRunModel,
    DatasetVersionModel,
)
from forgeml.modules.deployments.infrastructure.sqlalchemy_models import (
    DeploymentModel,
    DeploymentRevisionModel,
)
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import (
    DriftProfileModel,
    DriftReportModel,
)
from forgeml.modules.experiments.infrastructure.sqlalchemy_models import (
    ExperimentModel,
    ExperimentRunModel,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import (
    FeatureMaterializationModel,
    FeaturePipelineModel,
    FeatureSetModel,
)
from forgeml.modules.inference.infrastructure.sqlalchemy_models import (
    InferenceEndpointModel,
    InferenceMetricSnapshotModel,
    InferenceRequestLogModel,
)
from forgeml.modules.lifecycle.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyProjectLifecycleRepository,
)
from forgeml.modules.model_registry.infrastructure.sqlalchemy_models import (
    ModelApprovalModel,
    ModelVersionModel,
    RegisteredModelModel,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.modules.retraining.infrastructure.sqlalchemy_models import (
    RetrainingPolicyModel,
    RetrainingRunModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base


def test_lifecycle_repository_loads_project_lifecycle_snapshot() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    with Session(engine) as session:
        seeded = _seed_lifecycle(session, organization_id, project_id, user_id)
        _seed_lifecycle(session, uuid4(), uuid4(), uuid4(), project_name="Other Org")
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyProjectLifecycleRepository(session)
        snapshot = repository.load_snapshot(organization_id, project_id)

    assert snapshot is not None
    assert snapshot.project_id == project_id
    assert snapshot.project_name == "Fraud Detection"
    assert snapshot.datasets == 1
    assert snapshot.dataset_versions == 1
    assert snapshot.validation_runs == 1
    assert snapshot.feature_sets == 1
    assert snapshot.feature_pipelines == 1
    assert snapshot.materializations == 1
    assert snapshot.experiments == 1
    assert snapshot.experiment_runs == 1
    assert snapshot.training_runs == 2
    assert snapshot.succeeded_training_runs == 1
    assert snapshot.failed_training_runs == 1
    assert snapshot.registered_models == 1
    assert snapshot.model_versions == 1
    assert snapshot.approved_model_versions == 1
    assert snapshot.deployments == 1
    assert snapshot.active_deployments == 1
    assert snapshot.inference_endpoints == 1
    assert snapshot.active_inference_endpoints == 1
    assert snapshot.prediction_count == 1200
    assert snapshot.request_count == 2
    assert snapshot.inference_error_count == 12
    assert snapshot.max_p95_latency_ms == 84.8
    assert snapshot.drift_profiles == 1
    assert snapshot.drift_reports == 1
    assert snapshot.breached_drift_reports == 1
    assert snapshot.alert_rules == 1
    assert snapshot.active_alert_events == 1
    assert snapshot.retraining_policies == 1
    assert snapshot.enabled_retraining_policies == 1
    assert snapshot.retraining_runs == 2
    assert snapshot.successful_retraining_runs == 1
    assert snapshot.queued_retraining_runs == 1
    assert snapshot.last_updated_at is not None
    assert seeded["project_id"] == project_id


def test_lifecycle_repository_returns_none_for_cross_organization_project() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()

    with Session(engine) as session:
        _seed_lifecycle(session, organization_id, project_id, uuid4())
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyProjectLifecycleRepository(session)
        snapshot = repository.load_snapshot(uuid4(), project_id)

    assert snapshot is None


def _seed_lifecycle(
    session: Session,
    organization_id,
    project_id,
    user_id,
    *,
    project_name: str = "Fraud Detection",
) -> dict[str, object]:
    dataset_id = uuid4()
    dataset_version_id = uuid4()
    feature_set_id = uuid4()
    pipeline_id = uuid4()
    materialization_id = uuid4()
    experiment_id = uuid4()
    experiment_run_id = uuid4()
    succeeded_training_run_id = uuid4()
    failed_training_run_id = uuid4()
    registered_model_id = uuid4()
    model_version_id = uuid4()
    deployment_id = uuid4()
    deployment_revision_id = uuid4()
    endpoint_id = uuid4()
    drift_profile_id = uuid4()
    drift_report_id = uuid4()
    alert_rule_id = uuid4()
    policy_id = uuid4()

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
            name="Transactions",
            slug=f"{slug}-transactions",
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
            object_uri="s3://forgeml/datasets/transactions.csv",
            content_hash="sha256:dataset",
            row_count=1000,
            size_bytes=2048,
            status="validated",
            created_by=user_id,
        )
    )
    session.add(
        DatasetValidationRunModel(
            id=uuid4(),
            dataset_version_id=dataset_version_id,
            status="passed",
            report_json={"columns": 12},
            error_message=None,
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
        FeaturePipelineModel(
            id=pipeline_id,
            feature_set_id=feature_set_id,
            name="daily materialization",
            source_dataset_id=dataset_id,
            code_ref="git://features/merchant_signals.py",
            schedule_cron="0 3 * * *",
            status="active",
        )
    )
    session.add(
        FeatureMaterializationModel(
            id=materialization_id,
            feature_set_id=feature_set_id,
            pipeline_id=pipeline_id,
            version=1,
            offline_uri="s3://forgeml/features/merchant-signals/v1",
            online_ref="feature-set:merchant:v1",
            orchestrator_run_id="feature-run-1",
            status="succeeded",
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
    session.add(
        ExperimentRunModel(
            id=experiment_run_id,
            experiment_id=experiment_id,
            project_id=project_id,
            run_name="xgb-depth-6",
            status="succeeded",
            model_type="binary_classifier",
            started_by=user_id,
            dataset_version_id=dataset_version_id,
            feature_set_id=feature_set_id,
            parameters_json={"max_depth": 6},
            metrics_json={"auc": 0.94},
            artifact_uri="s3://forgeml/training-runs/run-1",
            evaluation_report_json={"auc": 0.94},
            error_message=None,
        )
    )
    for run_id, status, error_message in (
        (succeeded_training_run_id, "succeeded", None),
        (failed_training_run_id, "failed", "validation split missing target"),
    ):
        session.add(
            TrainingRunModel(
                id=run_id,
                organization_id=organization_id,
                project_id=project_id,
                experiment_id=experiment_id,
                experiment_run_id=experiment_run_id,
                dataset_version_id=dataset_version_id,
                feature_set_id=feature_set_id,
                algorithm="xgboost",
                model_type="binary_classifier",
                objective_metric_name="auc",
                hyperparameters_json={"max_depth": 6},
                status=status,
                requested_by=user_id,
                artifact_uri=f"s3://forgeml/training-runs/{run_id}",
                orchestrator_run_id=f"training-{run_id}",
                metrics_json={"auc": 0.94} if status == "succeeded" else {},
                error_message=error_message,
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
            version=1,
            training_run_id=succeeded_training_run_id,
            experiment_run_id=experiment_run_id,
            artifact_uri="s3://forgeml/models/fraud-risk-xgb/v1",
            artifact_manifest_uri="s3://forgeml/models/fraud-risk-xgb/v1/manifest.json",
            artifact_manifest_hash="sha256:model-manifest",
            model_format="xgboost-booster",
            signature_json={"inputs": [{"name": "amount"}]},
            metrics_json={"auc": 0.94},
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
    session.add(
        DeploymentModel(
            id=deployment_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Risk Production",
            slug=f"{slug}-production",
            description="",
            environment="production",
            status="active",
            created_by=user_id,
        )
    )
    session.add(
        DeploymentRevisionModel(
            id=deployment_revision_id,
            deployment_id=deployment_id,
            model_version_id=model_version_id,
            revision=1,
            serving_image="ghcr.io/forgeml/serving/xgboost:1.0.0",
            runtime_config_json={"replicas": 3},
            traffic_percentage=100,
            status="healthy",
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
            deployment_revision_id=deployment_revision_id,
            name="Fraud Risk Online",
            slug=f"{slug}-online",
            route_path=f"/inference/{slug}",
            description="",
            status="active",
            created_by=user_id,
        )
    )
    session.add(
        InferenceMetricSnapshotModel(
            id=uuid4(),
            endpoint_id=endpoint_id,
            window_seconds=300,
            prediction_count=1200,
            error_count=12,
            p50_latency_ms=18.2,
            p95_latency_ms=84.8,
        )
    )
    for index in range(2):
        session.add(
            InferenceRequestLogModel(
                id=uuid4(),
                endpoint_id=endpoint_id,
                deployment_revision_id=deployment_revision_id,
                request_id=f"{slug}-req-{index}",
                status="succeeded",
                latency_ms=18.0 + index,
                input_payload_json={"amount": 128.45},
                output_payload_json={"score": 0.81},
                error_message=None,
            )
        )
    session.add(
        DriftProfileModel(
            id=drift_profile_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Drift Baseline",
            slug=f"{slug}-drift-baseline",
            description="",
            model_version_id=model_version_id,
            dataset_version_id=dataset_version_id,
            baseline_profile_json={"features": {"amount": {"mean": 120.0}}},
            status="active",
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
            deployment_revision_id=deployment_revision_id,
            status="completed",
            drift_score=0.42,
            drifted_feature_count=2,
            evaluated_feature_count=5,
            window_seconds=3600,
            drift_threshold=0.3,
            summary_json={"risk": "elevated"},
            report_uri="s3://forgeml/reports/drift.json",
            error_message=None,
        )
    )
    session.add(
        AlertRuleModel(
            id=alert_rule_id,
            organization_id=organization_id,
            project_id=project_id,
            name="Fraud Error Rate",
            slug=f"{slug}-error-rate",
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
            alert_rule_id=alert_rule_id,
            endpoint_id=endpoint_id,
            severity="warning",
            status="open",
            message="Fraud Error Rate triggered.",
            observed_value=0.02,
            threshold=0.01,
            metadata_json={"metric": "inference_error_rate"},
            acknowledged_by=None,
            resolved_by=None,
        )
    )
    session.add(
        RetrainingPolicyModel(
            id=policy_id,
            organization_id=organization_id,
            project_id=project_id,
            deployment_id=deployment_id,
            name="Fraud drift retraining",
            slug=f"{slug}-drift-retraining",
            description="",
            trigger_type="drift",
            trigger_config_json={"threshold": 0.3},
            training_template_json={"algorithm": "xgboost"},
            cooldown_seconds=3600,
            max_runs_per_day=2,
            approval_required=True,
            enabled=True,
            status="active",
            created_by=user_id,
        )
    )
    session.add_all(
        [
            RetrainingRunModel(
                id=uuid4(),
                organization_id=organization_id,
                project_id=project_id,
                policy_id=policy_id,
                deployment_id=deployment_id,
                trigger_type="drift",
                drift_report_id=drift_report_id,
                alert_event_id=None,
                training_run_id=succeeded_training_run_id,
                status="succeeded",
                reason="drift threshold exceeded",
                training_config_json={"algorithm": "xgboost"},
                decision_metadata_json={"drift_score": 0.42},
                requested_by=user_id,
                approved_by=user_id,
                rejected_by=None,
            ),
            RetrainingRunModel(
                id=uuid4(),
                organization_id=organization_id,
                project_id=project_id,
                policy_id=policy_id,
                deployment_id=deployment_id,
                trigger_type="drift",
                drift_report_id=drift_report_id,
                alert_event_id=None,
                training_run_id=None,
                status="queued",
                reason="scheduled refresh",
                training_config_json={"algorithm": "xgboost"},
                decision_metadata_json={"schedule": "nightly"},
                requested_by=user_id,
                approved_by=None,
                rejected_by=None,
            ),
        ]
    )
    return {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "endpoint_id": endpoint_id,
    }
