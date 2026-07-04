"""
app/services/evaluation_service.py
------------------------------------
IR-style ranking quality evaluation metrics.
"""

from __future__ import annotations
import numpy as np


def precision_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    if k <= 0 or not ranked_ids:
        return 0.0
    hits = sum(1 for rid in ranked_ids[:k] if rid in relevant)
    return hits / min(k, len(ranked_ids))


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for rid in ranked_ids[:k] if rid in relevant)
    return hits / len(relevant)


def mean_reciprocal_rank(ranked_ids: list[str], relevant: set[str]) -> float:
    for rank, rid in enumerate(ranked_ids, start=1):
        if rid in relevant:
            return 1.0 / rank
    return 0.0


def evaluate(
    ranked_ids: list[str],
    relevant: set[str],
    k_values: list[int] = (3, 5, 10),
    cosine_scores: list[float] | None = None,
) -> dict:
    metrics: dict[str, float] = {}
    metrics["mrr"] = round(mean_reciprocal_rank(ranked_ids, relevant), 4)
    for k in k_values:
        metrics[f"precision@{k}"] = round(precision_at_k(ranked_ids, relevant, k), 4)
        metrics[f"recall@{k}"] = round(recall_at_k(ranked_ids, relevant, k), 4)
    avg_cos = float(np.mean(cosine_scores)) if cosine_scores else 0.0
    return {
        "mrr": metrics.pop("mrr"),
        "metrics": metrics,
        "average_cosine_similarity": round(avg_cos, 4),
    }
