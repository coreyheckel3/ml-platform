from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.feature_store.api.schemas import (
    CreateFeatureSetRequest,
    FeatureDefinitionListResponse,
    FeatureDefinitionResponse,
    FeatureLineageListResponse,
    FeatureLineageResponse,
    FeatureMaterializationListResponse,
    FeatureMaterializationResponse,
    FeaturePipelineListResponse,
    FeaturePipelineResponse,
    FeatureSetListResponse,
    FeatureSetResponse,
    RegisterFeatureDefinitionsRequest,
    RegisterFeaturePipelineRequest,
)
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
from forgeml.modules.feature_store.infrastructure.orchestrator import (
    LocalFeatureWorkflowOrchestrator,
)
from forgeml.modules.feature_store.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyFeatureStoreRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["feature-store"])


def get_feature_store_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> FeatureStoreService:
    return FeatureStoreService(
        repository=SqlAlchemyFeatureStoreRepository(session),
        orchestrator=LocalFeatureWorkflowOrchestrator(),
        artifact_bucket=settings.object_storage_bucket,
    )


@router.post(
    "/projects/{project_id}/feature-sets",
    response_model=FeatureSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_feature_set(
    project_id: UUID,
    request: CreateFeatureSetRequest,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureSetResponse:
    feature_set = service.create_feature_set(
        CreateFeatureSetCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            name=request.name,
            description=request.description,
            entity_key=request.entity_key,
        ),
        principal,
    )
    return _feature_set_response(feature_set)


@router.get("/projects/{project_id}/feature-sets", response_model=FeatureSetListResponse)
def list_feature_sets(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureSetListResponse:
    return FeatureSetListResponse(
        items=[
            _feature_set_response(feature_set)
            for feature_set in service.list_feature_sets(project_id, principal)
        ]
    )


@router.get("/feature-sets/{feature_set_id}", response_model=FeatureSetResponse)
def get_feature_set(
    feature_set_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureSetResponse:
    return _feature_set_response(service.get_feature_set(feature_set_id, principal))


@router.post(
    "/feature-sets/{feature_set_id}/features",
    response_model=FeatureDefinitionListResponse,
)
def register_feature_definitions(
    feature_set_id: UUID,
    request: RegisterFeatureDefinitionsRequest,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureDefinitionListResponse:
    definitions = service.register_feature_definitions(
        RegisterFeatureDefinitionsCommand(
            feature_set_id=feature_set_id,
            definitions=tuple(
                FeatureDefinitionInput(
                    name=definition.name,
                    dtype=definition.dtype,
                    description=definition.description,
                    nullable=definition.nullable,
                    constraints=definition.constraints,
                )
                for definition in request.definitions
            ),
        ),
        principal,
    )
    return FeatureDefinitionListResponse(
        items=[_feature_definition_response(definition) for definition in definitions]
    )


@router.get(
    "/feature-sets/{feature_set_id}/features",
    response_model=FeatureDefinitionListResponse,
)
def list_feature_definitions(
    feature_set_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureDefinitionListResponse:
    return FeatureDefinitionListResponse(
        items=[
            _feature_definition_response(definition)
            for definition in service.list_feature_definitions(feature_set_id, principal)
        ]
    )


@router.post(
    "/feature-sets/{feature_set_id}/pipelines",
    response_model=FeaturePipelineResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_feature_pipeline(
    feature_set_id: UUID,
    request: RegisterFeaturePipelineRequest,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeaturePipelineResponse:
    pipeline = service.register_pipeline(
        RegisterFeaturePipelineCommand(
            feature_set_id=feature_set_id,
            name=request.name,
            source_dataset_id=(
                UUID(request.source_dataset_id) if request.source_dataset_id else None
            ),
            code_ref=request.code_ref,
            schedule_cron=request.schedule_cron,
        ),
        principal,
    )
    return _feature_pipeline_response(pipeline)


@router.get(
    "/feature-sets/{feature_set_id}/pipelines",
    response_model=FeaturePipelineListResponse,
)
def list_feature_pipelines(
    feature_set_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeaturePipelineListResponse:
    return FeaturePipelineListResponse(
        items=[
            _feature_pipeline_response(pipeline)
            for pipeline in service.list_pipelines(feature_set_id, principal)
        ]
    )


@router.post(
    "/feature-pipelines/{pipeline_id}/materialize",
    response_model=FeatureMaterializationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def materialize_feature_pipeline(
    pipeline_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureMaterializationResponse:
    return _feature_materialization_response(
        service.materialize_pipeline(
            MaterializeFeaturePipelineCommand(pipeline_id=pipeline_id),
            principal,
        )
    )


@router.get(
    "/feature-sets/{feature_set_id}/materializations",
    response_model=FeatureMaterializationListResponse,
)
def list_feature_materializations(
    feature_set_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureMaterializationListResponse:
    return FeatureMaterializationListResponse(
        items=[
            _feature_materialization_response(materialization)
            for materialization in service.list_materializations(feature_set_id, principal)
        ]
    )


@router.get("/feature-sets/{feature_set_id}/lineage", response_model=FeatureLineageListResponse)
def get_feature_lineage(
    feature_set_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: FeatureStoreService = Depends(get_feature_store_service),
) -> FeatureLineageListResponse:
    return FeatureLineageListResponse(
        items=[
            _feature_lineage_response(lineage)
            for lineage in service.get_lineage(feature_set_id, principal)
        ]
    )


def _feature_set_response(feature_set: FeatureSet) -> FeatureSetResponse:
    return FeatureSetResponse(
        id=str(feature_set.id),
        organization_id=str(feature_set.organization_id),
        project_id=str(feature_set.project_id),
        name=feature_set.name,
        slug=feature_set.slug,
        description=feature_set.description,
        entity_key=feature_set.entity_key,
        status=feature_set.status.value,
    )


def _feature_definition_response(definition: FeatureDefinition) -> FeatureDefinitionResponse:
    return FeatureDefinitionResponse(
        id=str(definition.id),
        feature_set_id=str(definition.feature_set_id),
        name=definition.name,
        dtype=definition.dtype,
        description=definition.description,
        nullable=definition.nullable,
        constraints=definition.constraints,
    )


def _feature_pipeline_response(pipeline: FeaturePipeline) -> FeaturePipelineResponse:
    return FeaturePipelineResponse(
        id=str(pipeline.id),
        feature_set_id=str(pipeline.feature_set_id),
        name=pipeline.name,
        source_dataset_id=str(pipeline.source_dataset_id) if pipeline.source_dataset_id else None,
        code_ref=pipeline.code_ref,
        schedule_cron=pipeline.schedule_cron,
        status=pipeline.status.value,
    )


def _feature_materialization_response(
    materialization: FeatureMaterialization,
) -> FeatureMaterializationResponse:
    return FeatureMaterializationResponse(
        id=str(materialization.id),
        feature_set_id=str(materialization.feature_set_id),
        pipeline_id=str(materialization.pipeline_id),
        version=materialization.version,
        offline_uri=materialization.offline_uri,
        online_ref=materialization.online_ref,
        orchestrator_run_id=materialization.orchestrator_run_id,
        status=materialization.status.value,
    )


def _feature_lineage_response(lineage: FeatureLineage) -> FeatureLineageResponse:
    return FeatureLineageResponse(
        id=str(lineage.id),
        feature_set_id=str(lineage.feature_set_id),
        upstream_type=lineage.upstream_type,
        upstream_id=lineage.upstream_id,
    )
