from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from forgeml.modules.training.domain.entities import TrainingRun, TrainingRunStatus
from forgeml.modules.training.infrastructure.execution import (
    external_training_profile_catalog,
)
from forgeml.modules.training.infrastructure.external_package import (
    CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
    EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION,
    EXTERNAL_TRAINING_PROFILE_PARAMETER,
    ExternalProcessResult,
    ExternalTrainingPackageRunner,
    conversational_movie_recommender_profile,
    preview_external_training_command,
)
from forgeml.platform.config import Settings


def test_external_training_package_runner_executes_profile(tmp_path: Path) -> None:
    repo_root = _fake_external_repo(tmp_path)
    profile = conversational_movie_recommender_profile(
        repo_root=repo_root,
        timeout_seconds=30,
    )
    runner = ExternalTrainingPackageRunner(
        artifact_root=tmp_path / "artifacts",
        profiles=[profile],
    )
    training_run = _external_training_run()

    result = runner.run(training_run)

    assert runner.can_run(training_run)
    assert result.status == TrainingRunStatus.SUCCEEDED
    assert result.metrics == {
        "ndcg_at_k": 0.67,
        "precision_at_k": 0.42,
        "recall_at_k": 0.58,
        "hit_rate_at_k": 0.71,
        "mrr_at_k": 0.61,
        "evaluated_users": 7.0,
        "component.hybrid.ndcg_at_k": 0.67,
        "component.hybrid.precision_at_k": 0.42,
        "component.hybrid.recall_at_k": 0.58,
        "component.hybrid.hit_rate_at_k": 0.71,
        "component.hybrid.mrr_at_k": 0.61,
        "component.hybrid.evaluated_users": 7.0,
        "component.popularity.ndcg_at_k": 0.31,
        "component.popularity.precision_at_k": 0.2,
        "component.popularity.recall_at_k": 0.24,
        "component.popularity.hit_rate_at_k": 0.29,
        "component.popularity.mrr_at_k": 0.25,
        "component.popularity.evaluated_users": 7.0,
        "baseline.best_baseline_recall_at_k": 0.24,
        "baseline.best_baseline_ndcg_at_k": 0.31,
        "baseline.lift_over_best_baseline_recall": 2.4166666666666665,
    }
    assert result.runner_name == "external-training-package-runner"
    assert result.external_run_id.startswith(
        f"external-package:{CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG}:"
    )
    assert result.evaluation_report["external_package"]["schema_version"] == (
        EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION
    )
    assert result.evaluation_report["external_package"]["profile"] == (
        CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG
    )
    assert {artifact.name for artifact in result.artifacts} == {
        "collaborative-filter",
        "evaluation",
        "metadata-retriever",
        "model",
    }
    model = next(artifact for artifact in result.artifacts if artifact.name == "model")
    assert model.artifact_type == "model"
    assert model.metadata["control_plane_uri"].endswith("/model/engine.joblib")


def test_external_training_package_runner_returns_failed_result_for_command_failure(
    tmp_path: Path,
) -> None:
    repo_root = _fake_external_repo(tmp_path)
    profile = conversational_movie_recommender_profile(
        repo_root=repo_root,
        timeout_seconds=30,
    )
    runner = ExternalTrainingPackageRunner(
        artifact_root=tmp_path / "artifacts",
        profiles=[profile],
        executor=lambda _command, _cwd, _env, _timeout: ExternalProcessResult(
            returncode=2,
            stdout="",
            stderr="model package crashed",
            duration_seconds=0.4,
        ),
    )

    result = runner.run(_external_training_run())

    assert result.status == TrainingRunStatus.FAILED
    assert result.error_message == "model package crashed"
    assert result.artifacts == []
    assert result.evaluation_report["external_package"]["returncode"] == 2


def test_external_training_package_runner_rejects_unsafe_data_path(tmp_path: Path) -> None:
    repo_root = _fake_external_repo(tmp_path)
    profile = conversational_movie_recommender_profile(
        repo_root=repo_root,
        timeout_seconds=30,
    )
    runner = ExternalTrainingPackageRunner(
        artifact_root=tmp_path / "artifacts",
        profiles=[profile],
    )

    with pytest.raises(ValueError, match="inside the external package repository"):
        runner.run(
            _external_training_run(
                hyperparameters={
                    EXTERNAL_TRAINING_PROFILE_PARAMETER: (
                        CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG
                    ),
                    "data_dir": "../private",
                }
            )
        )


