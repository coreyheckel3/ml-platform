from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from ml.examples.common import (
    cosine_similarity,
    read_jsonl,
    repo_root,
    round_metrics,
    term_counts,
    tokenize,
    write_json,
)

PROJECT_SLUG = "semantic-search"
EVALUATION_QUERIES = [
    ("feature freshness delayed materialization", "d001"),
    ("approve model before production", "d002"),
    ("serving validation failures", "d003"),
    ("dataset schema compatibility rules", "d004"),
    ("canary rollback deployment", "d005"),
    ("feature drift production windows", "d006"),
]


def train(data_path: Path | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    root = repo_root()
    resolved_data_path = data_path or (
        root / "examples/projects/semantic_search/data/documents.jsonl"
    )
    resolved_output_dir = output_dir or (root / f"artifacts/examples/{PROJECT_SLUG}")
    documents = read_jsonl(resolved_data_path)
    index = build_tfidf_index(documents)
    ranked_queries = [rank_query(query, index) for query, _expected in EVALUATION_QUERIES]
    metrics = round_metrics(evaluate_queries(ranked_queries))
    artifact = {
        "schema_version": "forgeml.example_model_artifact.v1",
        "project_slug": PROJECT_SLUG,
        "algorithm": "tfidf-cosine-retriever",
        "metrics": metrics,
        "document_count": len(documents),
        "vocabulary_size": len(index["idf"]),
        "documents": index["document_metadata"],
        "query_examples": ranked_queries,
    }
    evaluation = {
        "model_card": {
            "intended_use": "Retrieve internal ML platform documentation passages.",
            "serving_mode": "online vector retrieval",
            "indexed_documents": len(documents),
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


def build_tfidf_index(documents: list[dict[str, Any]]) -> dict[str, Any]:
    tokenized_documents = [
        (
            document,
            term_counts(
                tokenize(
                    " ".join(
                        [
                            str(document["title"]),
                            str(document["body"]),
                            str(document["category"]),
                        ]
                    )
                )
            ),
        )
        for document in documents
    ]
    document_frequency: Counter[str] = Counter()
    for _document, counts in tokenized_documents:
        document_frequency.update(counts.keys())
    document_count = len(documents)
    idf = {
        token: math.log((document_count + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }
    vectors = {
        str(document["doc_id"]): _tfidf_vector(counts, idf)
        for document, counts in tokenized_documents
    }
    return {
        "idf": idf,
        "vectors": vectors,
        "document_metadata": [
            {
                "doc_id": document["doc_id"],
                "title": document["title"],
                "category": document["category"],
            }
            for document in documents
        ],
    }


def rank_query(query: str, index: dict[str, Any]) -> dict[str, Any]:
    query_vector = _tfidf_vector(term_counts(tokenize(query)), index["idf"])
    ranked = sorted(
        (
            {
                "doc_id": doc_id,
                "score": cosine_similarity(query_vector, document_vector),
            }
            for doc_id, document_vector in index["vectors"].items()
        ),
        key=lambda item: item["score"],
        reverse=True,
    )
    expected_doc_id = dict(EVALUATION_QUERIES)[query]
    return {
        "query": query,
        "expected_doc_id": expected_doc_id,
        "ranked_documents": [
            {"doc_id": item["doc_id"], "score": round(item["score"], 6)}
            for item in ranked[:10]
        ],
    }


def evaluate_queries(ranked_queries: list[dict[str, Any]]) -> dict[str, float]:
    recall_hits = 0
    reciprocal_rank_sum = 0.0
    for query_result in ranked_queries:
        ranked_doc_ids = [item["doc_id"] for item in query_result["ranked_documents"]]
        expected_doc_id = query_result["expected_doc_id"]
        if expected_doc_id in ranked_doc_ids[:5]:
            recall_hits += 1
        if expected_doc_id in ranked_doc_ids[:10]:
            reciprocal_rank_sum += 1 / (ranked_doc_ids.index(expected_doc_id) + 1)
    return {
        "recall_at_5": recall_hits / len(ranked_queries),
        "mrr_at_10": reciprocal_rank_sum / len(ranked_queries),
        "embedding_coverage": 1.0,
    }


def _tfidf_vector(counts: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {
        token: (count / total) * idf[token]
        for token, count in counts.items()
        if token in idf
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ForgeML semantic search index.")
    parser.add_argument("--data-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = train(data_path=args.data_path, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
