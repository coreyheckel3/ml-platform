from functools import lru_cache

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
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="FORGEML_MLFLOW_TRACKING_URI",
    )
    airflow_base_url: str = Field(
        default="http://localhost:8080",
        alias="FORGEML_AIRFLOW_BASE_URL",
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
    rate_limit_enabled: bool = Field(default=True, alias="FORGEML_RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=120, ge=1, alias="FORGEML_RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        alias="FORGEML_RATE_LIMIT_WINDOW_SECONDS",
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
