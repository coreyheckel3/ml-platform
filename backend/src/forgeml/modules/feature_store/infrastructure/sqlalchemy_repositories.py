from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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
from forgeml.modules.feature_store.infrastructure.sqlalchemy_models import (
    FeatureDefinitionModel,
    FeatureLineageModel,
    FeatureMaterializationModel,
    FeaturePipelineModel,
    FeatureSetModel,
)


class SqlAlchemyFeatureStoreRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_feature_set(self, feature_set: FeatureSet) -> FeatureSet:
        model = FeatureSetModel(
            id=feature_set.id,
            organization_id=feature_set.organization_id,
            project_id=feature_set.project_id,
            name=feature_set.name,
            slug=feature_set.slug,
            description=feature_set.description,
            entity_key=feature_set.entity_key,
            status=feature_set.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return _feature_set_to_domain(model)

    def get_feature_set(self, feature_set_id: UUID) -> FeatureSet | None:
        model = self._session.get(FeatureSetModel, feature_set_id)
        return _feature_set_to_domain(model) if model else None

    def list_feature_sets(self, organization_id: UUID, project_id: UUID) -> list[FeatureSet]:
        models = self._session.scalars(
            select(FeatureSetModel)
            .where(
                FeatureSetModel.organization_id == organization_id,
                FeatureSetModel.project_id == project_id,
            )
            .order_by(FeatureSetModel.name)
        ).all()
        return [_feature_set_to_domain(model) for model in models]

    def feature_set_slug_exists(self, organization_id: UUID, project_id: UUID, slug: str) -> bool:
        return (
            self._session.scalar(
                select(FeatureSetModel.id).where(
                    FeatureSetModel.organization_id == organization_id,
                    FeatureSetModel.project_id == project_id,
                    FeatureSetModel.slug == slug,
                )
            )
            is not None
        )

    def replace_feature_definitions(
        self,
        feature_set_id: UUID,
        definitions: tuple[FeatureDefinition, ...],
    ) -> list[FeatureDefinition]:
        self._session.execute(
            delete(FeatureDefinitionModel).where(
                FeatureDefinitionModel.feature_set_id == feature_set_id
            )
        )
        models = [
            FeatureDefinitionModel(
                id=definition.id,
                feature_set_id=definition.feature_set_id,
                name=definition.name,
                dtype=definition.dtype,
                description=definition.description,
                nullable=definition.nullable,
                constraints_json=definition.constraints,
            )
            for definition in definitions
        ]
        self._session.add_all(models)
        self._session.flush()
        return [_feature_definition_to_domain(model) for model in models]

    def list_feature_definitions(self, feature_set_id: UUID) -> list[FeatureDefinition]:
        models = self._session.scalars(
            select(FeatureDefinitionModel)
            .where(FeatureDefinitionModel.feature_set_id == feature_set_id)
            .order_by(FeatureDefinitionModel.name)
        ).all()
        return [_feature_definition_to_domain(model) for model in models]

    def add_feature_pipeline(self, pipeline: FeaturePipeline) -> FeaturePipeline:
        model = FeaturePipelineModel(
            id=pipeline.id,
            feature_set_id=pipeline.feature_set_id,
            name=pipeline.name,
            source_dataset_id=pipeline.source_dataset_id,
            code_ref=pipeline.code_ref,
            schedule_cron=pipeline.schedule_cron,
            status=pipeline.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return _feature_pipeline_to_domain(model)

    def get_feature_pipeline(self, pipeline_id: UUID) -> FeaturePipeline | None:
        model = self._session.get(FeaturePipelineModel, pipeline_id)
        return _feature_pipeline_to_domain(model) if model else None

    def list_feature_pipelines(self, feature_set_id: UUID) -> list[FeaturePipeline]:
        models = self._session.scalars(
            select(FeaturePipelineModel)
            .where(FeaturePipelineModel.feature_set_id == feature_set_id)
            .order_by(FeaturePipelineModel.name)
        ).all()
        return [_feature_pipeline_to_domain(model) for model in models]

    def pipeline_name_exists(self, feature_set_id: UUID, name: str) -> bool:
        return (
            self._session.scalar(
                select(FeaturePipelineModel.id).where(
                    FeaturePipelineModel.feature_set_id == feature_set_id,
                    FeaturePipelineModel.name == name,
                )
            )
            is not None
        )

    def latest_materialization_version(self, feature_set_id: UUID) -> int:
        versions = self._session.scalars(
            select(FeatureMaterializationModel.version).where(
                FeatureMaterializationModel.feature_set_id == feature_set_id
            )
        ).all()
        return max(versions, default=0)

    def add_materialization(
        self,
        materialization: FeatureMaterialization,
    ) -> FeatureMaterialization:
        model = FeatureMaterializationModel(
            id=materialization.id,
            feature_set_id=materialization.feature_set_id,
            pipeline_id=materialization.pipeline_id,
            version=materialization.version,
            offline_uri=materialization.offline_uri,
            online_ref=materialization.online_ref,
            orchestrator_run_id=materialization.orchestrator_run_id,
            status=materialization.status.value,
        )
        self._session.add(model)
        self._session.flush()
        return _feature_materialization_to_domain(model)

    def list_materializations(self, feature_set_id: UUID) -> list[FeatureMaterialization]:
        models = self._session.scalars(
            select(FeatureMaterializationModel)
            .where(FeatureMaterializationModel.feature_set_id == feature_set_id)
            .order_by(FeatureMaterializationModel.version.desc())
        ).all()
        return [_feature_materialization_to_domain(model) for model in models]

    def add_lineage(self, lineage: FeatureLineage) -> FeatureLineage:
        model = FeatureLineageModel(
            id=lineage.id,
            feature_set_id=lineage.feature_set_id,
            upstream_type=lineage.upstream_type,
            upstream_id=lineage.upstream_id,
        )
        self._session.add(model)
        self._session.flush()
        return _feature_lineage_to_domain(model)

    def list_lineage(self, feature_set_id: UUID) -> list[FeatureLineage]:
        models = self._session.scalars(
            select(FeatureLineageModel)
            .where(FeatureLineageModel.feature_set_id == feature_set_id)
            .order_by(FeatureLineageModel.upstream_type, FeatureLineageModel.upstream_id)
        ).all()
        return [_feature_lineage_to_domain(model) for model in models]


def _feature_set_to_domain(model: FeatureSetModel) -> FeatureSet:
    return FeatureSet(
        id=model.id,
        organization_id=model.organization_id,
        project_id=model.project_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        entity_key=model.entity_key,
        status=FeatureSetStatus(model.status),
    )


def _feature_definition_to_domain(model: FeatureDefinitionModel) -> FeatureDefinition:
    return FeatureDefinition(
        id=model.id,
        feature_set_id=model.feature_set_id,
        name=model.name,
        dtype=model.dtype,
        description=model.description,
        nullable=model.nullable,
        constraints=model.constraints_json,
    )


def _feature_pipeline_to_domain(model: FeaturePipelineModel) -> FeaturePipeline:
    return FeaturePipeline(
        id=model.id,
        feature_set_id=model.feature_set_id,
        name=model.name,
        source_dataset_id=model.source_dataset_id,
        code_ref=model.code_ref,
        schedule_cron=model.schedule_cron,
        status=FeaturePipelineStatus(model.status),
    )


def _feature_materialization_to_domain(
    model: FeatureMaterializationModel,
) -> FeatureMaterialization:
    return FeatureMaterialization(
        id=model.id,
        feature_set_id=model.feature_set_id,
        pipeline_id=model.pipeline_id,
        version=model.version,
        offline_uri=model.offline_uri,
        online_ref=model.online_ref,
        orchestrator_run_id=model.orchestrator_run_id,
        status=FeatureMaterializationStatus(model.status),
    )


def _feature_lineage_to_domain(model: FeatureLineageModel) -> FeatureLineage:
    return FeatureLineage(
        id=model.id,
        feature_set_id=model.feature_set_id,
        upstream_type=model.upstream_type,
        upstream_id=model.upstream_id,
    )

