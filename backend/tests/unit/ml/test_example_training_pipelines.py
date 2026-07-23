from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from ml.examples.fraud_detection.train import train as train_fraud_detection
from ml.examples.movie_recommendation.train import train as train_movie_recommendation
from ml.examples.semantic_search.build_index import train as train_semantic_search
from scripts.examples.run_local_training import run_training

Trainer = Callable[..., dict[str, Any]]


@pytest.mark.parametrize(
    ("trainer", "slug", "objective_metric"),
    [
        (train_fraud_detection, "fraud-detection", "auc"),
        (train_movie_recommendation, "movie-recommendation", "ndcg_at_10"),
        (train_semantic_search, "semantic-search", "recall_at_5"),
    ],
)
def test_example_trainers_write_versioned_artifacts(
    tmp_path: Path,
    trainer: Trainer,
    slug: str,
    objective_metric: str,
) -> None:
    summary = trainer(output_dir=tmp_path / slug)

    model_path = Path(summary["artifact_paths"]["model"])
    evaluation_path = Path(summary["artifact_paths"]["evaluation"])
    summary_path = Path(summary["artifact_paths"]["summary"])
    model = json.loads(model_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    persisted_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["project_slug"] == slug
    assert model_path.is_file()
    assert evaluation_path.is_file()
    assert summary_path.is_file()
    assert persisted_summary == summary
    assert model["schema_version"] == "forgeml.example_model_artifact.v1"
    assert model["project_slug"] == slug
    assert evaluation["artifact_path"] == "model.json"
    assert objective_metric in summary["metrics"]
    assert summary["metrics"][objective_metric] >= 0


def test_example_training_orchestrator_writes_combined_manifest(tmp_path: Path) -> None:
    manifest = run_training(
        output_dir=tmp_path,
        selected_projects=["semantic-search", "fraud-detection"],
    )

    persisted_manifest = json.loads(
        (tmp_path / "training-summary.json").read_text(encoding="utf-8")
    )

    assert manifest == persisted_manifest
    assert manifest["schema_version"] == "forgeml.example_training_manifest.v1"
    assert manifest["project_count"] == 2
    assert [project["project_slug"] for project in manifest["projects"]] == [
        "semantic-search",
        "fraud-detection",
    ]
    assert (tmp_path / "semantic-search" / "model.json").is_file()
    assert (tmp_path / "fraud-detection" / "evaluation.json").is_file()
    assert (tmp_path / "fraud-detection" / "summary.json").is_file()


def test_example_training_orchestrator_rejects_unknown_project(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing-project"):
        run_training(output_dir=tmp_path, selected_projects=["missing-project"])
