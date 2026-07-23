from pathlib import Path

from scripts.examples.bootstrap_examples import (
    build_retraining_policy_payload,
    dataset_file_metadata,
    ensure_model_version,
    load_catalog_entries,
    row_count,
)


def test_bootstrap_loader_preserves_manifest_project_roots() -> None:
    entries = load_catalog_entries(Path("examples/catalog.json"))

    project_roots = {manifest.slug: project_root.name for manifest, project_root in entries}

    assert project_roots == {
        "movie-recommendation": "movie_recommendation",
        "semantic-search": "semantic_search",
        "fraud-detection": "fraud_detection",
    }


def test_dataset_metadata_counts_supported_example_formats() -> None:
    movie_data = Path("examples/projects/movie_recommendation/data/ratings.csv")
    search_data = Path("examples/projects/semantic_search/data/documents.jsonl")

    assert row_count(movie_data) == 8
    assert row_count(search_data) == 6
    assert dataset_file_metadata(movie_data)["row_count"] == 8
    assert dataset_file_metadata(search_data)["row_count"] == 6


def test_retraining_policy_payload_injects_runtime_dependencies() -> None:
    manifest = load_catalog_entries(Path("examples/catalog.json"))[0][0]

    payload = build_retraining_policy_payload(
        manifest,
        deployment_id="deployment-1",
        experiment_id="experiment-1",
        dataset_version_id="dataset-version-1",
        feature_set_id="feature-set-1",
    )

    assert payload["deployment_id"] == "deployment-1"
    assert payload["training_template"]["experiment_id"] == "experiment-1"
    assert payload["training_template"]["dataset_version_id"] == "dataset-version-1"
    assert payload["training_template"]["feature_set_id"] == "feature-set-1"
    assert payload["approval_required"] is True


def test_model_version_approval_returns_refreshed_model_version() -> None:
    manifest = load_catalog_entries(Path("examples/catalog.json"))[0][0]
    client = FakeModelRegistryClient()

    model_version = ensure_model_version(
        client,
        model_id="registered-model-1",
        training_run_id="training-run-1",
        manifest=manifest,
    )

    assert model_version["id"] == "model-version-1"
    assert model_version["status"] == "approved"
    assert client.requested_version_id == "model-version-1"
    assert client.reviewed_version_id == "model-version-1"


class FakeModelRegistryClient:
    def __init__(self) -> None:
        self.requested_version_id: str | None = None
        self.reviewed_version_id: str | None = None

    def list_model_versions(self, _model_id: str) -> dict[str, object]:
        return {"items": []}

    def register_model_version(
        self,
        _model_id: str,
        _payload: dict[str, object],
    ) -> dict[str, object]:
        return {"id": "model-version-1", "status": "candidate"}

    def request_model_approval(
        self,
        version_id: str,
        _payload: dict[str, object],
    ) -> dict[str, object]:
        self.requested_version_id = version_id
        return {"id": "approval-1", "model_version_id": version_id, "status": "pending"}

    def review_model_version(
        self,
        version_id: str,
        _payload: dict[str, object],
    ) -> dict[str, object]:
        self.reviewed_version_id = version_id
        return {"id": "approval-1", "model_version_id": version_id, "status": "approved"}

    def get_model_version(self, version_id: str) -> dict[str, object]:
        return {"id": version_id, "status": "approved"}
