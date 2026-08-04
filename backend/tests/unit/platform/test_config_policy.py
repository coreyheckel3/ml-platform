import pytest

from forgeml.platform.config import Settings
from forgeml.platform.config_policy import (
    RuntimeConfigurationError,
    assert_runtime_config_safe,
    is_production_like_environment,
    validate_runtime_config,
)


def test_local_runtime_allows_development_defaults() -> None:
    assert validate_runtime_config(Settings()) == ()


@pytest.mark.parametrize("environment", ["prod", "production", "staging"])
def test_production_like_environment_aliases_are_enforced(environment: str) -> None:
    assert is_production_like_environment(environment)


def test_production_runtime_rejects_insecure_defaults() -> None:
    violations = validate_runtime_config(Settings(environment="production"))
    violation_codes = {violation.code for violation in violations}

    assert {
        "jwt_secret_not_default",
        "jwt_secret_minimum_length",
        "docs_disabled",
        "readiness_checks_enabled",
        "cors_no_localhost",
        "database_url_not_localhost",
        "redis_url_not_localhost",
        "object_storage_endpoint_not_localhost",
        "mlflow_tracking_uri_not_localhost",
        "airflow_base_url_not_localhost",
    }.issubset(violation_codes)
    assert all(
        "change-me-for-local-development" not in violation.message for violation in violations
    )


def test_production_runtime_rejects_disabled_rate_limit() -> None:
    settings = _production_settings(rate_limit_enabled=False)

    violations = validate_runtime_config(settings)

    assert "rate_limit_enabled" in {violation.code for violation in violations}


def test_production_runtime_rejects_wildcard_cors() -> None:
    settings = _production_settings(cors_origins=["*"])

    violations = validate_runtime_config(settings)

    assert "cors_no_wildcard" in {violation.code for violation in violations}


def test_production_runtime_rejects_empty_cors() -> None:
    settings = _production_settings(cors_origins=[])

    violations = validate_runtime_config(settings)

    assert "cors_origins_non_empty" in {violation.code for violation in violations}


def test_production_runtime_accepts_hardened_settings() -> None:
    assert validate_runtime_config(_production_settings()) == ()


def test_runtime_config_assertion_raises_actionable_error() -> None:
    with pytest.raises(RuntimeConfigurationError) as exc_info:
        assert_runtime_config_safe(Settings(environment="production"))

    assert "Unsafe ForgeML runtime configuration" in str(exc_info.value)
    assert exc_info.value.violations


def _production_settings(**overrides: object) -> Settings:
    values = {
        "environment": "production",
        "database_url": "postgresql+psycopg://forgeml:forgeml@postgres.internal:5432/forgeml",
        "redis_url": "redis://redis.internal:6379/0",
        "object_storage_endpoint": "https://s3.us-east-1.amazonaws.com",
        "mlflow_tracking_uri": "https://mlflow.forgeml.internal",
        "airflow_base_url": "https://airflow.forgeml.internal",
        "jwt_secret": "production-grade-secret-material-32",
        "enable_docs": False,
        "cors_origins": ["https://app.forgeml.example"],
        "rate_limit_enabled": True,
        "readiness_checks_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)
