from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from ml.examples.common import repo_root, write_json
from ml.examples.fraud_detection.train import train as train_fraud_detection
from ml.examples.movie_recommendation.train import train as train_movie_recommendation
from ml.examples.semantic_search.build_index import train as train_semantic_search

Trainer = Callable[..., dict[str, Any]]
TRAINERS: dict[str, Trainer] = {
    "fraud-detection": train_fraud_detection,
    "movie-recommendation": train_movie_recommendation,
    "semantic-search": train_semantic_search,
}


def run_training(
    *,
    output_dir: Path | None = None,
    selected_projects: Iterable[str] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = output_dir or (repo_root() / "artifacts/examples")
    selected_slugs = list(selected_projects or TRAINERS)
    unknown_projects = sorted(set(selected_slugs) - set(TRAINERS))
    if unknown_projects:
        raise ValueError(f"Unknown example project(s): {', '.join(unknown_projects)}")

    summaries = [
        TRAINERS[slug](output_dir=resolved_output_dir / slug)
        for slug in selected_slugs
    ]
    manifest = {
        "schema_version": "forgeml.example_training_manifest.v1",
        "artifact_root": str(resolved_output_dir),
        "project_count": len(summaries),
        "projects": summaries,
    }
    write_json(resolved_output_dir / "training-summary.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic local ForgeML example training jobs."
    )
    parser.add_argument(
        "--project",
        action="append",
        choices=sorted(TRAINERS),
        help="Example project slug to train. Repeat the flag to train multiple projects.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root() / "artifacts/examples",
    )
    args = parser.parse_args()
    manifest = run_training(
        output_dir=args.output_dir,
        selected_projects=args.project,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
