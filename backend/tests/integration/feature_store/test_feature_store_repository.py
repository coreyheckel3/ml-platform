from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgeml.modules.auth.infrastructure.sqlalchemy_models import UserModel
from forgeml.modules.datasets.domain.entities import DatasetSourceType, DatasetStatus
from forgeml.modules.datasets.infrastructure.sqlalchemy_models import DatasetModel
from forgeml.modules.feature_store.domain.entities import (
    FeatureDefinition,
    FeatureLineage,
    FeatureMaterialization,
    FeatureMaterializationStatus,
    FeaturePipeline,
    FeaturePipelineStatus,
    FeatureSet,
    FeatureSetStatus,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyFeatureStoreRepository,
)
from forgeml.modules.projects.infrastructure.sqlalchemy_models import (
    OrganizationModel,
    ProjectModel,
)
from forgeml.platform.database.base import Base


def test_feature_store_repository_round_trips_feature_assets() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    dataset_id = uuid4()
    feature_set_id = uuid4()
    pipeline_id = uuid4()

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
        repository = SqlAlchemyFeatureStoreRepository(session)
        feature_set = repository.add_feature_set(
            FeatureSet(
                id=feature_set_id,
                organization_id=organization_id,
                project_id=project_id,
                name="Merchant Signals",
                slug="merchant-signals",
                description="",
                entity_key="merchant_id",
                status=FeatureSetStatus.ACTIVE,
            )
        )
        repository.replace_feature_definitions(
            feature_set.id,
            (
                FeatureDefinition(
                    id=uuid4(),
                    feature_set_id=feature_set.id,
                    name="chargeback_rate_30d",
                    dtype="float",
                    description="Rolling chargeback rate.",
                    nullable=False,
                    constraints={"min": 0, "max": 1},
                ),
            ),
        )
        pipeline = repository.add_feature_pipeline(
            FeaturePipeline(
                id=pipeline_id,
                feature_set_id=feature_set.id,
                name="daily materialization",
                source_dataset_id=dataset_id,
                code_ref="git://feature-pipelines/merchant_signals.py",
                schedule_cron="0 3 * * *",
                status=FeaturePipelineStatus.ACTIVE,
            )
        )
        repository.add_materialization(
            FeatureMaterialization(
                id=uuid4(),
                feature_set_id=feature_set.id,
                pipeline_id=pipeline.id,
                version=1,
                offline_uri="s3://forgeml/features/materialization",
                online_ref="feature-set:merchant:v1",
                orchestrator_run_id="run-1",
                status=FeatureMaterializationStatus.REQUESTED,
            )
        )
        repository.add_lineage(
            FeatureLineage(
                id=uuid4(),
                feature_set_id=feature_set.id,
                upstream_type="dataset",
                upstream_id=str(dataset_id),
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyFeatureStoreRepository(session)

        feature_sets = repository.list_feature_sets(organization_id, project_id)
        definitions = repository.list_feature_definitions(feature_set_id)
        pipelines = repository.list_feature_pipelines(feature_set_id)
        materializations = repository.list_materializations(feature_set_id)
        lineage = repository.list_lineage(feature_set_id)

    assert feature_sets[0].slug == "merchant-signals"
    assert definitions[0].constraints["max"] == 1
    assert pipelines[0].source_dataset_id == dataset_id
    assert materializations[0].version == 1
    assert lineage[0].upstream_id == str(dataset_id)

