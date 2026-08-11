from pydantic import BaseModel, Field


class StartTrainingRunRequest(BaseModel):
    experiment_id: str
    run_name: str = Field(min_length=3, max_length=160)
    dataset_version_id: str | None = None
    feature_set_id: str | None = None
    algorithm: str = Field(min_length=2, max_length=120)
    model_type: str = Field(min_length=2, max_length=64)
    objective_metric_name: str = Field(min_length=1, max_length=120)
    hyperparameters: dict[str, object] = Field(default_factory=dict)


class TrainingRunResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    experiment_id: str
    experiment_run_id: str
    dataset_version_id: str | None
    feature_set_id: str | None
    algorithm: str
    model_type: str
    objective_metric_name: str
    hyperparameters: dict[str, object]
    status: str
    requested_by: str
    artifact_uri: str
    orchestrator_run_id: str
    metrics: dict[str, float]
    error_message: str | None
    attempt_count: int
    max_attempts: int
    worker_id: str | None
    lease_expires_at: str | None
    last_heartbeat_at: str | None
    queued_at: str | None
    started_at: str | None
    completed_at: str | None
    next_retry_at: str | None


class TrainingRunListResponse(BaseModel):
    items: list[TrainingRunResponse]
    next_cursor: str | None = None


class RecordTrainingResultRequest(BaseModel):
    status: str = Field(pattern="^(succeeded|failed|canceled)$")
    metrics: dict[str, float] = Field(default_factory=dict)
    evaluation_report: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = Field(default=None, max_length=2000)


class TrainingRunEventResponse(BaseModel):
    id: str
    training_run_id: str
    event_type: str
    message: str
    metadata: dict[str, object]


class TrainingRunEventListResponse(BaseModel):
    items: list[TrainingRunEventResponse]
    next_cursor: str | None = None


class TrainingRunLogResponse(BaseModel):
    id: str
    training_run_id: str
    sequence: int
    level: str
    logger: str
    message: str
    metadata: dict[str, object]
    created_at: str | None


class TrainingRunLogListResponse(BaseModel):
    items: list[TrainingRunLogResponse]
    next_cursor: str | None = None


class TrainingOrchestrationStatusResponse(BaseModel):
    training_run_id: str
    orchestrator_run_id: str
    orchestrator: str
    external_status: str
    mapped_training_status: str | None
    is_terminal: bool
    external_url: str | None
    metadata: dict[str, object]
    observed_at: str | None
