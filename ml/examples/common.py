from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_csv_records(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def auc_score(labels: list[int], scores: list[float]) -> float:
    positives = [
        (score, index)
        for index, (label, score) in enumerate(zip(labels, scores, strict=True))
        if label
    ]
    negatives = [
        (score, index)
        for index, (label, score) in enumerate(zip(labels, scores, strict=True))
        if not label
    ]
    if not positives or not negatives:
        return 0.0

    wins = 0.0
    for positive_score, positive_index in positives:
        for negative_score, negative_index in negatives:
            if positive_score > negative_score:
                wins += 1.0
            elif positive_score == negative_score and positive_index != negative_index:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def precision_at_fraction(labels: list[int], scores: list[float], fraction: float) -> float:
    ranked = _rank_labels(labels, scores)
    cutoff = max(1, math.ceil(len(ranked) * fraction))
    top_labels = ranked[:cutoff]
    return sum(top_labels) / len(top_labels)


def recall_at_fraction(labels: list[int], scores: list[float], fraction: float) -> float:
    positives = sum(labels)
    if positives == 0:
        return 0.0
    ranked = _rank_labels(labels, scores)
    cutoff = max(1, math.ceil(len(ranked) * fraction))
    return sum(ranked[:cutoff]) / positives


def ndcg_at_k(relevances: list[float], k: int) -> float:
    discounted_gain = _discounted_gain(relevances[:k])
    ideal_gain = _discounted_gain(sorted(relevances, reverse=True)[:k])
    return discounted_gain / ideal_gain if ideal_gain else 0.0


def average_precision_at_k(relevances: list[float], k: int, threshold: float = 0.8) -> float:
    hits = 0
    precision_sum = 0.0
    for index, relevance in enumerate(relevances[:k], start=1):
        if relevance >= threshold:
            hits += 1
            precision_sum += hits / index
    return precision_sum / hits if hits else 0.0


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def term_counts(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def round_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {name: round(value, 6) for name, value in metrics.items()}


def _rank_labels(labels: list[int], scores: list[float]) -> list[int]:
    return [
        label
        for label, _score in sorted(
            zip(labels, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _discounted_gain(relevances: list[float]) -> float:
    return sum(
        ((2**relevance) - 1) / math.log2(index + 2)
        for index, relevance in enumerate(relevances)
    )
