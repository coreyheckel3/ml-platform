from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ml.libraries.forgeml_sdk.client import ForgeMLClient
from ml.libraries.forgeml_sdk.examples import ExampleProjectManifest, load_example_manifest
from scripts.examples.run_local_training import TRAINERS

EXAMPLE_PROJECT_SLUG_PARAMETER = "forgeml.example_project_slug"


@dataclass(frozen=True)
class BootstrapSummary:
    slug: str
    project_id: str
    dataset_version_id: str
    feature_set_id: str
    experiment_id: str
    training_run_id: str
    model_version_id: str
    deployment_id: str
    endpoint_id: str
    drift_report_id: str
    retraining_policy_id: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap ForgeML example projects.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--email", default="admin@forgeml.dev")
    parser.add_argument("--password", default="forgeml-local-admin")
    parser.add_argument("--catalog", default="examples/catalog.json")
    parser.add_argument("--project", action="append", default=[])
    args = parser.parse_args()

    client = ForgeMLClient(base_url=args.base_url)
    tokens = client.login(args.email, args.password)
    authenticated = client.with_access_token(str(tokens["access_token"]))
    catalog_path = Path(args.catalog)
    catalog_entries = load_catalog_entries(catalog_path)
    selected = set(args.project)
    summaries = [
        bootstrap_project(authenticated, manifest, project_root)
        for manifest, project_root in catalog_entries
        if not selected or manifest.slug in selected
    ]
    print(json.dumps([summary.__dict__ for summary in summaries], indent=2, sort_keys=True))


def load_catalog_entries(catalog_path: Path) -> list[tuple[ExampleProjectManifest, Path]]:
    catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
    return [
        (
            load_example_manifest(catalog_path.parent / manifest_path),
            (catalog_path.parent / manifest_path).parent,
        )
        for manifest_path in catalog_data["projects"]
    ]


