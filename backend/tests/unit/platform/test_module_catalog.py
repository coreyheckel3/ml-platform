from pathlib import Path

from forgeml.modules.catalog import MODULES, module_names


def test_module_catalog_contains_required_platform_modules() -> None:
    assert module_names() == {
        "auth",
        "projects",
        "datasets",
        "feature_store",
        "training",
        "experiments",
        "model_registry",
        "deployments",
        "inference",
        "monitoring",
        "alerting",
        "drift_detection",
        "retraining",
        "administration",
    }


def test_each_module_has_clean_architecture_directories() -> None:
    module_root = Path("backend/src/forgeml/modules")
    expected_layers = {"api", "application", "domain", "repositories", "infrastructure"}

    for module in MODULES:
        existing_layers = {
            path.name for path in (module_root / module.name).iterdir() if path.is_dir()
        }
        assert expected_layers.issubset(existing_layers), module.name
