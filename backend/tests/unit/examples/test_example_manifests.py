from pathlib import Path

from ml.libraries.forgeml_sdk.examples import load_example_catalog
from scripts.examples.bootstrap_examples import dataset_file_metadata, load_catalog_entries


def test_example_catalog_loads_reference_projects() -> None:
    manifests = load_example_catalog(Path("examples/catalog.json"))

    assert {manifest.slug for manifest in manifests} == {
        "movie-recommendation",
        "semantic-search",
        "fraud-detection",
    }
    assert {manifest.model.task_type for manifest in manifests} == {
        "recommendation",
        "retrieval",
        "classification",
    }


def test_example_manifests_have_complete_platform_lifecycle() -> None:
    entries = load_catalog_entries(Path("examples/catalog.json"))

    for manifest, project_root in entries:
        data_path = project_root / manifest.dataset.data_path
        evaluation_path = project_root / manifest.training_run.evaluation_report_path
        schema_names = [field.name for field in manifest.dataset.schema_fields]
        feature_names = [field.name for field in manifest.feature_set.definitions]

        assert data_path.exists(), manifest.slug
        assert evaluation_path.exists(), manifest.slug
        assert len(schema_names) == len(set(schema_names)), manifest.slug
        assert len(feature_names) == len(set(feature_names)), manifest.slug
        assert manifest.training_run.objective_metric_name in manifest.training_run.metrics
        assert manifest.model.signature["inputs"]
        assert manifest.model.signature["outputs"]
        assert manifest.deployment.sample_requests
        assert manifest.drift.baseline_profile
        assert manifest.alert.enabled
        assert manifest.retraining.enabled


def test_example_dataset_metadata_is_deterministic() -> None:
    entries = load_catalog_entries(Path("examples/catalog.json"))

    for _manifest, project_root in entries:
        data_file = next((project_root / "data").iterdir())
        first = dataset_file_metadata(data_file)
        second = dataset_file_metadata(data_file)

        assert first == second
        assert first["content_hash"].startswith("sha256:")
        assert first["size_bytes"] > 0
        assert first["row_count"] > 0
