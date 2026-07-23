from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ml.examples.common import (
    auc_score,
    precision_at_fraction,
    read_csv_records,
    recall_at_fraction,
    repo_root,
    round_metrics,
    sigmoid,
    write_json,
)

FEATURE_NAMES = [
    "bias",
    "amount_zscore",
    "merchant_risk_score",
    "account_velocity_1h",
    "cross_border",
]
PROJECT_SLUG = "fraud-detection"


def train(
    data_path: Path | None = None,
    output_dir: Path | None = None,
    *,
    epochs: int = 500,
    learning_rate: float = 0.18,
) -> dict[str, Any]:
    root = repo_root()
    resolved_data_path = data_path or (
        root / "examples/projects/fraud_detection/data/transactions.csv"
    )
    resolved_output_dir = output_dir or (root / f"artifacts/examples/{PROJECT_SLUG}")
    rows = read_csv_records(resolved_data_path)
    feature_rows = build_feature_rows(rows)
    labels = [int(row["is_fraud"]) for row in rows]
    weights = fit_logistic_regression(
        [row["features"] for row in feature_rows],
        labels,
        epochs=epochs,
        learning_rate=learning_rate,
    )
    scores = [
        sigmoid(
            sum(
                weight * value
                for weight, value in zip(weights, row["features"], strict=True)
            )
        )
        for row in feature_rows
    ]
    metrics = round_metrics(
        {
            "auc": auc_score(labels, scores),
            "precision_at_1_percent": precision_at_fraction(labels, scores, 0.01),
            "recall_at_5_percent": recall_at_fraction(labels, scores, 0.05),
        }
    )
    artifact = {
        "schema_version": "forgeml.example_model_artifact.v1",
        "project_slug": PROJECT_SLUG,
        "algorithm": "logistic-regression-sgd",
        "feature_names": FEATURE_NAMES,
        "weights": [round(weight, 8) for weight in weights],
        "metrics": metrics,
        "training_rows": len(rows),
        "scored_examples": [
            {
                "transaction_id": row["transaction_id"],
                "score": round(score, 6),
                "label": label,
            }
            for row, score, label in zip(rows, scores, labels, strict=True)
        ],
    }
    evaluation = {
        "model_card": {
            "intended_use": "Score card transactions for fraud risk before authorization.",
            "serving_mode": "online classification",
            "training_rows": len(rows),
        },
        "metrics": metrics,
        "feature_names": FEATURE_NAMES,
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


def build_feature_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    amounts = [float(row["amount"]) for row in rows]
    amount_mean = sum(amounts) / len(amounts)
    amount_std = math.sqrt(
        sum((amount - amount_mean) ** 2 for amount in amounts) / len(amounts)
    )
    category_counts: Counter[str] = Counter(row["merchant_category"] for row in rows)
    category_frauds: Counter[str] = Counter(
        row["merchant_category"] for row in rows if int(row["is_fraud"])
    )
    category_risk = {
        category: (category_frauds[category] + 1) / (count + 2)
        for category, count in category_counts.items()
    }
    previous_events: dict[str, list[datetime]] = defaultdict(list)
    feature_rows: list[dict[str, Any]] = []

    for row in sorted(rows, key=lambda item: item["event_timestamp"]):
        timestamp = datetime.fromisoformat(row["event_timestamp"].replace("Z", "+00:00"))
        account_id = row["account_id"]
        one_hour_ago = timestamp - timedelta(hours=1)
        recent_events = [
            event_time
            for event_time in previous_events[account_id]
            if event_time >= one_hour_ago
        ]
        previous_events[account_id] = [*recent_events, timestamp]
        amount_zscore = (float(row["amount"]) - amount_mean) / (amount_std or 1.0)
        features = [
            1.0,
            amount_zscore,
            category_risk[row["merchant_category"]],
            float(len(recent_events)),
            1.0 if row["country"] != "US" else 0.0,
        ]
        feature_rows.append(
            {
                "transaction_id": row["transaction_id"],
                "features": features,
            }
        )
    feature_by_id = {row["transaction_id"]: row for row in feature_rows}
    return [feature_by_id[row["transaction_id"]] for row in rows]


def fit_logistic_regression(
    features: list[list[float]],
    labels: list[int],
    *,
    epochs: int,
    learning_rate: float,
) -> list[float]:
    weights = [0.0 for _feature in FEATURE_NAMES]
    for _epoch in range(epochs):
        for row, label in zip(features, labels, strict=True):
            prediction = sigmoid(
                sum(weight * value for weight, value in zip(weights, row, strict=True))
            )
            error = prediction - label
            for index, value in enumerate(row):
                weights[index] -= learning_rate * error * value / len(features)
    return weights


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ForgeML fraud detection example.")
    parser.add_argument("--data-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = train(data_path=args.data_path, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
