import json
from pathlib import Path

from scripts.dev import refresh_demo_data as refresh_module
from scripts.examples.bootstrap_examples import BootstrapSummary


def test_refresh_demo_data_builds_versioned_report(monkeypatch, tmp_path: Path) -> None:
    recorded: dict[str, object] = {}

    def fake_run_bootstrap(**kwargs):
        recorded.update(kwargs)
        return [
            BootstrapSummary(
                slug="fraud-detection",
                project_id="project-1",
                dataset_version_id="dataset-version-1",
                feature_set_id="feature-set-1",
                experiment_id="experiment-1",
                training_run_id="training-run-1",
                model_version_id="model-version-1",
                deployment_id="deployment-1",
                endpoint_id="endpoint-1",
                drift_report_id="drift-report-1",
                retraining_policy_id="retraining-policy-1",
            )
        ]

    monkeypatch.setattr(refresh_module, "run_bootstrap", fake_run_bootstrap)

    report = refresh_module.refresh_demo_data(
        base_url="http://127.0.0.1:8001",
        email="admin@forgeml.dev",
        password="forgeml-local-admin",
        catalog_path=Path("examples/catalog.json"),
        selected_projects=["fraud-detection"],
        artifact_root=tmp_path / "artifacts",
    )

    assert report["schema_version"] == "forgeml.demo_data_refresh.v1"
    assert report["summary"]["project_slugs"] == ["fraud-detection"]
    assert "training_runs" in report["summary"]["seeded_surfaces"]
    assert report["bootstrap"]["project_count"] == 1
    assert recorded["selected_projects"] == ["fraud-detection"]


def test_refresh_report_write_round_trip(tmp_path: Path) -> None:
    report = {
        "schema_version": "forgeml.demo_data_refresh.v1",
        "summary": {"project_count": 0},
    }
    output_path = tmp_path / "reports" / "demo-data-refresh.json"

    refresh_module.write_refresh_report(report, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == report
