from __future__ import annotations

import json
import os
import subprocess  # noqa: S404
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from forgeml.modules.training.domain.entities import (
    TrainingArtifact,
    TrainingExecutionResult,
    TrainingRun,
    TrainingRunStatus,
)
from forgeml.platform.artifacts import sha256_uri

EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION = "forgeml.external_training_package.v1"
EXTERNAL_TRAINING_PROFILE_PARAMETER = "forgeml.external_training_profile"
CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG = "conversational-movie-recommender"


@dataclass(frozen=True)
class ExternalTrainingAlgorithmProfile:
    algorithm: str
    model_type: str
    objective_metric_name: str
    collaborative_model: str
    default_hyperparameters: dict[str, object]


@dataclass(frozen=True)
class ExternalTrainingPackageProfile:
    slug: str
    display_name: str
    package_name: str
    executable_name: str
    description: str
    repo_root: Path
    default_data_dir: str
    timeout_seconds: float
    algorithms: tuple[ExternalTrainingAlgorithmProfile, ...]

    @property
    def executable_path(self) -> Path:
        return self.repo_root / ".venv/bin" / self.executable_name

    @property
    def default_algorithm_profile(self) -> ExternalTrainingAlgorithmProfile:
        return self.algorithms[0]

    def algorithm_profile(self, algorithm: str) -> ExternalTrainingAlgorithmProfile | None:
        return next((item for item in self.algorithms if item.algorithm == algorithm), None)

    def availability(self) -> dict[str, object]:
        data_dir = self.repo_root / self.default_data_dir
        executable_exists = self.executable_path.is_file()
        data_dir_exists = data_dir.is_dir()
        return {
            "available": executable_exists and data_dir_exists,
            "repo_root": str(self.repo_root),
            "executable_path": str(self.executable_path),
            "data_dir": str(data_dir),
            "missing": [
                label
                for label, exists in (
                    ("repo_root", self.repo_root.is_dir()),
                    ("executable", executable_exists),
                    ("data_dir", data_dir_exists),
                )
                if not exists
            ],
        }


@dataclass(frozen=True)
class ExternalProcessResult:
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


CommandExecutor = Callable[[Sequence[str], Path, Mapping[str, str], float], ExternalProcessResult]


class ExternalTrainingPackageRunner:
    def __init__(
        self,
        *,
        artifact_root: Path,
        profiles: Sequence[ExternalTrainingPackageProfile],
        executor: CommandExecutor | None = None,
    ) -> None:
        self._artifact_root = artifact_root
        self._profiles = {profile.slug: profile for profile in profiles}
        self._executor = executor or _subprocess_executor

    @property
    def profiles(self) -> tuple[ExternalTrainingPackageProfile, ...]:
        return tuple(self._profiles.values())

    def can_run(self, training_run: TrainingRun) -> bool:
        profile = self._profile_for(training_run)
        return profile is not None and profile.algorithm_profile(training_run.algorithm) is not None

    def run(self, training_run: TrainingRun) -> TrainingExecutionResult:
        profile = self._profile_for(training_run)
        if profile is None:
            raise ValueError("Training run does not declare an external training profile.")
        algorithm_profile = profile.algorithm_profile(training_run.algorithm)
        if algorithm_profile is None:
            raise ValueError(
                f"External training profile {profile.slug!r} does not support "
                f"algorithm {training_run.algorithm!r}."
            )

        availability = profile.availability()
        if not availability["available"]:
            return _failed_execution_result(
                profile=profile,
                training_run=training_run,
                error_message=(
                    "External training profile is unavailable: "
                    f"{', '.join(str(item) for item in availability['missing'])}."
                ),
                command=[],
                stdout="",
                stderr="",
                duration_seconds=0.0,
            )

        output_dir = (self._artifact_root / str(training_run.id) / profile.slug).resolve()
        model_dir = output_dir / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        command, data_dir = _build_command(
            profile=profile,
            algorithm_profile=algorithm_profile,
            training_run=training_run,
            model_dir=model_dir,
        )
        env = _environment_for(profile.repo_root)
        result = self._executor(command, profile.repo_root, env, profile.timeout_seconds)
        evaluation_report = _read_evaluation_report(model_dir)
        execution_report = {
            "external_package": {
                "schema_version": EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION,
                "profile": profile.slug,
                "package_name": profile.package_name,
                "repo_root": str(profile.repo_root),
                "data_dir": str(data_dir),
                "model_dir": str(model_dir),
                "command": command,
                "duration_seconds": result.duration_seconds,
                "returncode": result.returncode,
                "stdout_tail": _tail(result.stdout),
                "stderr_tail": _tail(result.stderr),
            },
            "metrics_report": evaluation_report,
        }
        if result.returncode != 0:
            return _failed_execution_result(
                profile=profile,
                training_run=training_run,
                error_message=(
                    _tail(result.stderr, max_chars=700)
                    or _tail(result.stdout, max_chars=700)
                    or f"External training command exited with {result.returncode}."
                ),
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=result.duration_seconds,
                evaluation_report=execution_report,
            )

        return TrainingExecutionResult(
            status=TrainingRunStatus.SUCCEEDED,
            metrics=_metrics_from_evaluation(evaluation_report),
            evaluation_report=execution_report,
            artifacts=_artifacts_from_model_dir(model_dir, training_run.artifact_uri, profile.slug),
            runner_name="external-training-package-runner",
            external_run_id=f"external-package:{profile.slug}:{training_run.id}",
        )

    def _profile_for(self, training_run: TrainingRun) -> ExternalTrainingPackageProfile | None:
        return self._profiles.get(_profile_slug(training_run))