def bootstrap_project(
    client: ForgeMLClient,
    manifest: ExampleProjectManifest,
    project_root: Path,
) -> BootstrapSummary:
    project = ensure_named(
        client.list_projects,
        lambda: client.create_project(
            {"name": manifest.name, "description": manifest.description}
        ),
        manifest.name,
    )
    dataset = ensure_named(
        lambda: client.list_datasets(str(project["id"])),
        lambda: client.create_dataset(
            str(project["id"]),
            {
                "name": manifest.dataset.name,
                "description": manifest.dataset.description,
                "source_type": manifest.dataset.source_type,
            },
        ),
        manifest.dataset.name,
    )
    dataset_version = ensure_dataset_version(client, str(dataset["id"]), manifest, project_root)
    feature_set = ensure_named(
        lambda: client.list_feature_sets(str(project["id"])),
        lambda: client.create_feature_set(
            str(project["id"]),
            {
                "name": manifest.feature_set.name,
                "description": manifest.feature_set.description,
                "entity_key": manifest.feature_set.entity_key,
            },
        ),
        manifest.feature_set.name,
    )
    ensure_feature_definitions(client, str(feature_set["id"]), manifest)
    ensure_named(
        lambda: client.list_feature_pipelines(str(feature_set["id"])),
        lambda: client.register_feature_pipeline(
            str(feature_set["id"]),
            {
                "name": manifest.feature_set.pipeline.name,
                "source_dataset_id": str(dataset["id"]),
                "code_ref": manifest.feature_set.pipeline.code_ref,
                "schedule_cron": manifest.feature_set.pipeline.schedule_cron,
            },
        ),
        manifest.feature_set.pipeline.name,
    )
    experiment = ensure_named(
        lambda: client.list_experiments(str(project["id"])),
        lambda: client.create_experiment(
            str(project["id"]),
            {"name": manifest.experiment.name, "description": manifest.experiment.description},
        ),
        manifest.experiment.name,
    )
    training_run = ensure_succeeded_training_run(
        client,
        str(project["id"]),
        str(experiment["id"]),
        str(dataset_version["id"]),
        str(feature_set["id"]),
        manifest,
        project_root,
    )
    registered_model = ensure_named(
        lambda: client.list_registered_models(str(project["id"])),
        lambda: client.create_registered_model(
            str(project["id"]),
            {
                "name": manifest.model.name,
                "description": manifest.model.description,
                "task_type": manifest.model.task_type,
            },
        ),
        manifest.model.name,
    )
    model_version = ensure_model_version(
        client,
        str(registered_model["id"]),
        str(training_run["id"]),
        manifest,
    )
    deployment = ensure_named(
        lambda: client.list_deployments(str(project["id"])),
        lambda: client.create_deployment(
            str(project["id"]),
            {
                "name": manifest.deployment.name,
                "description": manifest.deployment.description,
                "environment": manifest.deployment.environment,
            },
        ),
        manifest.deployment.name,
    )
    revision = ensure_deployment_revision(
        client,
        str(deployment["id"]),
        str(model_version["id"]),
        manifest,
    )
    endpoint = ensure_inference_endpoint(
        client,
        str(project["id"]),
        str(deployment["id"]),
        str(revision["id"]),
        manifest,
    )
    ensure_prediction_logs(client, str(endpoint["id"]), manifest)
    client.record_inference_metric_snapshot(
        str(endpoint["id"]),
        manifest.deployment.metric_snapshot.model_dump(),
    )
    drift_profile = ensure_named(
        lambda: client.list_drift_profiles(str(project["id"])),
        lambda: client.create_drift_profile(
            str(project["id"]),
            {
                "name": manifest.drift.profile_name,
                "description": manifest.drift.description,
                "dataset_version_id": str(dataset_version["id"]),
                "baseline_profile": manifest.drift.baseline_profile,
            },
        ),
        manifest.drift.profile_name,
    )
    drift_report = client.run_drift_report(
        str(drift_profile["id"]),
        {
            "endpoint_id": str(endpoint["id"]),
            "window_seconds": manifest.drift.report.window_seconds,
            "drift_threshold": manifest.drift.report.drift_threshold,
            "sample_limit": manifest.drift.report.sample_limit,
            "report_uri": (
                "s3://forgeml-artifacts/examples/"
                f"{manifest.slug}/reports/drift/latest.json"
            ),
        },
    )
    alert_rule = ensure_named(
        lambda: client.list_alert_rules(str(project["id"])),
        lambda: client.create_alert_rule(str(project["id"]), manifest.alert.model_dump()),
        manifest.alert.name,
    )
    client.evaluate_alert_rule(str(alert_rule["id"]), {"endpoint_id": str(endpoint["id"])})
    retraining_policy = ensure_named(
        lambda: client.list_retraining_policies(str(project["id"])),
        lambda: client.create_retraining_policy(
            str(project["id"]),
            build_retraining_policy_payload(
                manifest,
                str(deployment["id"]),
                str(experiment["id"]),
                str(dataset_version["id"]),
                str(feature_set["id"]),
            ),
        ),
        manifest.retraining.name,
    )
    client.evaluate_retraining_policy(
        str(retraining_policy["id"]),
        {"drift_report_id": str(drift_report["id"]), "reason": "Example drift evaluation."},
    )
    return BootstrapSummary(
        slug=manifest.slug,
        project_id=str(project["id"]),
        dataset_version_id=str(dataset_version["id"]),
        feature_set_id=str(feature_set["id"]),
        experiment_id=str(experiment["id"]),
        training_run_id=str(training_run["id"]),
        model_version_id=str(model_version["id"]),
        deployment_id=str(deployment["id"]),
        endpoint_id=str(endpoint["id"]),
        drift_report_id=str(drift_report["id"]),
        retraining_policy_id=str(retraining_policy["id"]),
    )


def ensure_dataset_version(
    client: ForgeMLClient,
    dataset_id: str,
    manifest: ExampleProjectManifest,
    project_root: Path,
) -> dict[str, Any]:
    data_path = project_root / manifest.dataset.data_path
    metadata = dataset_file_metadata(data_path)
    existing = next(
        (
            item
            for item in client.list_dataset_versions(dataset_id).get("items", [])
            if item.get("content_hash") == metadata["content_hash"]
        ),
        None,
    )
    if existing is not None:
        return existing
    created = client.create_dataset_version(
        dataset_id,
        {
            "filename": data_path.name,
            "content_type": manifest.dataset.content_type,
        },
    )
    version = created["version"]
    finalized = client.finalize_dataset_version(
        str(version["id"]),
        {
            "object_uri": created["upload"]["object_uri"],
            "content_hash": metadata["content_hash"],
            "size_bytes": metadata["size_bytes"],
            "row_count": metadata["row_count"],
            "schema_fields": [field.model_dump() for field in manifest.dataset.schema_fields],
        },
    )
    client.validate_dataset_version(str(finalized["id"]))
    return finalized


