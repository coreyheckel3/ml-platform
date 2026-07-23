from pydantic import BaseModel, Field


class CreateFeatureSetRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    entity_key: str = Field(min_length=1, max_length=120)


class FeatureSetResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    name: str
    slug: str
    description: str
    entity_key: str
    status: str


class FeatureSetListResponse(BaseModel):
    items: list[FeatureSetResponse]
    next_cursor: str | None = None


class FeatureDefinitionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dtype: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=1000)
    nullable: bool = False
    constraints: dict[str, object] = Field(default_factory=dict)


class RegisterFeatureDefinitionsRequest(BaseModel):
    definitions: list[FeatureDefinitionRequest] = Field(min_length=1, max_length=500)


class FeatureDefinitionResponse(BaseModel):
    id: str
    feature_set_id: str
    name: str
    dtype: str
    description: str
    nullable: bool
    constraints: dict[str, object]


class FeatureDefinitionListResponse(BaseModel):
    items: list[FeatureDefinitionResponse]
    next_cursor: str | None = None


class RegisterFeaturePipelineRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    source_dataset_id: str | None = None
    code_ref: str = Field(min_length=3, max_length=512)
    schedule_cron: str | None = Field(default=None, max_length=120)


class FeaturePipelineResponse(BaseModel):
    id: str
    feature_set_id: str
    name: str
    source_dataset_id: str | None
    code_ref: str
    schedule_cron: str | None
    status: str


class FeaturePipelineListResponse(BaseModel):
    items: list[FeaturePipelineResponse]
    next_cursor: str | None = None


class FeatureMaterializationResponse(BaseModel):
    id: str
    feature_set_id: str
    pipeline_id: str
    version: int
    offline_uri: str
    online_ref: str | None
    orchestrator_run_id: str
    status: str


class FeatureMaterializationListResponse(BaseModel):
    items: list[FeatureMaterializationResponse]
    next_cursor: str | None = None


class FeatureLineageResponse(BaseModel):
    id: str
    feature_set_id: str
    upstream_type: str
    upstream_id: str


class FeatureLineageListResponse(BaseModel):
    items: list[FeatureLineageResponse]
    next_cursor: str | None = None

