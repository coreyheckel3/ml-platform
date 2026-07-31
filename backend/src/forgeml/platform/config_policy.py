from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from forgeml.platform.config import Settings

PRODUCTION_LIKE_ENVIRONMENTS = frozenset({"prod", "production", "staging"})
INSECURE_JWT_SECRETS = frozenset(
    {
        "",
        "change-me-for-local-development",
        "changeme",
        "dev-secret",
        "secret",
    }
)
LOCAL_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})  # noqa: S104
MINIMUM_PRODUCTION_JWT_SECRET_LENGTH = 32


@dataclass(frozen=True)
class RuntimeConfigGuardrail:
    code: str
    setting: str
    description: str
    severity: str = "critical"


@dataclass(frozen=True)
class RuntimeConfigViolation:
    code: str
    setting: str
    message: str


class RuntimeConfigurationError(RuntimeError):
    def __init__(self, violations: tuple[RuntimeConfigViolation, ...]) -> None:
        self.violations = violations
        details = "; ".join(f"{violation.code}: {violation.message}" for violation in violations)
        super().__init__(f"Unsafe ForgeML runtime configuration: {details}")


RUNTIME_CONFIG_GUARDRAILS = (
    RuntimeConfigGuardrail(
        code="jwt_secret_not_default",
        setting="jwt_secret",
        description="JWT signing secret must not use a local development default.",
    ),
    RuntimeConfigGuardrail(
        code="jwt_secret_minimum_length",
        setting="jwt_secret",
        description="JWT signing secret must be at least 32 characters.",
    ),
    RuntimeConfigGuardrail(
        code="docs_disabled",
        setting="enable_docs",
        description="Interactive API documentation must be disabled in production-like runtimes.",
    ),
    RuntimeConfigGuardrail(
        code="rate_limit_enabled",
        setting="rate_limit_enabled",
        description="API rate limiting must be enabled in production-like runtimes.",
    ),
    RuntimeConfigGuardrail(
        code="cors_origins_non_empty",
        setting="cors_origins",
        description="CORS must list at least one explicit allowed origin.",
    ),
    RuntimeConfigGuardrail(
        code="cors_no_wildcard",
        setting="cors_origins",
        description="CORS must not allow wildcard origins with credentialed requests.",
    ),
    RuntimeConfigGuardrail(
        code="cors_no_localhost",
        setting="cors_origins",
        description="CORS origins must not point at localhost in production-like runtimes.",
    ),
    RuntimeConfigGuardrail(
        code="database_url_not_localhost",
        setting="database_url",
        description="Database URL must not point at a local host in production-like runtimes.",
    ),
    RuntimeConfigGuardrail(
        code="redis_url_not_localhost",
        setting="redis_url",
        description="Redis URL must not point at a local host in production-like runtimes.",
    ),
    RuntimeConfigGuardrail(
        code="object_storage_endpoint_not_localhost",
        setting="object_storage_endpoint",
        description=(
            "Object storage endpoint must not point at a local host in production-like runtimes."
        ),
    ),
    RuntimeConfigGuardrail(
        code="mlflow_tracking_uri_not_localhost",
        setting="mlflow_tracking_uri",
        description=(
            "MLflow tracking URI must not point at a local host in production-like runtimes."
        ),
    ),
    RuntimeConfigGuardrail(
        code="airflow_base_url_not_localhost",
        setting="airflow_base_url",
        description="Airflow base URL must not point at a local host in production-like runtimes.",
    ),
)


def is_production_like_environment(environment: str) -> bool:
    return environment.strip().lower() in PRODUCTION_LIKE_ENVIRONMENTS


def validate_runtime_config(settings: Settings) -> tuple[RuntimeConfigViolation, ...]:
    if not is_production_like_environment(settings.environment):
        return ()

    violations: list[RuntimeConfigViolation] = []
    jwt_secret = settings.jwt_secret.strip()
    if jwt_secret in INSECURE_JWT_SECRETS:
        violations.append(
            RuntimeConfigViolation(
                code="jwt_secret_not_default",
                setting="jwt_secret",
                message="FORGEML_JWT_SECRET must be set to a non-default secret.",
            )
        )
    if len(jwt_secret) < MINIMUM_PRODUCTION_JWT_SECRET_LENGTH:
        violations.append(
            RuntimeConfigViolation(
                code="jwt_secret_minimum_length",
                setting="jwt_secret",
                message=(
                    "FORGEML_JWT_SECRET must be at least "
                    f"{MINIMUM_PRODUCTION_JWT_SECRET_LENGTH} characters."
                ),
            )
        )
    if settings.enable_docs:
        violations.append(
            RuntimeConfigViolation(
                code="docs_disabled",
                setting="enable_docs",
                message="FastAPI docs and ReDoc must be disabled outside local development.",
            )
        )
    if not settings.rate_limit_enabled:
        violations.append(
            RuntimeConfigViolation(
                code="rate_limit_enabled",
                setting="rate_limit_enabled",
                message="API rate limiting must be enabled outside local development.",
            )
        )

    cors_origins = tuple(origin.strip() for origin in settings.cors_origins if origin.strip())
    if not cors_origins:
        violations.append(
            RuntimeConfigViolation(
                code="cors_origins_non_empty",
                setting="cors_origins",
                message="FORGEML_CORS_ORIGINS must include at least one explicit origin.",
            )
        )
    if "*" in cors_origins:
        violations.append(
            RuntimeConfigViolation(
                code="cors_no_wildcard",
                setting="cors_origins",
                message="FORGEML_CORS_ORIGINS must not include '*'.",
            )
        )
    if any(_is_local_url(origin) for origin in cors_origins):
        violations.append(
            RuntimeConfigViolation(
                code="cors_no_localhost",
                setting="cors_origins",
                message="FORGEML_CORS_ORIGINS must not include localhost origins.",
            )
        )

    endpoint_checks = (
        ("database_url_not_localhost", "database_url", settings.database_url),
        ("redis_url_not_localhost", "redis_url", settings.redis_url),
        (
            "object_storage_endpoint_not_localhost",
            "object_storage_endpoint",
            settings.object_storage_endpoint,
        ),
        ("mlflow_tracking_uri_not_localhost", "mlflow_tracking_uri", settings.mlflow_tracking_uri),
        ("airflow_base_url_not_localhost", "airflow_base_url", settings.airflow_base_url),
    )
    for code, setting, value in endpoint_checks:
        if _is_local_url(value):
            violations.append(
                RuntimeConfigViolation(
                    code=code,
                    setting=setting,
                    message=f"{setting} must not point at localhost.",
                )
            )

    return tuple(violations)


def assert_runtime_config_safe(settings: Settings) -> None:
    violations = validate_runtime_config(settings)
    if violations:
        raise RuntimeConfigurationError(violations)


def _is_local_url(value: str) -> bool:
    hostname = urlparse(value).hostname
    if hostname is None:
        return False
    normalized = hostname.strip("[]").lower()
    return normalized in LOCAL_HOSTNAMES or normalized.endswith(".localhost")
