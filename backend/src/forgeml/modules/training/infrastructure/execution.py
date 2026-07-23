from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forgeml.modules.training.domain.entities import (
    TrainingArtifact,
    TrainingExecutionResult,
    TrainingRun,
    TrainingRunStatus,
)

EXAMPLE_PROJECT_SLUG_PARAMETER = "forgeml.example_project_slug"


@dataclass(frozen=True)
class ExampleTrainerSpec:
    slug: str
    supported_algorithms: frozenset[str]
    train: Callable[..., dict[str, Any]]


class LocalExampleTrainingRunner:
    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root

    def can_run(self, training_run: TrainingRun) -> bool:
        slug = _example_project_slug(training_run)
        specs = _example_trainer_specs()
        return slug in specs and training_run.algorithm in specs[slug].supported_algorithms

    def run(self, training_run: TrainingRun) -> TrainingExecutionResult:
        slug = _example_project_slug(training_run)
        specs = _example_trainer_specs()
        if slug not in specs:
            raise ValueError(f"Unsupported example project slug: {slug}")

        spec = specs[slug]
        if training_run.algorithm not in spec.supported_algorithms:
            raise ValueError(
                f"Unsupported algorithm {training_run.algorithm!r} for example project {slug!r}"
            )

        output_dir = (self._artifact_root / str(training_run.id)).resolve()
        summary = spec.train(output_dir=output_dir)
        evaluation_report = _read_json(Path(summary["artifact_paths"]["evaluation"]))
        return TrainingExecutionResult(
            status=TrainingRunStatus.SUCCEEDED,
            metrics={name: float(value) for name, value in summary["metrics"].items()},
            evaluation_report={
                **evaluation_report,
                "example_project_slug": slug,
                "requested_algorithm": training_run.algorithm,
            },
            artifacts=_artifacts_from_summary(summary, training_run.artifact_uri),
            runner_name="local-example-training-runner",
            external_run_id=f"local-example:{training_run.id}",
        )


def _example_project_slug(training_run: TrainingRun) -> str:
    return str(training_run.hyperparameters.get(EXAMPLE_PROJECT_SLUG_PARAMETER, ""))


def _example_trainer_specs() -> dict[str, ExampleTrainerSpec]:
    from ml.examples.fraud_detection.train import train as train_fraud_detection
    from ml.examples.movie_recommendation.train import train as train_movie_recommendation
    from ml.examples.semantic_search.build_index import train as train_semantic_search

    return {
        "fraud-detection": ExampleTrainerSpec(
            slug="fraud-detection",
            supported_algorithms=frozenset({"xgboost", "logistic-regression-sgd"}),
            train=train_fraud_detection,
        ),
        "movie-recommendation": ExampleTrainerSpec(
            slug="movie-recommendation",
            supported_algorithms=frozenset({"pytorch-two-tower", "aggregate-ranking-baseline"}),
            train=train_movie_recommendation,
        ),
        "semantic-search": ExampleTrainerSpec(
            slug="semantic-search",
            supported_algorithms=frozenset({"sentence-transformer", "tfidf-cosine-retriever"}),
            train=train_semantic_search,
        ),
    }


def _artifacts_from_summary(
    summary: dict[str, Any],
    control_plane_artifact_uri: str,
) -> list[TrainingArtifact]:
    artifact_types = {
        "model": "model",
        "evaluation": "evaluation_report",
        "summary": "execution_summary",
    }
    return [
        TrainingArtifact(
            name=name,
            artifact_type=artifact_types[name],
            uri=Path(path).resolve().as_uri(),
            media_type="application/json",
            metadata={
                "local_path": str(Path(path).resolve()),
                "control_plane_uri": f"{control_plane_artifact_uri}/{name}.json",
            },
        )
        for name, path in summary["artifact_paths"].items()
    ]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