def conversational_movie_recommender_profile(
    *,
    repo_root: Path,
    timeout_seconds: float,
) -> ExternalTrainingPackageProfile:
    svd_defaults: dict[str, object] = {
        EXTERNAL_TRAINING_PROFILE_PARAMETER: CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
        "data_dir": "data/sample",
        "write_metrics": True,
        "eval_k": 5,
        "eval_max_users": 20,
        "quiet": True,
    }
    two_tower_defaults = {
        **svd_defaults,
        "two_tower_embedding_dim": 16,
        "two_tower_epochs": 2,
        "two_tower_batch_size": 64,
        "two_tower_negative_ratio": 1,
        "two_tower_validation_fraction": 0.1,
        "eval_two_tower_epochs": 2,
    }
    return ExternalTrainingPackageProfile(
        slug=CONVERSATIONAL_MOVIE_RECOMMENDER_PROFILE_SLUG,
        display_name="Conversational Movie Recommender",
        package_name="conversational-movie-recommender",
        executable_name="movie-rec-build",
        description=(
            "Runs the external recommender package build CLI and imports its "
            "ranking metrics plus model artifacts into ForgeML."
        ),
        repo_root=repo_root.expanduser().resolve(),
        default_data_dir="data/sample",
        timeout_seconds=timeout_seconds,
        algorithms=(
            ExternalTrainingAlgorithmProfile(
                algorithm="movie-rec-svd",
                model_type="hybrid-recommender",
                objective_metric_name="ndcg_at_k",
                collaborative_model="svd",
                default_hyperparameters=svd_defaults,
            ),
            ExternalTrainingAlgorithmProfile(
                algorithm="movie-rec-two-tower",
                model_type="neural-two-tower-recommender",
                objective_metric_name="ndcg_at_k",
                collaborative_model="two_tower",
                default_hyperparameters=two_tower_defaults,
            ),
        ),
    )


def preview_external_training_command(
    profile: ExternalTrainingPackageProfile,
    algorithm_profile: ExternalTrainingAlgorithmProfile | None = None,
) -> list[str]:
    selected_algorithm = algorithm_profile or profile.default_algorithm_profile
    command, _data_dir = _command_from_hyperparameters(
        profile=profile,
        algorithm_profile=selected_algorithm,
        hyperparameters=selected_algorithm.default_hyperparameters,
        model_dir=Path("<artifact-root>") / "<training-run-id>" / profile.slug / "model",
    )
    return command


def _profile_slug(training_run: TrainingRun) -> str:
    return str(training_run.hyperparameters.get(EXTERNAL_TRAINING_PROFILE_PARAMETER, ""))


def _build_command(
    *,
    profile: ExternalTrainingPackageProfile,
    algorithm_profile: ExternalTrainingAlgorithmProfile,
    training_run: TrainingRun,
    model_dir: Path,
) -> tuple[list[str], Path]:
    return _command_from_hyperparameters(
        profile=profile,
        algorithm_profile=algorithm_profile,
        hyperparameters=training_run.hyperparameters,
        model_dir=model_dir,
    )


