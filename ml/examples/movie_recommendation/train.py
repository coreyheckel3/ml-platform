from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ml.examples.common import (
    average_precision_at_k,
    ndcg_at_k,
    read_csv_records,
    repo_root,
    round_metrics,
    write_json,
)

PROJECT_SLUG = "movie-recommendation"


def train(data_path: Path | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    root = repo_root()
    resolved_data_path = data_path or (
        root / "examples/projects/movie_recommendation/data/ratings.csv"
    )
    resolved_output_dir = output_dir or (root / f"artifacts/examples/{PROJECT_SLUG}")
    rows = read_csv_records(resolved_data_path)
    model = build_ranking_model(rows)
    ranked_lists = rank_candidates(rows, model)
    metrics = round_metrics(
        {
            "ndcg_at_10": sum(item["ndcg_at_10"] for item in ranked_lists) / len(ranked_lists),
            "map_at_10": sum(item["map_at_10"] for item in ranked_lists) / len(ranked_lists),
            "coverage": model["coverage"],
        }
    )
    artifact = {
        "schema_version": "forgeml.example_model_artifact.v1",
        "project_slug": PROJECT_SLUG,
        "algorithm": "aggregate-ranking-baseline",
        "metrics": metrics,
        "user_profiles": model["user_profiles"],
        "movie_profiles": model["movie_profiles"],
        "ranked_examples": ranked_lists,
    }
    evaluation = {
        "model_card": {
            "intended_use": "Rank candidate movies for signed-in members.",
            "serving_mode": "online ranking",
            "training_rows": len(rows),
        },
        "metrics": metrics,
        "artifact_path": "model.json",
    }
    summary = {
        "project_slug": PROJECT_SLUG,
        "output_dir": str(resolved_output_dir),
        "metrics": metrics,
        "artifact_paths": {
            "model": str(resolved_output_dir / "model.json"),
            "evaluation": str(resolved_output_dir / "evaluation.json"),
            "summary": str(resolved_output_dir / "summary.json"),
        },
    }
    write_json(resolved_output_dir / "model.json", artifact)
    write_json(resolved_output_dir / "evaluation.json", evaluation)
    write_json(resolved_output_dir / "summary.json", summary)
    return summary


def build_ranking_model(rows: list[dict[str, str]]) -> dict[str, Any]:
    ratings_by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    ratings_by_movie: dict[str, list[dict[str, str]]] = defaultdict(list)
    genre_counts: Counter[str] = Counter()
    for row in rows:
        ratings_by_user[row["user_id"]].append(row)
        ratings_by_movie[row["movie_id"]].append(row)
        genre_counts[row["genre"]] += 1

    user_profiles = {
        user_id: {
            "mean_rating": _mean(float(row["rating"]) for row in user_rows),
            "genre_affinity": _genre_affinity(user_rows),
            "rating_history_count": len(user_rows),
        }
        for user_id, user_rows in ratings_by_user.items()
    }
    movie_profiles = {
        movie_id: {
            "mean_rating": _mean(float(row["rating"]) for row in movie_rows),
            "genre": movie_rows[0]["genre"],
            "release_year": int(movie_rows[0]["release_year"]),
            "interaction_count": len(movie_rows),
        }
        for movie_id, movie_rows in ratings_by_movie.items()
    }
    recommendations = {
        user_id: [
            movie_id
            for movie_id, _score in sorted(
                (
                    (movie_id, score_movie(user_profile, movie_profile))
                    for movie_id, movie_profile in movie_profiles.items()
                ),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ]
        for user_id, user_profile in user_profiles.items()
    }
    covered_movies = {movie_id for movie_ids in recommendations.values() for movie_id in movie_ids}
    return {
        "user_profiles": user_profiles,
        "movie_profiles": movie_profiles,
        "genre_counts": dict(genre_counts),
        "coverage": len(covered_movies) / len(movie_profiles),
    }


def rank_candidates(rows: list[dict[str, str]], model: dict[str, Any]) -> list[dict[str, Any]]:
    observed_relevance = {
        (row["user_id"], row["movie_id"]): float(row["rating"]) / 5.0
        for row in rows
    }
    ranked_lists = []
    for user_id, user_profile in model["user_profiles"].items():
        scored_candidates = sorted(
            (
                (
                    movie_id,
                    score_movie(user_profile, movie_profile),
                    observed_relevance.get((user_id, movie_id), 0.0),
                )
                for movie_id, movie_profile in model["movie_profiles"].items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        relevances = [relevance for _movie_id, _score, relevance in scored_candidates]
        ranked_lists.append(
            {
                "user_id": user_id,
                "top_movies": [
                    {"movie_id": movie_id, "score": round(score, 6)}
                    for movie_id, score, _relevance in scored_candidates[:10]
                ],
                "ndcg_at_10": ndcg_at_k(relevances, 10),
                "map_at_10": average_precision_at_k(relevances, 10),
            }
        )
    return ranked_lists


def score_movie(user_profile: dict[str, Any], movie_profile: dict[str, Any]) -> float:
    genre_affinity = user_profile["genre_affinity"].get(movie_profile["genre"], 0.0)
    normalized_rating = movie_profile["mean_rating"] / 5.0
    normalized_recency = (movie_profile["release_year"] - 1990) / 40
    return (0.55 * normalized_rating) + (0.35 * genre_affinity) + (0.10 * normalized_recency)


def _genre_affinity(rows: list[dict[str, str]]) -> dict[str, float]:
    total_watch_seconds = sum(float(row["watch_seconds"]) for row in rows)
    if total_watch_seconds == 0:
        return {}
    by_genre: dict[str, float] = defaultdict(float)
    for row in rows:
        by_genre[row["genre"]] += float(row["watch_seconds"])
    return {
        genre: round(watch_seconds / total_watch_seconds, 6)
        for genre, watch_seconds in by_genre.items()
    }


def _mean(values: Any) -> float:
    value_list = list(values)
    return sum(value_list) / len(value_list)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ForgeML movie recommendation example.")
    parser.add_argument("--data-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = train(data_path=args.data_path, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