def test_external_training_profile_catalog_exposes_command_preview(tmp_path: Path) -> None:
    repo_root = _fake_external_repo(tmp_path)
    profile = conversational_movie_recommender_profile(
        repo_root=repo_root,
        timeout_seconds=30,
    )

    preview = preview_external_training_command(profile)

    assert str(repo_root / ".venv/bin/movie-rec-build") in preview
    assert "--write-metrics" in preview
    assert "--eval-max-users" in preview


def test_external_training_profile_catalog_honors_disabled_setting(tmp_path: Path) -> None:
    settings = Settings(
        external_training_profiles_enabled=False,
        external_training_movie_recommender_repo_root=_fake_external_repo(tmp_path),
    )

    assert external_training_profile_catalog(settings) == []


def test_external_training_package_runner_requires_profile_selector(tmp_path: Path) -> None:
    repo_root = _fake_external_repo(tmp_path)
    profile = conversational_movie_recommender_profile(
        repo_root=repo_root,
        timeout_seconds=30,
    )
    runner = ExternalTrainingPackageRunner(
        artifact_root=tmp_path / "artifacts",
        profiles=[profile],
    )

    assert not runner.can_run(_external_training_run(hyperparameters={}))


def _external_training_run(
    *,
    hyperparameters: dict[str, object] | None = None,
) -> TrainingRun:
    return TrainingRun(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        experiment_id=uuid4(),
        experiment_run_id=uuid4(),
        dataset_version_id=uuid4(),
        feature_set_id=None,
        algorithm="movie-rec-svd",
        model_type="hybrid-recommender",
        objective_metric_name="ndcg_at_k",
        hyperparameters=hyperparameters
        if hyperparameters is not None
        else {
            EXTERNAL_TRAINING_PROFILE_PARAMETER: CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
            "data_dir": "data/sample",
            "write_metrics": True,
            "eval_k": 5,
            "eval_max_users": 7,
            "quiet": True,
        },
        status=TrainingRunStatus.QUEUED,
        requested_by=uuid4(),
        artifact_uri="s3://forgeml-artifacts/training-runs/run-1",
        orchestrator_run_id="local-training:run-1",
        metrics={},
        error_message=None,
    )


def _fake_external_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "movie-recommender"
    bin_dir = repo_root / ".venv/bin"
    data_dir = repo_root / "data/sample"
    bin_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    executable = bin_dir / "movie-rec-build"
    executable.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import argparse, json",
                "from pathlib import Path",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--data-dir')",
                "parser.add_argument('--model-dir')",
                "parser.add_argument('--collaborative-model')",
                "parser.add_argument('--write-metrics', action='store_true')",
                "parser.add_argument('--quiet', action='store_true')",
                "parser.add_argument('--eval-k', type=int)",
                "parser.add_argument('--eval-max-users', type=int)",
                "args, _unknown = parser.parse_known_args()",
                "model_dir = Path(args.model_dir)",
                "model_dir.mkdir(parents=True, exist_ok=True)",
                "model_files = [",
                "    'engine.joblib',",
                "    'collaborative_filter.joblib',",
                "    'metadata_retriever.joblib',",
                "]",
                "for name in model_files:",
                "    (model_dir / name).write_bytes(b'fake-model')",
                "if args.write_metrics:",
                "    (model_dir / 'evaluation.json').write_text(json.dumps({",
                "        'precision_at_k': 0.42,",
                "        'recall_at_k': 0.58,",
                "        'ndcg_at_k': 0.67,",
                "        'hit_rate_at_k': 0.71,",
                "        'mrr_at_k': 0.61,",
                "        'evaluated_users': args.eval_max_users,",
                "        'collaborative_model': args.collaborative_model,",
                "        'component_metrics': {",
                "            'hybrid': {",
                "                'precision_at_k': 0.42,",
                "                'recall_at_k': 0.58,",
                "                'ndcg_at_k': 0.67,",
                "                'hit_rate_at_k': 0.71,",
                "                'mrr_at_k': 0.61,",
                "                'evaluated_users': args.eval_max_users,",
                "            },",
                "            'popularity': {",
                "                'precision_at_k': 0.20,",
                "                'recall_at_k': 0.24,",
                "                'ndcg_at_k': 0.31,",
                "                'hit_rate_at_k': 0.29,",
                "                'mrr_at_k': 0.25,",
                "                'evaluated_users': args.eval_max_users,",
                "            },",
                "        },",
                "        'baseline_summary': {",
                "            'best_baseline_recall_at_k': 0.24,",
                "            'best_baseline_ndcg_at_k': 0.31,",
                "            'lift_over_best_baseline_recall': 2.4166666666666665,",
                "        },",
                "    }), encoding='utf-8')",
                "print(f'Saved recommender artifacts to {model_dir}')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return repo_root
