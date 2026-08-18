import json
from pathlib import Path

from scripts.ci.check_deployment_runtime_contract import (
    build_deployment_runtime_contract,
    check_deployment_runtime_contract,
    serialize_deployment_runtime_contract,
    validate_deployment_runtime_definition,
    write_deployment_runtime_contract,
)


def test_deployment_runtime_contract_serialization_is_deterministic() -> None:
    contract = build_deployment_runtime_contract()

    assert serialize_deployment_runtime_contract(contract) == (
        serialize_deployment_runtime_contract(contract)
    )
    assert json.loads(serialize_deployment_runtime_contract(contract)) == contract


def test_deployment_runtime_contract_write_and_check_round_trip(tmp_path: Path) -> None:
    contract_path = tmp_path / "deployment-serving.v1.json"
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text(
        "run: python scripts/ci/check_deployment_runtime_contract.py\n",
        encoding="utf-8",
    )

    write_deployment_runtime_contract(contract_path)

    assert check_deployment_runtime_contract(contract_path, ci_path=ci_path)[0]


def test_deployment_runtime_definition_validates_required_fragments() -> None:
    assert validate_deployment_runtime_definition(Path(".")) == ()


def test_checked_in_deployment_runtime_contract_matches_builder() -> None:
    contract = json.loads(
        Path("contracts/runtime/deployment-serving.v1.json").read_text(encoding="utf-8")
    )

    assert contract == build_deployment_runtime_contract()
    assert contract["adapter_boundary"]["inference_runtime_router"] == "RoutedInferenceRuntime"
    assert "conversational-movie-recommender" in contract["adapter_boundary"][
        "external_adapters"
    ]
    assert "POST /api/v1/inference-endpoints/{endpoint_id}/predict" in contract[
        "api_surface"
    ]
    assert "GET /api/v1/inference-endpoints/{endpoint_id}/health-probe" in contract[
        "api_surface"
    ]
    assert "conversational-movie-recommender" in contract["external_adapter_semantics"]
