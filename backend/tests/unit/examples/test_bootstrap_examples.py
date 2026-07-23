from pathlib import Path

from scripts.examples.bootstrap_examples import (
    EXAMPLE_PROJECT_SLUG_PARAMETER,
    build_retraining_policy_payload,
    build_training_execution_report,
    dataset_file_metadata,
    ensure_model_version,
    ensure_succeeded_training_run,
    example_training_hyperparameters,
    load_catalog_entries,
    row_count,
)
from scripts.examples.run_local_training import TRAINERS


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
    assert payload["training_template"]["hyperparameters"][EXAMPLE_PROJECT_SLUG_PARAMETER] == (
        manifest.slug
    )
    assert payload["approval_required"] is True


def test_example_training_helpers_record_generated_execution_metadata(tmp_path: Path) -> None:
    manifest = next(
        manifest
        for manifest, _project_root in load_catalog_entries(Path("examples/catalog.json"))
        if manifest.slug == "semantic-search"
    )
    summary = TRAINERS[manifest.slug](output_dir=tmp_path / manifest.slug)
    report = build_training_execution_report(summary, manifest)

    assert example_training_hyperparameters(manifest)[EXAMPLE_PROJECT_SLUG_PARAMETER] == (
        "semantic-search"
    )
    assert report["example_project_slug"] == "semantic-search"
    assert report["training_execution"]["schema_version"] == (
        "forgeml.training_execution_result.v1"
    )
    assert {artifact["name"] for artifact in report["training_execution"]["artifacts"]} == {
        "model",
        "evaluation",
        "summary",
    }


def test_bootstrap_training_run_records_generated_metrics(tmp_path: Path) -> None:
    manifest, project_root = next(
        entry
        for entry in load_catalog_entries(Path("examples/catalog.json"))
        if entry[0].slug == "fraud-detection"
    )
    client = FakeTrainingClient()

    training_run = ensure_succeeded_training_run(
        client,
        project_id="project-1",
        experiment_id="experiment-1",
        dataset_version_id="dataset-version-1",
        feature_set_id="feature-set-1",
        manifest=manifest,
        project_root=project_root,
        artifact_root=tmp_path,
    )

    assert training_run["status"] == "succeeded"
    assert client.started_payload["hyperparameters"][EXAMPLE_PROJECT_SLUG_PARAMETER] == (
        "fraud-detection"
    )
    assert client.recorded_payload["metrics"]["auc"] == 1.0
    assert client.recorded_payload["evaluation_report"]["training_execution"][
        "schema_version"
    ] == "forgeml.training_execution_result.v1"


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


class FakeTrainingClient:
    def __init__(self) -> None:
        self.started_payload: dict[str, object] = {}
        self.recorded_payload: dict[str, object] = {}

    def list_training_runs(self, _project_id: str) -> dict[str, object]:
        return {"items": []}

    def start_training_run(self, _project_id: str, payload: dict[str, object]) -> dict[str, str]:
        self.started_payload = payload
        return {"id": "training-run-1"}

    def record_training_result(
        self,
        training_run_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        self.recorded_payload = payload
        return {
            "id": training_run_id,
            "status": payload["status"],
            "metrics": payload["metrics"],
            "evaluation_report": payload["evaluation_report"],
        }
