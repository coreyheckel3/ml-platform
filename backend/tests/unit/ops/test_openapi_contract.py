import json
from pathlib import Path

from scripts.ci.generate_openapi_contract import (
    check_openapi_contract,
    generate_openapi_schema,
    serialize_openapi_schema,
    write_openapi_contract,
)


def test_openapi_contract_serialization_is_deterministic() -> None:
    schema = {
        "paths": {"/health/live": {"get": {"tags": ["health"]}}},
        "openapi": "3.1.0",
    }

    assert serialize_openapi_schema(schema).splitlines()[0] == "{"
    assert serialize_openapi_schema(schema) == serialize_openapi_schema(schema)
    assert json.loads(serialize_openapi_schema(schema)) == schema


def test_openapi_contract_check_detects_stale_files(tmp_path: Path) -> None:
    contract_path = tmp_path / "forgeml.openapi.json"

    assert not check_openapi_contract(contract_path)

    contract_path.write_text("{}", encoding="utf-8")

    assert not check_openapi_contract(contract_path)


def test_openapi_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "forgeml.openapi.json"

    write_openapi_contract(contract_path)

    assert check_openapi_contract(contract_path)


def test_checked_in_openapi_contract_matches_application_schema() -> None:
    contract = json.loads(
        Path("contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )

    assert contract == generate_openapi_schema()


def test_checked_in_openapi_contract_covers_core_platform_groups() -> None:
    contract = json.loads(
        Path("contracts/openapi/forgeml.v1.openapi.json").read_text(encoding="utf-8")
    )
    paths = set(contract["paths"])

    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/projects" in paths
    assert "/api/v1/projects/{project_id}/datasets" in paths
    assert "/api/v1/projects/{project_id}/training-runs" in paths
    assert "/api/v1/training-runs/{training_run_id}/orchestration-status" in paths
    assert "/api/v1/models/{model_id}/versions/promote-training-run" in paths
    assert "/api/v1/deployments/{deployment_id}/canary-simulation" in paths
    assert "/api/v1/deployment-revisions/{revision_id}/health-probe" in paths
    assert "/api/v1/inference-endpoints/{endpoint_id}/predict" in paths
    assert "/api/v1/inference-endpoints/{endpoint_id}/health-probe" in paths
    assert "/api/v1/projects/{project_id}/drift-reports" in paths
    assert "/api/v1/retraining-policies/{policy_id}/trigger" in paths
