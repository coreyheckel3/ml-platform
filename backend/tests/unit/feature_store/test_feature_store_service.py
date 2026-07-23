from uuid import UUID, uuid4

import pytest

from forgeml.modules.feature_store.application.services import (
    CreateFeatureSetCommand,
    FeatureDefinitionInput,
    FeatureStoreService,
    MaterializeFeaturePipelineCommand,
    RegisterFeatureDefinitionsCommand,
    RegisterFeaturePipelineCommand,
)
from forgeml.modules.feature_store.domain.entities import (
    FeatureDefinition,
    FeatureLineage,
    FeatureMaterialization,
    FeaturePipeline,
    FeatureSet,
)
from forgeml.platform.domain.errors import ConflictError, PermissionDeniedError
from forgeml.platform.security.rbac import Principal


class FakeFeatureRepository:
    def __init__(self) -> None:
        self.feature_sets: dict[UUID, FeatureSet] = {}
        self.definitions: dict[UUID, list[FeatureDefinition]] = {}
        self.pipelines: dict[UUID, FeaturePipeline] = {}
        self.materializations: list[FeatureMaterialization] = []
        self.lineage: list[FeatureLineage] = []

    def add_feature_set(self, feature_set: FeatureSet) -> FeatureSet:
        self.feature_sets[feature_set.id] = feature_set
        return feature_set

    def get_feature_set(self, feature_set_id: UUID) -> FeatureSet | None:
        return self.feature_sets.get(feature_set_id)

    def list_feature_sets(self, organization_id: UUID, project_id: UUID) -> list[FeatureSet]:
        return [
            feature_set
            for feature_set in self.feature_sets.values()
            if feature_set.organization_id == organization_id
            and feature_set.project_id == project_id
        ]

    def feature_set_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return any(
            feature_set.organization_id == organization_id
            and feature_set.project_id == project_id
            and feature_set.slug == slug
            for feature_set in self.feature_sets.values()
        )

    def replace_feature_definitions(
        self,
        feature_set_id: UUID,
        definitions: tuple[FeatureDefinition, ...],
    ) -> list[FeatureDefinition]:
        self.definitions[feature_set_id] = list(definitions)
        return list(definitions)

    def list_feature_definitions(self, feature_set_id: UUID) -> list[FeatureDefinition]:
        return self.definitions.get(feature_set_id, [])

    def add_feature_pipeline(self, pipeline: FeaturePipeline) -> FeaturePipeline:
        self.pipelines[pipeline.id] = pipeline
        return pipeline

    def get_feature_pipeline(self, pipeline_id: UUID) -> FeaturePipeline | None:
        return self.pipelines.get(pipeline_id)

    def list_feature_pipelines(self, feature_set_id: UUID) -> list[FeaturePipeline]:
        return [
            pipeline
            for pipeline in self.pipelines.values()
            if pipeline.feature_set_id == feature_set_id
        ]

    def pipeline_name_exists(self, feature_set_id: UUID, name: str) -> bool:
        return any(
            pipeline.feature_set_id == feature_set_id and pipeline.name == name
            for pipeline in self.pipelines.values()
        )

    def latest_materialization_version(self, feature_set_id: UUID) -> int:
        return max(
            (
                materialization.version
                for materialization in self.materializations
                if materialization.feature_set_id == feature_set_id
            ),
            default=0,
        )

    def add_materialization(
        self,
        materialization: FeatureMaterialization,
    ) -> FeatureMaterialization:
        self.materializations.append(materialization)
        return materialization

    def list_materializations(self, feature_set_id: UUID) -> list[FeatureMaterialization]:
        return [
            materialization
            for materialization in self.materializations
            if materialization.feature_set_id == feature_set_id
        ]

    def add_lineage(self, lineage: FeatureLineage) -> FeatureLineage:
        self.lineage.append(lineage)
        return lineage

    def list_lineage(self, feature_set_id: UUID) -> list[FeatureLineage]:
        return [lineage for lineage in self.lineage if lineage.feature_set_id == feature_set_id]


class FakeOrchestrator:
    def trigger_materialization(self, pipeline: FeaturePipeline, materialization_id: UUID) -> str:
        return f"run:{pipeline.id}:{materialization_id}"


def principal(organization_id: UUID, user_id: UUID, permissions: set[str]) -> Principal:
    return Principal(
        user_id=str(user_id),
        email="owner@example.com",
        organization_id=str(organization_id),
        permissions=frozenset(permissions),
    )


def test_feature_store_service_registers_definitions_pipeline_and_materialization() -> None:
    repository = FakeFeatureRepository()
    service = FeatureStoreService(
        repository=repository,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
    )
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(
        organization_id,
        user_id,
        {
            "feature_sets:create",
            "feature_sets:read",
            "feature_definitions:write",
            "feature_pipelines:write",
            "feature_materializations:create",
        },
    )

    feature_set = service.create_feature_set(
        CreateFeatureSetCommand(
            organization_id=organization_id,
            project_id=project_id,
            name="Merchant Signals",
            description="Merchant behavior features.",
            entity_key="merchant_id",
        ),
        actor,
    )
    definitions = service.register_feature_definitions(
        RegisterFeatureDefinitionsCommand(
            feature_set_id=feature_set.id,
            definitions=(
                FeatureDefinitionInput(
                    name="chargeback_rate_30d",
                    dtype="float",
                    description="Rolling chargeback rate.",
                    nullable=False,
                    constraints={"min": 0, "max": 1},
                ),
            ),
        ),
        actor,
    )
    source_dataset_id = uuid4()
    pipeline = service.register_pipeline(
        RegisterFeaturePipelineCommand(
            feature_set_id=feature_set.id,
            name="daily materialization",
            source_dataset_id=source_dataset_id,
            code_ref="git://feature-pipelines/merchant_signals.py",
            schedule_cron="0 3 * * *",
        ),
        actor,
    )
    materialization = service.materialize_pipeline(
        MaterializeFeaturePipelineCommand(pipeline_id=pipeline.id),
        actor,
    )

    assert feature_set.slug == "merchant-signals"
    assert definitions[0].dtype == "float"
    assert repository.lineage[0].upstream_id == str(source_dataset_id)
    assert materialization.version == 1
    assert materialization.offline_uri.startswith("s3://forgeml-artifacts/features/")


def test_feature_store_service_rejects_duplicate_feature_set_slug() -> None:
    repository = FakeFeatureRepository()
    service = FeatureStoreService(
        repository=repository,
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
    )
    organization_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()
    actor = principal(organization_id, user_id, {"feature_sets:create"})
    command = CreateFeatureSetCommand(
        organization_id=organization_id,
        project_id=project_id,
        name="User Features",
        description="",
        entity_key="user_id",
    )

    service.create_feature_set(command, actor)

    with pytest.raises(ConflictError):
        service.create_feature_set(command, actor)


def test_feature_store_service_requires_permissions() -> None:
    service = FeatureStoreService(
        repository=FakeFeatureRepository(),
        orchestrator=FakeOrchestrator(),
        artifact_bucket="forgeml-artifacts",
    )
    organization_id = uuid4()
    user_id = uuid4()

    with pytest.raises(PermissionDeniedError):
        service.create_feature_set(
            CreateFeatureSetCommand(
                organization_id=organization_id,
                project_id=uuid4(),
                name="User Features",
                description="",
                entity_key="user_id",
            ),
            principal(organization_id, user_id, {"feature_sets:read"}),
        )