def ensure_feature_definitions(
    client: ForgeMLClient,
    feature_set_id: str,
    manifest: ExampleProjectManifest,
) -> None:
    existing_names = {
        item["name"] for item in client.list_feature_definitions(feature_set_id).get("items", [])
    }
    missing = [
        definition.model_dump()
        for definition in manifest.feature_set.definitions
        if definition.name not in existing_names
    ]
    if missing:
        client.register_feature_definitions(feature_set_id, {"definitions": missing})


def ensure_succeeded_training_run(
    client: ForgeMLClient,
    project_id: str,
    experiment_id: str,
    dataset_version_id: str,
    feature_set_id: str,
    manifest: ExampleProjectManifest,
    project_root: Path,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in client.list_training_runs(project_id).get("items", [])
            if item.get("algorithm") == manifest.training_run.algorithm
            and item.get("status") == "succeeded"
            and item.get("hyperparameters", {}).get(EXAMPLE_PROJECT_SLUG_PARAMETER)
            == manifest.slug
        ),
        None,
    )
    if existing is not None:
        return existing
    training_run = client.start_training_run(
        project_id,
        {
            "experiment_id": experiment_id,
            "run_name": manifest.training_run.run_name,
            "dataset_version_id": dataset_version_id,
            "feature_set_id": feature_set_id,
            "algorithm": manifest.training_run.algorithm,
            "model_type": manifest.training_run.model_type,
            "objective_metric_name": manifest.training_run.objective_metric_name,
            "hyperparameters": example_training_hyperparameters(manifest),
        },
    )
    resolved_artifact_root = artifact_root or Path("artifacts/examples")
    summary = TRAINERS[manifest.slug](
        output_dir=resolved_artifact_root / manifest.slug / str(training_run["id"])
    )
    evaluation_report = build_training_execution_report(summary, manifest)
    return client.record_training_result(
        str(training_run["id"]),
        {
            "status": "succeeded",
            "metrics": summary["metrics"],
            "evaluation_report": evaluation_report,
        },
    )


def example_training_hyperparameters(manifest: ExampleProjectManifest) -> dict[str, object]:
    return {
        **manifest.training_run.hyperparameters,
        EXAMPLE_PROJECT_SLUG_PARAMETER: manifest.slug,
    }


def build_training_execution_report(
    summary: dict[str, Any],
    manifest: ExampleProjectManifest,
) -> dict[str, object]:
    evaluation_report = json.loads(
        Path(summary["artifact_paths"]["evaluation"]).read_text(encoding="utf-8")
    )
    artifacts = [
        {
            "name": name,
            "artifact_type": {
                "model": "model",
                "evaluation": "evaluation_report",
                "summary": "execution_summary",
            }[name],
            "uri": Path(path).resolve().as_uri(),
            "media_type": "application/json",
            "metadata": {
                "local_path": str(Path(path).resolve()),
                "example_project_slug": manifest.slug,
            },
        }
        for name, path in summary["artifact_paths"].items()
    ]
    return {
        **evaluation_report,
        "example_project_slug": manifest.slug,
        "training_execution": {
            "schema_version": "forgeml.training_execution_result.v1",
            "runner_name": "local-example-training-runner",
            "external_run_id": f"bootstrap-example:{manifest.slug}",
            "artifacts": artifacts,
        },
    }


def ensure_model_version(
    client: ForgeMLClient,
    model_id: str,
    training_run_id: str,
    manifest: ExampleProjectManifest,
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in client.list_model_versions(model_id).get("items", [])
            if item.get("training_run_id") == training_run_id
        ),
        None,
    )
    model_version = existing or client.register_model_version(
        model_id,
        {
            "training_run_id": training_run_id,
            "model_format": manifest.model.model_format,
            "signature": manifest.model.signature,
        },
    )
    version_id = str(model_version["id"])
    if model_version["status"] == "candidate":
        client.request_model_approval(
            version_id,
            {"comment": manifest.model.approval_comment},
        )
        client.review_model_version(
            version_id,
            {"status": "approved", "comment": manifest.model.approval_comment},
        )
        model_version = client.get_model_version(version_id)
    elif model_version["status"] == "pending_approval":
        client.review_model_version(
            version_id,
            {"status": "approved", "comment": manifest.model.approval_comment},
        )
        model_version = client.get_model_version(version_id)
    return model_version