def _command_from_hyperparameters(
    *,
    profile: ExternalTrainingPackageProfile,
    algorithm_profile: ExternalTrainingAlgorithmProfile,
    hyperparameters: Mapping[str, object],
    model_dir: Path,
) -> tuple[list[str], Path]:
    defaults = algorithm_profile.default_hyperparameters
    data_dir = profile.repo_root / _relative_path_param(
        hyperparameters,
        "data_dir",
        str(defaults.get("data_dir", profile.default_data_dir)),
    )
    command = [
        str(profile.executable_path),
        "--data-dir",
        str(data_dir),
        "--model-dir",
        str(model_dir),
        "--collaborative-model",
        algorithm_profile.collaborative_model,
    ]
    if _bool_param(hyperparameters, "write_metrics", bool(defaults.get("write_metrics", True))):
        command.append("--write-metrics")
    if _bool_param(hyperparameters, "quiet", bool(defaults.get("quiet", True))):
        command.append("--quiet")
    command.extend(
        [
            "--eval-k",
            str(_int_param(hyperparameters, "eval_k", int(defaults.get("eval_k", 5)), 1, 100)),
        ]
    )
    eval_max_users = _optional_int_param(
        hyperparameters,
        "eval_max_users",
        defaults.get("eval_max_users"),
        1,
        1_000_000,
    )
    if eval_max_users is not None:
        command.extend(["--eval-max-users", str(eval_max_users)])
    if algorithm_profile.collaborative_model == "two_tower":
        command.extend(_two_tower_arguments(hyperparameters, defaults))
    return command, data_dir


def _two_tower_arguments(
    hyperparameters: Mapping[str, object],
    defaults: Mapping[str, object],
) -> list[str]:
    return [
        "--two-tower-embedding-dim",
        str(
            _int_param(
                hyperparameters,
                "two_tower_embedding_dim",
                int(defaults.get("two_tower_embedding_dim", 16)),
                1,
                4096,
            )
        ),
        "--two-tower-epochs",
        str(
            _int_param(
                hyperparameters,
                "two_tower_epochs",
                int(defaults.get("two_tower_epochs", 2)),
                1,
                10_000,
            )
        ),
        "--two-tower-batch-size",
        str(
            _int_param(
                hyperparameters,
                "two_tower_batch_size",
                int(defaults.get("two_tower_batch_size", 64)),
                1,
                100_000,
            )
        ),
        "--two-tower-negative-ratio",
        str(
            _int_param(
                hyperparameters,
                "two_tower_negative_ratio",
                int(defaults.get("two_tower_negative_ratio", 1)),
                1,
                1_000,
            )
        ),
        "--two-tower-validation-fraction",
        str(
            _float_param(
                hyperparameters,
                "two_tower_validation_fraction",
                float(defaults.get("two_tower_validation_fraction", 0.1)),
                0.0,
                0.9,
            )
        ),
        "--eval-two-tower-epochs",
        str(
            _int_param(
                hyperparameters,
                "eval_two_tower_epochs",
                int(defaults.get("eval_two_tower_epochs", 2)),
                1,
                10_000,
            )
        ),
    ]


def _subprocess_executor(
    command: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> ExternalProcessResult:
    started_at = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603
            list(command),
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
        return ExternalProcessResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started_at,
        )
    except subprocess.TimeoutExpired as exc:
        return ExternalProcessResult(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"External training command timed out after {timeout_seconds}s.",
            duration_seconds=time.monotonic() - started_at,
        )


