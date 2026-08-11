from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local", alias="FORGEML_ENV")
    service_name: str = "forgeml-api"
    database_url: str = Field(
        default="postgresql+psycopg://forgeml:forgeml@localhost:5432/forgeml",
        alias="FORGEML_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="FORGEML_REDIS_URL")
    object_storage_endpoint: str = Field(
        default="http://localhost:9000",
        alias="FORGEML_OBJECT_STORAGE_ENDPOINT",
    )
    object_storage_bucket: str = Field(
        default="forgeml-artifacts",
        alias="FORGEML_OBJECT_STORAGE_BUCKET",
    )
    artifact_manifest_local_root: Path = Field(
        default=Path("artifacts/manifests"),
        alias="FORGEML_ARTIFACT_MANIFEST_LOCAL_ROOT",
    )
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="FORGEML_MLFLOW_TRACKING_URI",
    )
    mlflow_sync_enabled: bool = Field(
        default=False,
        alias="FORGEML_MLFLOW_SYNC_ENABLED",
    )
    mlflow_experiment_prefix: str = Field(
        default="forgeml",
        alias="FORGEML_MLFLOW_EXPERIMENT_PREFIX",
    )
    mlflow_http_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        alias="FORGEML_MLFLOW_HTTP_TIMEOUT_SECONDS",
    )
    local_training_artifact_root: Path = Field(
        default=Path("artifacts/training-runs"),
        alias="FORGEML_LOCAL_TRAINING_ARTIFACT_ROOT",
    )
    training_worker_max_attempts: int = Field(
        default=3,
        ge=1,
        le=100,
        alias="FORGEML_TRAINING_WORKER_MAX_ATTEMPTS",
    )
    training_worker_lease_seconds: int = Field(
        default=900,
        ge=1,
        alias="FORGEML_TRAINING_WORKER_LEASE_SECONDS",
    )
    training_worker_retry_backoff_seconds: int = Field(
        default=60,
        ge=0,
        alias="FORGEML_TRAINING_WORKER_RETRY_BACKOFF_SECONDS",
    )
    training_worker_max_retry_backoff_seconds: int = Field(
        default=1_800,
        ge=0,
        alias="FORGEML_TRAINING_WORKER_MAX_RETRY_BACKOFF_SECONDS",
    )
    airflow_base_url: str = Field(
        default="http://localhost:8080",
        alias="FORGEML_AIRFLOW_BASE_URL",
    )
    airflow_orchestration_enabled: bool = Field(
        default=False,
        alias="FORGEML_AIRFLOW_ORCHESTRATION_ENABLED",
    )
    airflow_training_dag_id: str = Field(
        default="forgeml_training_pipeline",
        alias="FORGEML_AIRFLOW_TRAINING_DAG_ID",
    )
    airflow_username: str | None = Field(
        default=None,
        alias="FORGEML_AIRFLOW_USERNAME",
    )
    airflow_password: str | None = Field(
        default=None,
        alias="FORGEML_AIRFLOW_PASSWORD",
    )
    airflow_http_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        alias="FORGEML_AIRFLOW_HTTP_TIMEOUT_SECONDS",
    )
    jwt_secret: str = Field(
        default="change-me-for-local-development",
        alias="FORGEML_JWT_SECRET",
    )
    jwt_issuer: str = "forgeml"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    enable_docs: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="FORGEML_CORS_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="FORGEML_LOG_LEVEL")
    structured_logging_enabled: bool = Field(
        default=True,
        alias="FORGEML_STRUCTURED_LOGGING_ENABLED",
    )
    request_logging_enabled: bool = Field(
        default=True,
        alias="FORGEML_REQUEST_LOGGING_ENABLED",
    )
    rate_limit_enabled: bool = Field(default=True, alias="FORGEML_RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=120, ge=1, alias="FORGEML_RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        alias="FORGEML_RATE_LIMIT_WINDOW_SECONDS",
    )
    readiness_checks_enabled: bool = Field(
        default=False,
        alias="FORGEML_READINESS_CHECKS_ENABLED",
    )
    readiness_timeout_seconds: float = Field(
        default=1.0,
        gt=0,
        alias="FORGEML_READINESS_TIMEOUT_SECONDS",
    )
    rate_limit_exempt_paths: list[str] = Field(
        default_factory=lambda: [
            "/health/live",
            "/health/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
        alias="FORGEML_RATE_LIMIT_EXEMPT_PATHS",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
