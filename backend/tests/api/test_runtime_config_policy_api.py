import pytest
from fastapi.testclient import TestClient

from forgeml.main import create_app
from forgeml.platform.config import Settings
from forgeml.platform.config_policy import RuntimeConfigurationError


def test_create_app_rejects_insecure_production_runtime() -> None:
    with pytest.raises(RuntimeConfigurationError):
        create_app(Settings(environment="production"))


def test_create_app_accepts_hardened_production_runtime_and_disables_docs() -> None:
    app = create_app(_production_settings())
    client = TestClient(app)

    live_response = client.get("/health/live")
    docs_response = client.get("/docs")

    assert live_response.status_code == 200
    assert docs_response.status_code == 404


def _production_settings() -> Settings:
    return Settings(
        environment="production",
        database_url="postgresql+psycopg://forgeml:forgeml@postgres.internal:5432/forgeml",
        redis_url="redis://redis.internal:6379/0",
        object_storage_endpoint="https://s3.us-east-1.amazonaws.com",
        mlflow_tracking_uri="https://mlflow.forgeml.internal",
        airflow_base_url="https://airflow.forgeml.internal",
        jwt_secret="production-grade-secret-material-32",
        enable_docs=False,
        cors_origins=["https://app.forgeml.example"],
        rate_limit_enabled=True,
        readiness_checks_enabled=True,
    )