def _failed_execution_result(
    *,
    profile: ExternalTrainingPackageProfile,
    training_run: TrainingRun,
    error_message: str,
    command: Sequence[str],
    stdout: str,
    stderr: str,
    duration_seconds: float,
    evaluation_report: dict[str, object] | None = None,
) -> TrainingExecutionResult:
    return TrainingExecutionResult(
        status=TrainingRunStatus.FAILED,
        metrics={},
        evaluation_report=evaluation_report
        or {
            "external_package": {
                "schema_version": EXTERNAL_TRAINING_PACKAGE_SCHEMA_VERSION,
                "profile": profile.slug,
                "package_name": profile.package_name,
                "repo_root": str(profile.repo_root),
                "command": list(command),
                "duration_seconds": duration_seconds,
                "returncode": 1,
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
        },
        artifacts=[],
        runner_name="external-training-package-runner",
        external_run_id=f"external-package:{profile.slug}:{training_run.id}",
        error_message=error_message,
    )


def _artifacts_from_model_dir(
    model_dir: Path,
    control_plane_artifact_uri: str,
    profile_slug: str,
) -> list[TrainingArtifact]:
    artifacts: list[TrainingArtifact] = []
    for path in sorted(model_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(model_dir).as_posix()
        artifacts.append(
            TrainingArtifact(
                name=_artifact_name(path),
                artifact_type=_artifact_type(path),
                uri=path.resolve().as_uri(),
                media_type=_media_type(path),
                metadata={
                    "local_path": str(path.resolve()),
                    "relative_path": relative_path,
                    "profile": profile_slug,
                    "control_plane_uri": (
                        f"{control_plane_artifact_uri}/{profile_slug}/model/{relative_path}"
                    ),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_uri(path.read_bytes()),
                },
            )
        )
    return artifacts


def _artifact_name(path: Path) -> str:
    if path.name == "engine.joblib":
        return "model"
    if path.name == "evaluation.json":
        return "evaluation"
    return path.stem.replace("_", "-")


def _artifact_type(path: Path) -> str:
    if path.name == "engine.joblib":
        return "model"
    if path.name == "evaluation.json":
        return "evaluation_report"
    if path.suffix == ".joblib":
        return "model_component"
    return "supporting_artifact"


def _media_type(path: Path) -> str:
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".joblib":
        return "application/octet-stream"
    return "application/octet-stream"


def _read_evaluation_report(model_dir: Path) -> dict[str, object]:
    path = model_dir / "evaluation.json"
    if not path.is_file():
        return {}
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items()}


def _metrics_from_evaluation(evaluation_report: Mapping[str, object]) -> dict[str, float]:
    metric_names = (
        "ndcg_at_k",
        "precision_at_k",
        "recall_at_k",
        "hit_rate_at_k",
        "mrr_at_k",
        "evaluated_users",
    )
    metrics: dict[str, float] = {}
    for name in metric_names:
        value = evaluation_report.get(name)
        if isinstance(value, int | float) and not isinstance(value, bool):
            metrics[name] = float(value)
    component_metrics = evaluation_report.get("component_metrics")
    if isinstance(component_metrics, Mapping):
        for component_name, component_payload in component_metrics.items():
            if not isinstance(component_name, str) or not isinstance(component_payload, Mapping):
                continue
            safe_component_name = _metric_name_part(component_name)
            for metric_name in metric_names:
                value = component_payload.get(metric_name)
                if isinstance(value, int | float) and not isinstance(value, bool):
                    metrics[f"component.{safe_component_name}.{metric_name}"] = float(value)
    baseline_summary = evaluation_report.get("baseline_summary")
    if isinstance(baseline_summary, Mapping):
        for name, value in baseline_summary.items():
            if (
                isinstance(name, str)
                and isinstance(value, int | float)
                and not isinstance(value, bool)
            ):
                metrics[f"baseline.{_metric_name_part(name)}"] = float(value)
    return metrics


def _metric_name_part(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def _environment_for(repo_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path if not current_pythonpath else f"{src_path}{os.pathsep}{current_pythonpath}"
    )
    return env


def _relative_path_param(
    hyperparameters: Mapping[str, object],
    key: str,
    default: str,
) -> Path:
    value = hyperparameters.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty relative path.")
    path = Path(value.strip())
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{key} must stay inside the external package repository.")
    return path


def _bool_param(hyperparameters: Mapping[str, object], key: str, default: bool) -> bool:
    value = hyperparameters.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean.")
    return value


def _int_param(
    hyperparameters: Mapping[str, object],
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = hyperparameters.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer.")
    if value < minimum or value > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return value


def _optional_int_param(
    hyperparameters: Mapping[str, object],
    key: str,
    default: object,
    minimum: int,
    maximum: int,
) -> int | None:
    value = hyperparameters.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer or null.")
    if value < minimum or value > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return value


def _float_param(
    hyperparameters: Mapping[str, object],
    key: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    value = hyperparameters.get(key, default)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric.")
    numeric = float(value)
    if numeric < minimum or numeric > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return numeric


def _tail(value: str, *, max_chars: int = 1200) -> str:
    cleaned = value.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[-max_chars:]
