from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend/src"
for import_path in (REPO_ROOT, BACKEND_SRC):
    import_path_value = str(import_path)
    if import_path_value not in sys.path:
        sys.path.insert(0, import_path_value)

from forgeml.modules.inference.infrastructure.runtime import (  # noqa: E402
    EXTERNAL_MOVIE_RECOMMENDER_ADAPTER,
    EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION,
)
from forgeml.platform.serving import SERVING_RUNTIME_SCHEMA_VERSION  # noqa: E402

DEPLOYMENT_RUNTIME_CONTRACT_SCHEMA_VERSION = "forgeml.deployment_runtime_contract.v1"
DEFAULT_OUTPUT_PATH = Path("contracts/runtime/deployment-serving.v1.json")
DEFAULT_CI_PATH = Path(".github/workflows/ci.yml")


def build_deployment_runtime_contract() -> dict[str, Any]:
    return {
        "schema_version": DEPLOYMENT_RUNTIME_CONTRACT_SCHEMA_VERSION,
        "serving_runtime_schema_version": SERVING_RUNTIME_SCHEMA_VERSION,
        "generated_from": [
            "forgeml.platform.serving.runtime",
            "forgeml.platform.config",
            "forgeml.modules.deployments.infrastructure.orchestrator",
            "forgeml.modules.deployments.application.services",
            "forgeml.modules.inference.application.services",
            "forgeml.modules.inference.domain.policies",
            "forgeml.modules.inference.infrastructure.runtime",
        ],
        "adapter_boundary": {
            "gateway_protocol": "ServingRuntimeGateway",
            "local_gateway": "InMemoryServingRuntimeGateway",
            "deployment_orchestrator": "LocalDeploymentOrchestrator",
            "inference_runtime_router": "RoutedInferenceRuntime",
            "external_serving_schema_version": EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION,
            "external_adapters": [EXTERNAL_MOVIE_RECOMMENDER_ADAPTER],
            "deployment_operations": [
                "deploy_revision",
                "apply_traffic_plan",
                "rollback",
                "probe_revision",
            ],
        },
        "api_surface": [
            "POST /api/v1/deployment-revisions/{revision_id}/health-probe",
            "POST /api/v1/deployments/{deployment_id}/canary-simulation",
            "POST /api/v1/inference-endpoints/{endpoint_id}/predict",
            "GET /api/v1/inference-endpoints/{endpoint_id}/health-probe",
        ],
        "traffic_semantics": {
            "full_promotion": (
                "target revision receives 100 percent traffic and active peers drain to 0"
            ),
            "canary": (
                "target revision receives 1-99 percent traffic and a healthy baseline "
                "receives the remainder"
            ),
            "rollback": (
                "target healthy revision receives 100 percent traffic and all active "
                "non-target revisions are drained"
            ),
            "routing": (
                "inference selects a servable deployment revision by deterministic "
                "request-id weighted routing"
            ),
        },
        "health_probe_semantics": {
            "deployment_probe": "serving runtime probe records a normal deployment health check",
            "inference_probe": (
                "endpoint probe resolves the same runtime revision path used by prediction"
            ),
            "external_adapter_probe": (
                "external movie recommender adapter maps upstream /health to serving "
                "health and reports unhealthy on transport failures"
            ),
        },
        "external_adapter_semantics": {
            EXTERNAL_MOVIE_RECOMMENDER_ADAPTER: {
                "selector": "deployment revision runtime_config.serving_adapter",
                "default_base_url_setting": (
                    "FORGEML_EXTERNAL_SERVING_MOVIE_RECOMMENDER_BASE_URL"
                ),
                "request_contract": (
                    "ForgeML accepts message/text/query plus optional user and history "
                    "fields, then calls POST /api/recommend on the external service"
                ),
                "response_contract": (
                    "ForgeML records normalized recommendations, parsed query, trace, "
                    "model artifact URI, model format, and model version provenance"
                ),
            }
        },
        "quality_gates": [
            "python scripts/ci/check_deployment_runtime_contract.py",
            "backend/tests/unit/platform/test_serving_runtime.py",
            "backend/tests/unit/deployments/test_deployment_service.py",
            "backend/tests/unit/inference/test_inference_serving_runtime.py",
            "backend/tests/unit/inference/test_inference_service.py",
            "backend/tests/api/test_deployments_api.py",
            "backend/tests/api/test_inference_api.py",
        ],
    }


def serialize_deployment_runtime_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_deployment_runtime_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_deployment_runtime_contract(build_deployment_runtime_contract()),
        encoding="utf-8",
    )


def check_deployment_runtime_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    ci_path: Path = DEFAULT_CI_PATH,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    findings = list(validate_deployment_runtime_definition(repo_root))
    if not output_path.is_file():
        findings.append(f"Deployment runtime contract does not exist: {output_path}")
    else:
        expected = serialize_deployment_runtime_contract(
            build_deployment_runtime_contract()
        )
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(f"Deployment runtime contract is stale: {output_path}")

    if not ci_path.is_file():
        findings.append(f"CI workflow does not exist: {ci_path}")
    else:
        ci_source = ci_path.read_text(encoding="utf-8")
        if "python scripts/ci/check_deployment_runtime_contract.py" not in ci_source:
            findings.append("Deployment runtime contract checker is not wired into CI.")

    if findings:
        return False, "Deployment runtime contract violations: " + "; ".join(findings)
    return True, f"Deployment runtime contract is current: {output_path}"


