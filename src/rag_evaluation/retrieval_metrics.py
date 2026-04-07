"""Traditional IR metrics for retrieval evaluation.

Computes Precision@K, Recall@K, MRR, and Hit Rate
against annotated golden evaluation pairs.
"""

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetrievalResult:
    """Results for a single retrieval query."""

    query_id: str
    query: str
    retrieved_ids: List[str]
    relevant_ids: List[str]
    precision_at_k: float
    recall_at_k: float
    mrr: float
    hit_rate: float
    similarity_scores: List[float] = field(default_factory=list)


def precision_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
    """Fraction of top-K retrieved docs that are relevant."""
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc in top_k if doc in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
    """Fraction of relevant docs found in top-K."""
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc in relevant if doc in top_k)
    return hits / len(relevant)


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """Reciprocal of rank of first relevant document."""
    for i, doc in enumerate(retrieved, 1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def hit_rate_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
    """1 if at least one relevant doc in top-K, else 0."""
    top_k = retrieved[:k]
    return 1.0 if any(doc in relevant for doc in top_k) else 0.0


def compute_all_metrics(
    retrieved: List[str], relevant: List[str], k: int = 5
) -> Dict[str, float]:
    """Compute all IR metrics for a single query."""
    return {
        "precision_at_k": precision_at_k(retrieved, relevant, k),
        "recall_at_k": recall_at_k(retrieved, relevant, k),
        "mrr": mean_reciprocal_rank(retrieved, relevant),
        "hit_rate": hit_rate_at_k(retrieved, relevant, k),
    }


def aggregate_metrics(results: List[RetrievalResult]) -> Dict[str, Dict[str, float]]:
    """Compute mean, stdev, min, max for all metrics across queries."""
    if not results:
        return {}

    metrics = {}
    for field_name in ["precision_at_k", "recall_at_k", "mrr", "hit_rate"]:
        values = [getattr(r, field_name) for r in results]
        metrics[field_name] = {
            "mean": round(statistics.mean(values), 4),
            "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "count": len(values),
        }
    return metrics
