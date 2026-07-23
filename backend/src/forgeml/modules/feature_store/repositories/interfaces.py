from typing import Protocol
from uuid import UUID

from forgeml.modules.feature_store.domain.entities import (
    FeatureDefinition,
    FeatureLineage,
    FeatureMaterialization,
    FeaturePipeline,
    FeatureSet,
)


class FeatureStoreRepository(Protocol):
    def add_feature_set(self, feature_set: FeatureSet) -> FeatureSet:
        raise NotImplementedError

    def get_feature_set(self, feature_set_id: UUID) -> FeatureSet | None:
        raise NotImplementedError

    def list_feature_sets(self, organization_id: UUID, project_id: UUID) -> list[FeatureSet]:
        raise NotImplementedError

    def feature_set_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        raise NotImplementedError

    def replace_feature_definitions(
        self,
        feature_set_id: UUID,
        definitions: tuple[FeatureDefinition, ...],
    ) -> list[FeatureDefinition]:
        raise NotImplementedError

    def list_feature_definitions(self, feature_set_id: UUID) -> list[FeatureDefinition]:
        raise NotImplementedError

    def add_feature_pipeline(self, pipeline: FeaturePipeline) -> FeaturePipeline:
        raise NotImplementedError

    def get_feature_pipeline(self, pipeline_id: UUID) -> FeaturePipeline | None:
        raise NotImplementedError

    def list_feature_pipelines(self, feature_set_id: UUID) -> list[FeaturePipeline]:
        raise NotImplementedError

    def pipeline_name_exists(self, feature_set_id: UUID, name: str) -> bool:
        raise NotImplementedError

    def latest_materialization_version(self, feature_set_id: UUID) -> int:
        raise NotImplementedError

    def add_materialization(
        self,
        materialization: FeatureMaterialization,
    ) -> FeatureMaterialization:
        raise NotImplementedError

    def list_materializations(self, feature_set_id: UUID) -> list[FeatureMaterialization]:
        raise NotImplementedError

    def add_lineage(self, lineage: FeatureLineage) -> FeatureLineage:
        raise NotImplementedError

    def list_lineage(self, feature_set_id: UUID) -> list[FeatureLineage]:
        raise NotImplementedError


class FeatureWorkflowOrchestrator(Protocol):
    def trigger_materialization(self, pipeline: FeaturePipeline, materialization_id: UUID) -> str:
        raise NotImplementedError