def validate_deployment_runtime_definition(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    required_files = [
        "backend/src/forgeml/platform/serving/runtime.py",
        "backend/src/forgeml/platform/serving/__init__.py",
        "backend/src/forgeml/platform/config.py",
        "backend/src/forgeml/modules/deployments/infrastructure/orchestrator.py",
        "backend/src/forgeml/modules/deployments/application/services.py",
        "backend/src/forgeml/modules/deployments/api/routes.py",
        "backend/src/forgeml/modules/deployments/api/schemas.py",
        "backend/src/forgeml/modules/inference/application/services.py",
        "backend/src/forgeml/modules/inference/domain/entities.py",
        "backend/src/forgeml/modules/inference/domain/policies.py",
        "backend/src/forgeml/modules/inference/infrastructure/runtime.py",
        "backend/src/forgeml/modules/inference/api/routes.py",
        "backend/src/forgeml/modules/inference/api/schemas.py",
        "backend/tests/unit/platform/test_serving_runtime.py",
        "backend/tests/unit/deployments/test_deployment_service.py",
        "backend/tests/unit/inference/test_inference_serving_runtime.py",
        "backend/tests/unit/inference/test_inference_service.py",
        "backend/tests/api/test_deployments_api.py",
        "backend/tests/api/test_inference_api.py",
    ]
    findings = [
        f"Missing deployment runtime source file: {path}"
        for path in required_files
        if not (repo_root / path).is_file()
    ]
    if findings:
        return tuple(findings)

    sources = {
        path: (repo_root / path).read_text(encoding="utf-8") for path in required_files
    }
    contract = serialize_deployment_runtime_contract(build_deployment_runtime_contract())
    required_fragments = (
        ("ServingRuntimeGateway", sources["backend/src/forgeml/platform/serving/runtime.py"]),
        (
            "InMemoryServingRuntimeGateway",
            sources["backend/src/forgeml/platform/serving/runtime.py"],
        ),
        (
            "ServingTrafficPlanRequest",
            sources["backend/src/forgeml/platform/serving/runtime.py"],
        ),
        (
            "probe_revision",
            sources["backend/src/forgeml/modules/deployments/infrastructure/orchestrator.py"],
        ),
        (
            "simulate_canary_traffic",
            sources["backend/src/forgeml/modules/deployments/application/services.py"],
        ),
        (
            "validate_traffic_target_status",
            sources["backend/src/forgeml/modules/deployments/application/services.py"],
        ),
        (
            "probe_revision_health",
            sources["backend/src/forgeml/modules/deployments/api/routes.py"],
        ),
        (
            "canary-simulation",
            sources["backend/src/forgeml/modules/deployments/api/routes.py"],
        ),
        (
            "select_serving_reference_for_request",
            sources["backend/src/forgeml/modules/inference/domain/policies.py"],
        ),
        (
            "build_local_inference_runtime",
            sources["backend/src/forgeml/modules/inference/api/routes.py"],
        ),
        (
            "list_deployment_serving_references",
            sources["backend/src/forgeml/modules/inference/application/services.py"],
        ),
        (
            "RoutedInferenceRuntime",
            sources["backend/src/forgeml/modules/inference/infrastructure/runtime.py"],
        ),
        (
            "ExternalMovieRecommenderRuntime",
            sources["backend/src/forgeml/modules/inference/infrastructure/runtime.py"],
        ),
        (
            "EXTERNAL_MOVIE_RECOMMENDER_SERVING_SCHEMA_VERSION",
            sources["backend/src/forgeml/modules/inference/infrastructure/runtime.py"],
        ),
        (
            "FORGEML_EXTERNAL_SERVING_MOVIE_RECOMMENDER_BASE_URL",
            sources["backend/src/forgeml/platform/config.py"],
        ),
        (
            "health_probe",
            sources["backend/src/forgeml/modules/inference/infrastructure/runtime.py"],
        ),
        (
            "model_artifact_uri",
            sources["backend/src/forgeml/modules/inference/domain/entities.py"],
        ),
        (
            "revision_runtime_config",
            sources["backend/src/forgeml/modules/inference/domain/entities.py"],
        ),
        (
            "/health-probe",
            sources["backend/src/forgeml/modules/inference/api/routes.py"],
        ),
        (
            "/predict",
            sources["backend/src/forgeml/modules/inference/api/routes.py"],
        ),
        ("deterministic request-id weighted routing", contract),
    )
    missing_fragments = sorted(
        fragment for fragment, source in required_fragments if fragment not in source
    )
    if missing_fragments:
        findings.append(f"Missing deployment runtime fragments: {missing_fragments}")

    runtime_contract = build_deployment_runtime_contract()
    if runtime_contract["serving_runtime_schema_version"] != SERVING_RUNTIME_SCHEMA_VERSION:
        findings.append("Serving runtime schema version is inconsistent.")
    if len(runtime_contract["api_surface"]) < 4:
        findings.append(
            "Deployment runtime contract must include probe, predict, and canary API coverage."
        )
    if "rollback" not in runtime_contract["traffic_semantics"]:
        findings.append("Deployment runtime contract must include rollback semantics.")
    if (
        EXTERNAL_MOVIE_RECOMMENDER_ADAPTER
        not in runtime_contract["adapter_boundary"]["external_adapters"]
    ):
        findings.append("Deployment runtime contract must include external recommender serving.")

    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ForgeML deployment runtime contract."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in deployment runtime contract.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in deployment runtime contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_deployment_runtime_contract(args.output)
        print(f"Wrote deployment runtime contract: {args.output}")
        return 0

    passed, detail = check_deployment_runtime_contract(args.output)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
