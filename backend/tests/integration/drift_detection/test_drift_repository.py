from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
from forgeml.modules.drift_detection.domain.entities import (
    DriftFeatureResult,
    DriftFeatureType,
    DriftProfile,
    DriftProfileStatus,
    DriftReport,
    DriftReportStatus,
)
from forgeml.modules.drift_detection.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDriftDetectionRepository,
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
    InferenceRequestLogModel,
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


def test_drift_repository_round_trips_profiles_reports_features_and_samples() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    deployment_id = uuid4()
    revision_id = uuid4()
    endpoint_id = uuid4()
    profile_id = uuid4()
    report_id = uuid4()

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
        for index, amount in enumerate([142.0, 160.0, 155.0]):
            session.add(
                InferenceRequestLogModel(
                    id=uuid4(),
                    endpoint_id=endpoint_id,
                    deployment_revision_id=revision_id,
                    request_id=f"req-{index}",
                    status=InferenceRequestStatus.SUCCEEDED.value,
                    latency_ms=18.0 + index,
                    input_payload_json={
                        "amount": amount,
                        "merchant_category": "travel",
                    },
                    output_payload_json={"score": 0.81},
                    error_message=None,
                )
            )
        repository = SqlAlchemyDriftDetectionRepository(session)
        profile = repository.add_profile(
            DriftProfile(
                id=profile_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Fraud Baseline",
                slug="fraud-baseline",
                description="",
                model_version_id=None,
                dataset_version_id=None,
                baseline_profile={"amount": {"type": "numeric", "mean": 100.0, "std": 20.0}},
                status=DriftProfileStatus.ACTIVE,
                created_by=user_id,
            )
        )
        report = repository.add_report(
            DriftReport(
                id=report_id,
                organization_id=organization_id,
                project_id=project_id,
                drift_profile_id=profile.id,
                endpoint_id=endpoint_id,
                deployment_id=deployment_id,
                deployment_revision_id=revision_id,
                status=DriftReportStatus.COMPLETED,
                drift_score=0.42,
                drifted_feature_count=1,
                evaluated_feature_count=1,
                window_seconds=3600,
                drift_threshold=0.2,
                summary={"endpoint_name": "Fraud Risk Online"},
                report_uri="s3://forgeml/reports/drift/fraud/report.json",
                error_message=None,
            )
        )
        repository.add_feature_results(
            [
                DriftFeatureResult(
                    id=uuid4(),
                    drift_report_id=report.id,
                    feature_name="amount",
                    feature_type=DriftFeatureType.NUMERIC,
                    drift_score=0.42,
                    threshold=0.2,
                    drift_detected=True,
                    statistics={"observed_mean": 152.3},
                )
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyDriftDetectionRepository(session)
        profiles = repository.list_profiles(organization_id, project_id)
        reports = repository.list_reports_for_project(organization_id, project_id)
        profile_reports = repository.list_reports_for_profile(profile_id)
        feature_results = repository.list_feature_results(report_id)
        endpoint = repository.get_endpoint_reference(endpoint_id)
        samples = repository.list_inference_payload_samples(endpoint_id, 10)
        profile_slug_exists = repository.profile_slug_exists(
            organization_id,
            project_id,
            "fraud-baseline",
        )

    assert profiles[0].slug == "fraud-baseline"
    assert profile_slug_exists
    assert reports[0].drift_score == 0.42
    assert profile_reports[0].id == report_id
    assert feature_results[0].feature_name == "amount"
    assert endpoint is not None
    assert endpoint.route_path == "/inference/fraud-risk-online"
    assert len(samples) == 3
    assert samples[0]["merchant_category"] == "travel"
