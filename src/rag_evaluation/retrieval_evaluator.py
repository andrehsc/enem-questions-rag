"""Retrieval evaluator: runs IR metrics over PgVectorSearch.

Evaluates retrieval quality across search modes (semantic, text, hybrid)
using golden evaluation dataset pairs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.rag_evaluation.retrieval_metrics import (
    RetrievalResult,
    aggregate_metrics,
    compute_all_metrics,
)


class RetrievalEvaluator:
    """Evaluates PgVectorSearch retrieval quality against golden pairs."""

    def __init__(self, search, k: int = 5):
        """
        Args:
            search: PgVectorSearch instance (or compatible with search_questions).
            k: Top-K for retrieval metrics.
        """
        self.search = search
        self.k = k

    async def evaluate(
        self,
        retrieval_pairs: List[Dict[str, Any]],
        search_modes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate retrieval over all pairs and modes.

        Args:
            retrieval_pairs: List of dicts with query, expected_db_ids, etc.
            search_modes: Modes to evaluate. Default: ["semantic", "text", "hybrid"].

        Returns:
            Dict keyed by mode with results and aggregate metrics.
        """
        if search_modes is None:
            search_modes = ["semantic", "text", "hybrid"]

        results_by_mode = {}
        for mode in search_modes:
            results = await self._evaluate_mode(retrieval_pairs, mode)
            agg = aggregate_metrics(results)
            results_by_mode[mode] = {
                "results": results,
                "aggregate": agg,
            }

        # Identify best mode by mean MRR
        best_mode = max(
            results_by_mode,
            key=lambda m: results_by_mode[m]["aggregate"].get("mrr", {}).get("mean", 0),
        )
        results_by_mode["_best_mode"] = best_mode

        return results_by_mode

    async def _evaluate_mode(
        self, retrieval_pairs: List[Dict], mode: str
    ) -> List[RetrievalResult]:
        """Run evaluation for a single search mode."""
        results = []
        for pair in retrieval_pairs:
            try:
                retrieved = await self.search.search_questions(
                    query=pair["query"],
                    limit=self.k,
                    search_mode=mode,
                )
            except Exception:
                retrieved = []

            # Extract IDs — use question_id (UUID str) from search results
            retrieved_ids = [str(r.get("question_id", "")) for r in retrieved]
            similarity_scores = [r.get("similarity_score", 0.0) for r in retrieved]

            # Expected IDs from golden eval dataset (db_ids = UUIDs)
            relevant_ids = pair.get("expected_db_ids", [])

            metrics = compute_all_metrics(retrieved_ids, relevant_ids, self.k)

            results.append(
                RetrievalResult(
                    query_id=pair["id"],
                    query=pair["query"],
                    retrieved_ids=retrieved_ids,
                    relevant_ids=relevant_ids,
                    precision_at_k=metrics["precision_at_k"],
                    recall_at_k=metrics["recall_at_k"],
                    mrr=metrics["mrr"],
                    hit_rate=metrics["hit_rate"],
                    similarity_scores=similarity_scores,
                )
            )
        return results

    def save_results(
        self,
        results: Dict[str, Any],
        output_dir: str = "reports",
        provider: str = "ollama",
    ) -> Path:
        """Save evaluation results to JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = output_path / f"retrieval_eval_{date_str}.json"

        # Convert RetrievalResult objects for JSON serialization
        serializable = {}
        for mode, data in results.items():
            if mode.startswith("_"):
                serializable[mode] = data
                continue
            serializable[mode] = {
                "aggregate": data["aggregate"],
                "query_count": len(data["results"]),
                "details": [
                    {
                        "query_id": r.query_id,
                        "query": r.query,
                        "precision_at_k": r.precision_at_k,
                        "recall_at_k": r.recall_at_k,
                        "mrr": r.mrr,
                        "hit_rate": r.hit_rate,
                        "retrieved_count": len(r.retrieved_ids),
                        "relevant_count": len(r.relevant_ids),
                    }
                    for r in data["results"]
                ],
            }

        output = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "k": self.k,
            "modes": serializable,
        }

        filepath.write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return filepath
