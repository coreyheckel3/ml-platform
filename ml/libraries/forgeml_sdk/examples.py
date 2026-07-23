from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ExampleSchemaField(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dtype: str = Field(min_length=1, max_length=64)
    nullable: bool


class ExampleDataset(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    source_type: str
    data_path: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    schema_fields: list[ExampleSchemaField] = Field(min_length=1)


class ExampleFeatureDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dtype: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=1000)
    nullable: bool = False
    constraints: dict[str, object] = Field(default_factory=dict)


class ExampleFeaturePipeline(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    code_ref: str = Field(min_length=3, max_length=512)
    schedule_cron: str | None = Field(default=None, max_length=120)


class ExampleFeatureSet(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    entity_key: str = Field(min_length=1, max_length=120)
    definitions: list[ExampleFeatureDefinition] = Field(min_length=1)
    pipeline: ExampleFeaturePipeline


class ExampleExperiment(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)


class ExampleTrainingRun(BaseModel):
    run_name: str = Field(min_length=3, max_length=160)
    algorithm: str = Field(min_length=2, max_length=120)
    model_type: str = Field(min_length=2, max_length=64)
    objective_metric_name: str = Field(min_length=1, max_length=120)
    hyperparameters: dict[str, object] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(min_length=1)
    evaluation_report_path: str = Field(min_length=1)
    artifact_uri: str = Field(min_length=3, max_length=2048)

    @field_validator("metrics")
    @classmethod
    def objective_metric_must_exist(cls, metrics: dict[str, float], info) -> dict[str, float]:
        objective_metric_name = info.data.get("objective_metric_name")
        if objective_metric_name and objective_metric_name not in metrics:
            raise ValueError("training metrics must include objective metric")
        return metrics


class ExampleModel(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    task_type: str = Field(min_length=2, max_length=64)
    model_format: str = Field(min_length=2, max_length=64)
    signature: dict[str, object]
    approval_comment: str = Field(default="", max_length=2000)

    @field_validator("signature")
    @classmethod
    def signature_has_io(cls, signature: dict[str, object]) -> dict[str, object]:
        if "inputs" not in signature or "outputs" not in signature:
            raise ValueError("model signature requires inputs and outputs")
        return signature


class ExampleHealthCheck(BaseModel):
    status: str
    latency_ms: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    details: dict[str, object] = Field(default_factory=dict)


class ExampleInferenceEndpoint(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    route_path: str = Field(min_length=1, max_length=160)


class ExamplePredictionRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, object] = Field(default_factory=dict)


class ExampleMetricSnapshot(BaseModel):
    window_seconds: int = Field(gt=0, le=86400)
    prediction_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    p50_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)


class ExampleDeployment(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    environment: str = Field(min_length=3, max_length=32)
    serving_image: str = Field(min_length=3, max_length=512)
    runtime_config: dict[str, object] = Field(default_factory=dict)
    health_check: ExampleHealthCheck
    inference_endpoint: ExampleInferenceEndpoint
    sample_requests: list[ExamplePredictionRequest] = Field(min_length=1)
    metric_snapshot: ExampleMetricSnapshot


class ExampleDriftReport(BaseModel):
    window_seconds: int = Field(gt=0, le=86400)
    drift_threshold: float = Field(ge=0, le=1)
    sample_limit: int = Field(gt=0, le=10000)


class ExampleDrift(BaseModel):
    profile_name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    baseline_profile: dict[str, object] = Field(min_length=1)
    report: ExampleDriftReport


class ExampleAlert(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    severity: str
    metric: str
    operator: str
    threshold: float
    window_seconds: int = Field(gt=0, le=86400)
    enabled: bool = True


class ExampleRetrainingTemplate(BaseModel):
    run_name_prefix: str = Field(min_length=3, max_length=96)
    algorithm: str = Field(min_length=2, max_length=120)
    model_type: str = Field(min_length=2, max_length=64)
    objective_metric_name: str = Field(min_length=1, max_length=120)
    hyperparameters: dict[str, object] = Field(default_factory=dict)


class ExampleRetraining(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    trigger_type: str
    trigger_config: dict[str, object] = Field(default_factory=dict)
    training_template: ExampleRetrainingTemplate
    cooldown_seconds: int = Field(ge=0, le=604800)
    max_runs_per_day: int = Field(ge=1, le=50)
    approval_required: bool = True
    enabled: bool = True


class ExampleProjectManifest(BaseModel):
    schema_version: str
    slug: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    owner_persona: str = Field(min_length=3, max_length=120)
    dataset: ExampleDataset
    feature_set: ExampleFeatureSet
    experiment: ExampleExperiment
    training_run: ExampleTrainingRun
    model: ExampleModel
    deployment: ExampleDeployment
    drift: ExampleDrift
    alert: ExampleAlert
    retraining: ExampleRetraining

    @field_validator("schema_version")
    @classmethod
    def schema_version_is_supported(cls, schema_version: str) -> str:
        if schema_version != "forgeml.example_project.v1":
            raise ValueError("unsupported example project schema version")
        return schema_version


def load_example_manifest(path: Path) -> ExampleProjectManifest:
    return ExampleProjectManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_example_catalog(path: Path) -> list[ExampleProjectManifest]:
    catalog = ExampleCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    return [load_example_manifest(path.parent / project_path) for project_path in catalog.projects]


class ExampleCatalog(BaseModel):
    schema_version: str
    projects: list[str] = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def catalog_schema_version_is_supported(cls, schema_version: str) -> str:
        if schema_version != "forgeml.example_catalog.v1":
            raise ValueError("unsupported example catalog schema version")
        return schema_version
