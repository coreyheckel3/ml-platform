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
from forgeml.modules.training.infrastructure.external_package import (
    ExternalTrainingPackageProfile,
    ExternalTrainingPackageRunner,
    conversational_movie_recommender_profile,
    preview_external_training_command,
)
from forgeml.modules.training.repositories.interfaces import TrainingJobRunner
from forgeml.platform.artifacts import sha256_uri
from forgeml.platform.config import Settings

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


class CompositeTrainingJobRunner:
    def __init__(self, runners: list[TrainingJobRunner]) -> None:
        self._runners = tuple(runners)

    def can_run(self, training_run: TrainingRun) -> bool:
        return any(runner.can_run(training_run) for runner in self._runners)

    def run(self, training_run: TrainingRun) -> TrainingExecutionResult:
        for runner in self._runners:
            if runner.can_run(training_run):
                return runner.run(training_run)
        raise ValueError("No composed training runner can execute this run.")


def build_training_job_runner(settings: Settings) -> CompositeTrainingJobRunner:
    runners: list[TrainingJobRunner] = [
        LocalExampleTrainingRunner(settings.local_training_artifact_root)
    ]
    if settings.external_training_profiles_enabled:
        runners.append(
            ExternalTrainingPackageRunner(
                artifact_root=settings.local_training_artifact_root,
                profiles=configured_external_training_profiles(settings),
            )
        )
    return CompositeTrainingJobRunner(runners)


def configured_external_training_profiles(
    settings: Settings,
) -> tuple[ExternalTrainingPackageProfile, ...]:
    return (
        conversational_movie_recommender_profile(
            repo_root=settings.external_training_movie_recommender_repo_root,
            timeout_seconds=settings.external_training_command_timeout_seconds,
        ),
    )


def external_training_profile_catalog(settings: Settings) -> list[dict[str, object]]:
    if not settings.external_training_profiles_enabled:
        return []
    return [
        {
            "slug": profile.slug,
            "display_name": profile.display_name,
            "runner_kind": "external_package",
            "package_name": profile.package_name,
            "description": profile.description,
            "supported_algorithms": [algorithm.algorithm for algorithm in profile.algorithms],
            "default_algorithm": profile.default_algorithm_profile.algorithm,
            "default_model_type": profile.default_algorithm_profile.model_type,
            "objective_metric_name": profile.default_algorithm_profile.objective_metric_name,
            "default_hyperparameters": profile.default_algorithm_profile.default_hyperparameters,
            "availability": profile.availability(),
            "command_preview": preview_external_training_command(profile),
        }
        for profile in configured_external_training_profiles(settings)
    ]


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
                "size_bytes": Path(path).resolve().stat().st_size,
                "sha256": sha256_uri(Path(path).resolve().read_bytes()),
            },
        )
        for name, path in summary["artifact_paths"].items()
    ]


def _read_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Training artifact must contain a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}
