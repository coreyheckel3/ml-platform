from dataclasses import dataclass
from uuid import UUID, uuid4

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
from forgeml.modules.feature_store.domain.policies import (
    build_feature_set_slug,
    validate_code_ref,
    validate_entity_key,
    validate_feature_definitions,
    validate_feature_set_name,
    validate_pipeline_name,
)
from forgeml.modules.feature_store.repositories.interfaces import (
    FeatureStoreRepository,
    FeatureWorkflowOrchestrator,
)
from forgeml.platform.domain.errors import (
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from forgeml.platform.security.rbac import Principal


@dataclass(frozen=True)
class CreateFeatureSetCommand:
    organization_id: UUID
    project_id: UUID
    name: str
    description: str
    entity_key: str


@dataclass(frozen=True)
class FeatureDefinitionInput:
    name: str
    dtype: str
    description: str
    nullable: bool
    constraints: dict[str, object]


@dataclass(frozen=True)
class RegisterFeatureDefinitionsCommand:
    feature_set_id: UUID
    definitions: tuple[FeatureDefinitionInput, ...]


@dataclass(frozen=True)
class RegisterFeaturePipelineCommand:
    feature_set_id: UUID
    name: str
    source_dataset_id: UUID | None
    code_ref: str
    schedule_cron: str | None


@dataclass(frozen=True)
class MaterializeFeaturePipelineCommand:
    pipeline_id: UUID


class FeatureStoreService:
    def __init__(
        self,
        *,
        repository: FeatureStoreRepository,
        orchestrator: FeatureWorkflowOrchestrator,
        artifact_bucket: str,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator
        self._artifact_bucket = artifact_bucket

    def create_feature_set(
        self,
        command: CreateFeatureSetCommand,
        principal: Principal,
    ) -> FeatureSet:
        self._require(principal, "feature_sets:create")
        self._require_same_organization(command.organization_id, principal)
        validate_feature_set_name(command.name)
        validate_entity_key(command.entity_key)
        slug = build_feature_set_slug(command.name)
        if self._repository.feature_set_slug_exists(
            command.organization_id,
            command.project_id,
            slug,
        ):
            raise ConflictError("A feature set with this name already exists in the project.")

        feature_set = FeatureSet(
            id=uuid4(),
            organization_id=command.organization_id,
            project_id=command.project_id,
            name=command.name.strip(),
            slug=slug,
            description=command.description.strip(),
            entity_key=command.entity_key.strip(),
            status=FeatureSetStatus.ACTIVE,
        )
        return self._repository.add_feature_set(feature_set)

    def list_feature_sets(self, project_id: UUID, principal: Principal) -> list[FeatureSet]:
        self._require(principal, "feature_sets:read")
        return self._repository.list_feature_sets(UUID(principal.organization_id), project_id)

    def get_feature_set(self, feature_set_id: UUID, principal: Principal) -> FeatureSet:
        self._require(principal, "feature_sets:read")
        return self._get_scoped_feature_set(feature_set_id, principal)

    def register_feature_definitions(
        self,
        command: RegisterFeatureDefinitionsCommand,
        principal: Principal,
    ) -> list[FeatureDefinition]:
        self._require(principal, "feature_definitions:write")
        feature_set = self._get_scoped_feature_set(command.feature_set_id, principal)
        definitions = tuple(
            FeatureDefinition(
                id=uuid4(),
                feature_set_id=feature_set.id,
                name=definition.name.strip(),
                dtype=definition.dtype,
                description=definition.description.strip(),
                nullable=definition.nullable,
                constraints=definition.constraints,
            )
            for definition in command.definitions
        )
        validate_feature_definitions(definitions)
        return self._repository.replace_feature_definitions(feature_set.id, definitions)

    def list_feature_definitions(
        self,
        feature_set_id: UUID,
        principal: Principal,
    ) -> list[FeatureDefinition]:
        self._require(principal, "feature_sets:read")
        feature_set = self._get_scoped_feature_set(feature_set_id, principal)
        return self._repository.list_feature_definitions(feature_set.id)

    def register_pipeline(
        self,
        command: RegisterFeaturePipelineCommand,
        principal: Principal,
    ) -> FeaturePipeline:
        self._require(principal, "feature_pipelines:write")
        feature_set = self._get_scoped_feature_set(command.feature_set_id, principal)
        validate_pipeline_name(command.name)
        validate_code_ref(command.code_ref)
        if self._repository.pipeline_name_exists(feature_set.id, command.name.strip()):
            raise ConflictError("A feature pipeline with this name already exists.")

        pipeline = FeaturePipeline(
            id=uuid4(),
            feature_set_id=feature_set.id,
            name=command.name.strip(),
            source_dataset_id=command.source_dataset_id,
            code_ref=command.code_ref.strip(),
            schedule_cron=command.schedule_cron.strip() if command.schedule_cron else None,
            status=FeaturePipelineStatus.ACTIVE,
        )
        saved = self._repository.add_feature_pipeline(pipeline)
        if saved.source_dataset_id is not None:
            self._repository.add_lineage(
                FeatureLineage(
                    id=uuid4(),
                    feature_set_id=feature_set.id,
                    upstream_type="dataset",
                    upstream_id=str(saved.source_dataset_id),
                )
            )
        return saved

    def list_pipelines(self, feature_set_id: UUID, principal: Principal) -> list[FeaturePipeline]:
        self._require(principal, "feature_sets:read")
        feature_set = self._get_scoped_feature_set(feature_set_id, principal)
        return self._repository.list_feature_pipelines(feature_set.id)

    def materialize_pipeline(
        self,
        command: MaterializeFeaturePipelineCommand,
        principal: Principal,
    ) -> FeatureMaterialization:
        self._require(principal, "feature_materializations:create")
        pipeline = self._repository.get_feature_pipeline(command.pipeline_id)
        if pipeline is None:
            raise ResourceNotFoundError("Feature pipeline was not found.")
        feature_set = self._get_scoped_feature_set(pipeline.feature_set_id, principal)
        version = self._repository.latest_materialization_version(feature_set.id) + 1
        materialization_id = uuid4()
        run_id = self._orchestrator.trigger_materialization(pipeline, materialization_id)
        materialization = FeatureMaterialization(
            id=materialization_id,
            feature_set_id=feature_set.id,
            pipeline_id=pipeline.id,
            version=version,
            offline_uri=(
                f"s3://{self._artifact_bucket}/features/{feature_set.id}/"
                f"materializations/{materialization_id}"
            ),
            online_ref=f"feature-set:{feature_set.id}:v{version}",
            orchestrator_run_id=run_id,
            status=FeatureMaterializationStatus.REQUESTED,
        )
        return self._repository.add_materialization(materialization)

    def list_materializations(
        self,
        feature_set_id: UUID,
        principal: Principal,
    ) -> list[FeatureMaterialization]:
        self._require(principal, "feature_sets:read")
        feature_set = self._get_scoped_feature_set(feature_set_id, principal)
        return self._repository.list_materializations(feature_set.id)

    def get_lineage(self, feature_set_id: UUID, principal: Principal) -> list[FeatureLineage]:
        self._require(principal, "feature_sets:read")
        feature_set = self._get_scoped_feature_set(feature_set_id, principal)
        return self._repository.list_lineage(feature_set.id)

    def _get_scoped_feature_set(self, feature_set_id: UUID, principal: Principal) -> FeatureSet:
        feature_set = self._repository.get_feature_set(feature_set_id)
        if feature_set is None or str(feature_set.organization_id) != principal.organization_id:
            raise ResourceNotFoundError("Feature set was not found.")
        return feature_set

    def _require(self, principal: Principal, permission: str) -> None:
        if not principal.has(permission):
            raise PermissionDeniedError(
                "You do not have permission to manage feature store assets."
            )

    def _require_same_organization(self, organization_id: UUID, principal: Principal) -> None:
        if str(organization_id) != principal.organization_id:
            raise PermissionDeniedError("You cannot manage feature sets in another organization.")
