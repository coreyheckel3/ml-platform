from datetime import datetime, timedelta
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
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_models import (
    DriftProfileModel,
    DriftReportModel,
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
from forgeml.modules.retraining.infrastructure.sqlalchemy_models import (
    RetrainingPolicyModel,
    RetrainingRunModel,
)
from forgeml.modules.training.infrastructure.sqlalchemy_models import TrainingRunModel
from forgeml.platform.database.base import Base

_SQLALCHEMY_MODEL_DEPENDENCIES = (
    DatasetModel,
    DatasetVersionModel,
    DriftProfileModel,
    DriftReportModel,
    ExperimentModel,
    ExperimentRunModel,
    FeatureSetModel,
    ModelVersionModel,
    RegisteredModelModel,
    RetrainingPolicyModel,
    RetrainingRunModel,
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


def test_monitoring_repository_builds_operations_overview() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    model_version_id = uuid4()
    endpoint_id = uuid4()
    drift_profile_id = uuid4()
    drift_report_id = uuid4()
    training_run_id = uuid4()
    policy_id = uuid4()
    retraining_run_id = uuid4()
    observed_at = datetime(2026, 1, 15, 12, 0, 0)

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
                prediction_count=100,
                error_count=10,
                p50_latency_ms=24.0,
                p95_latency_ms=650.0,
            )
        )
        session.add(
            DriftProfileModel(
                id=drift_profile_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Drift Baseline",
                slug="fraud-drift-baseline",
                description="",
                model_version_id=None,
                dataset_version_id=None,
                baseline_profile_json={"features": {"amount": {"mean": 120.0}}},
                status="active",
                created_by=user_id,
            )
        )
        session.add_all(
            [
                DriftReportModel(
                    id=drift_report_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    drift_profile_id=drift_profile_id,
                    endpoint_id=endpoint_id,
                    deployment_id=deployment_id,
                    deployment_revision_id=revision_id,
                    status="completed",
                    drift_score=0.42,
                    drifted_feature_count=2,
                    evaluated_feature_count=5,
                    window_seconds=3600,
                    drift_threshold=0.3,
                    summary_json={"risk": "elevated"},
                    report_uri="s3://forgeml/reports/drift.json",
                    error_message=None,
                    created_at=observed_at,
                ),
                DriftReportModel(
                    id=uuid4(),
                    organization_id=organization_id,
                    project_id=project_id,
                    drift_profile_id=drift_profile_id,
                    endpoint_id=endpoint_id,
                    deployment_id=deployment_id,
                    deployment_revision_id=revision_id,
                    status="failed",
                    drift_score=0.0,
                    drifted_feature_count=0,
                    evaluated_feature_count=0,
                    window_seconds=3600,
                    drift_threshold=0.3,
                    summary_json={},
                    report_uri="",
                    error_message="not enough production samples",
                    created_at=observed_at - timedelta(minutes=5),
                ),
            ]
        )
        session.add_all(
            [
                TrainingRunModel(
                    id=training_run_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    experiment_id=uuid4(),
                    experiment_run_id=uuid4(),
                    dataset_version_id=None,
                    feature_set_id=None,
                    algorithm="xgboost",
                    model_type="binary_classifier",
                    objective_metric_name="auc",
                    hyperparameters_json={"max_depth": 4},
                    status="failed",
                    requested_by=user_id,
                    artifact_uri="s3://forgeml/models/fraud",
                    orchestrator_run_id="airflow-run-1",
                    metrics_json={},
                    error_message="validation split missing target",
                    attempt_count=2,
                    max_attempts=3,
                    worker_id="worker-a",
                    lease_expires_at=None,
                    last_heartbeat_at=None,
                    queued_at=observed_at - timedelta(minutes=15),
                    started_at=observed_at - timedelta(minutes=10),
                    completed_at=observed_at,
                    next_retry_at=None,
                    updated_at=observed_at,
                ),
                TrainingRunModel(
                    id=uuid4(),
                    organization_id=organization_id,
                    project_id=project_id,
                    experiment_id=uuid4(),
                    experiment_run_id=uuid4(),
                    dataset_version_id=None,
                    feature_set_id=None,
                    algorithm="lightgbm",
                    model_type="binary_classifier",
                    objective_metric_name="auc",
                    hyperparameters_json={},
                    status="running",
                    requested_by=user_id,
                    artifact_uri="s3://forgeml/models/fraud-running",
                    orchestrator_run_id="airflow-run-2",
                    metrics_json={},
                    error_message=None,
                    attempt_count=1,
                    max_attempts=3,
                    worker_id="worker-b",
                    lease_expires_at=None,
                    last_heartbeat_at=observed_at,
                    queued_at=observed_at - timedelta(minutes=3),
                    started_at=observed_at - timedelta(minutes=2),
                    completed_at=None,
                    next_retry_at=None,
                    updated_at=observed_at,
                ),
            ]
        )
        session.add(
            RetrainingPolicyModel(
                id=policy_id,
                organization_id=organization_id,
                project_id=project_id,
                deployment_id=deployment_id,
                name="Fraud drift retraining",
                slug="fraud-drift-retraining",
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
        session.add(
            RetrainingRunModel(
                id=retraining_run_id,
                organization_id=organization_id,
                project_id=project_id,
                policy_id=policy_id,
                deployment_id=deployment_id,
                trigger_type="drift",
                drift_report_id=drift_report_id,
                alert_event_id=None,
                training_run_id=training_run_id,
                status="queued",
                reason="drift threshold exceeded",
                training_config_json={"algorithm": "xgboost"},
                decision_metadata_json={"drift_score": 0.42},
                requested_by=user_id,
                approved_by=None,
                rejected_by=None,
                created_at=observed_at,
                updated_at=observed_at,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMonitoringRepository(session)
        overview = repository.get_operations_overview(organization_id, project_id)

    assert overview.project_id == project_id
    assert overview.inference.endpoint_count == 1
    assert overview.inference.error_rate == 0.1
    assert overview.inference.weighted_p95_latency_ms == 650.0
    assert overview.drift.report_count == 2
    assert overview.drift.failed_report_count == 1
    assert overview.drift.breached_report_count == 1
    assert overview.drift.latest_drift_score == 0.42
    assert overview.training.total_run_count == 2
    assert overview.training.running_count == 1
    assert overview.training.failure_rate == 0.5
    assert overview.training.average_training_time_seconds == 600.0
    assert overview.training.latest_failures[0].error_message == (
        "validation split missing target"
    )
    assert overview.retraining.policy_count == 1
    assert overview.retraining.enabled_policy_count == 1
    assert overview.retraining.queued_count == 1
    assert overview.retraining.latest_activity[0].training_run_id == training_run_id


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
