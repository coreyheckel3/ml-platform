from uuid import UUID

from forgeml.modules.feature_store.domain.entities import FeaturePipeline


class LocalFeatureWorkflowOrchestrator:
    def trigger_materialization(self, pipeline: FeaturePipeline, materialization_id: UUID) -> str:
        return f"local-feature-materialization:{pipeline.id}:{materialization_id}"