def ensure_deployment_revision(
    client: ForgeMLClient,
    deployment_id: str,
    model_version_id: str,
    manifest: ExampleProjectManifest,
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in client.list_deployment_revisions(deployment_id).get("items", [])
            if item.get("model_version_id") == model_version_id
        ),
        None,
    )
    revision = existing or client.create_deployment_revision(
        deployment_id,
        {
            "model_version_id": model_version_id,
            "serving_image": manifest.deployment.serving_image,
            "runtime_config": manifest.deployment.runtime_config,
            "traffic_percentage": 100,
        },
    )
    if revision["status"] != "healthy":
        client.record_deployment_health(
            str(revision["id"]),
            manifest.deployment.health_check.model_dump(),
        )
        revisions = client.list_deployment_revisions(deployment_id).get("items", [])
        revision = next(item for item in revisions if item["id"] == revision["id"])
    return revision


def ensure_inference_endpoint(
    client: ForgeMLClient,
    project_id: str,
    deployment_id: str,
    revision_id: str,
    manifest: ExampleProjectManifest,
) -> dict[str, Any]:
    endpoint_template = manifest.deployment.inference_endpoint
    existing = next(
        (
            item
            for item in client.list_inference_endpoints(project_id).get("items", [])
            if item.get("route_path") == endpoint_template.route_path
        ),
        None,
    )
    return existing or client.create_inference_endpoint(
        project_id,
        {
            "deployment_id": deployment_id,
            "deployment_revision_id": revision_id,
            "name": endpoint_template.name,
            "description": endpoint_template.description,
            "route_path": endpoint_template.route_path,
        },
    )


def ensure_prediction_logs(
    client: ForgeMLClient,
    endpoint_id: str,
    manifest: ExampleProjectManifest,
) -> None:
    existing_ids = {
        item["request_id"] for item in client.list_inference_requests(endpoint_id).get("items", [])
    }
    for sample_request in manifest.deployment.sample_requests:
        if sample_request.request_id not in existing_ids:
            client.predict(endpoint_id, sample_request.model_dump())


def build_retraining_policy_payload(
    manifest: ExampleProjectManifest,
    deployment_id: str,
    experiment_id: str,
    dataset_version_id: str,
    feature_set_id: str,
) -> dict[str, Any]:
    training_template = {
        **manifest.retraining.training_template.model_dump(),
        "experiment_id": experiment_id,
        "dataset_version_id": dataset_version_id,
        "feature_set_id": feature_set_id,
    }
    training_template["hyperparameters"] = {
        **dict(training_template["hyperparameters"]),
        EXAMPLE_PROJECT_SLUG_PARAMETER: manifest.slug,
    }
    return {
        "deployment_id": deployment_id,
        "name": manifest.retraining.name,
        "description": manifest.retraining.description,
        "trigger_type": manifest.retraining.trigger_type,
        "trigger_config": manifest.retraining.trigger_config,
        "training_template": training_template,
        "cooldown_seconds": manifest.retraining.cooldown_seconds,
        "max_runs_per_day": manifest.retraining.max_runs_per_day,
        "approval_required": manifest.retraining.approval_required,
        "enabled": manifest.retraining.enabled,
    }


def ensure_named(list_items, create_item, name: str) -> dict[str, Any]:
    existing = next(
        (item for item in list_items().get("items", []) if item.get("name") == name),
        None,
    )
    return existing or create_item()


def dataset_file_metadata(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "content_hash": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "size_bytes": len(content),
        "row_count": row_count(path),
    }


def row_count(path: Path) -> int:
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return max(sum(1 for _row in csv.reader(handle)) - 1, 0)
    if path.suffix == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    raise ValueError(f"Unsupported example dataset extension: {path.suffix}")


if __name__ == "__main__":
    main()
