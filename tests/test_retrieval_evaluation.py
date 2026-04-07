"""Tests for retrieval evaluation metrics and evaluator.

Unit tests use known values; integration tests use mock search.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.rag_evaluation.retrieval_metrics import (
    RetrievalResult,
    aggregate_metrics,
    compute_all_metrics,
    hit_rate_at_k,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)
from src.rag_evaluation.retrieval_evaluator import RetrievalEvaluator


# ──────────────────────────────────────────────────────────
# Unit tests for individual metrics
# ──────────────────────────────────────────────────────────


class TestPrecisionAtK:
    def test_all_relevant(self):
        assert precision_at_k(["a", "b", "c"], ["a", "b", "c"], k=3) == 1.0

    def test_none_relevant(self):
        assert precision_at_k(["x", "y", "z"], ["a", "b"], k=3) == 0.0

    def test_partial_relevant(self):
        assert precision_at_k(["a", "x", "b"], ["a", "b"], k=3) == pytest.approx(2 / 3)

    def test_k_limits_results(self):
        # Only top-2 considered; "b" at position 3 is excluded
        assert precision_at_k(["a", "x", "b"], ["a", "b"], k=2) == 0.5

    def test_empty_retrieved(self):
        assert precision_at_k([], ["a"], k=5) == 0.0

    def test_empty_relevant(self):
        assert precision_at_k(["a", "b"], [], k=5) == 0.0


class TestRecallAtK:
    def test_all_found(self):
        assert recall_at_k(["a", "b", "c"], ["a", "b"], k=3) == 1.0

    def test_none_found(self):
        assert recall_at_k(["x", "y"], ["a", "b"], k=2) == 0.0

    def test_partial_found(self):
        assert recall_at_k(["a", "x"], ["a", "b"], k=2) == 0.5

    def test_empty_relevant_returns_zero(self):
        assert recall_at_k(["a"], [], k=5) == 0.0

    def test_k_limits_search(self):
        # "b" is at pos 3 but k=2
        assert recall_at_k(["x", "a", "b"], ["a", "b"], k=2) == 0.5


class TestMRR:
    def test_first_position(self):
        assert mean_reciprocal_rank(["a", "b"], ["a"]) == 1.0

    def test_second_position(self):
        assert mean_reciprocal_rank(["x", "a"], ["a"]) == 0.5

    def test_third_position(self):
        assert mean_reciprocal_rank(["x", "y", "a"], ["a"]) == pytest.approx(1 / 3)

    def test_not_found(self):
        assert mean_reciprocal_rank(["x", "y"], ["a"]) == 0.0

    def test_multiple_relevant_returns_first(self):
        # MRR only cares about the first relevant
        assert mean_reciprocal_rank(["x", "a", "b"], ["a", "b"]) == 0.5


class TestHitRate:
    def test_hit(self):
        assert hit_rate_at_k(["x", "a"], ["a"], k=2) == 1.0

    def test_miss(self):
        assert hit_rate_at_k(["x", "y"], ["a"], k=2) == 0.0

    def test_hit_outside_k(self):
        assert hit_rate_at_k(["x", "y", "a"], ["a"], k=2) == 0.0


class TestComputeAllMetrics:
    def test_perfect_retrieval(self):
        m = compute_all_metrics(["a", "b"], ["a", "b"], k=5)
        assert m["precision_at_k"] == 1.0
        assert m["recall_at_k"] == 1.0
        assert m["mrr"] == 1.0
        assert m["hit_rate"] == 1.0

    def test_zero_retrieval(self):
        m = compute_all_metrics(["x", "y"], ["a", "b"], k=5)
        assert m["precision_at_k"] == 0.0
        assert m["recall_at_k"] == 0.0
        assert m["mrr"] == 0.0
        assert m["hit_rate"] == 0.0


class TestAggregateMetrics:
    def test_aggregate_single(self):
        results = [
            RetrievalResult("q1", "query", [], [], 0.8, 0.6, 1.0, 1.0)
        ]
        agg = aggregate_metrics(results)
        assert agg["precision_at_k"]["mean"] == 0.8
        assert agg["precision_at_k"]["stdev"] == 0.0

    def test_aggregate_multiple(self):
        results = [
            RetrievalResult("q1", "q", [], [], 1.0, 1.0, 1.0, 1.0),
            RetrievalResult("q2", "q", [], [], 0.0, 0.0, 0.0, 0.0),
        ]
        agg = aggregate_metrics(results)
        assert agg["precision_at_k"]["mean"] == 0.5
        assert agg["mrr"]["mean"] == 0.5

    def test_aggregate_empty(self):
        assert aggregate_metrics([]) == {}


# ──────────────────────────────────────────────────────────
# Integration tests with mock PgVectorSearch
# ──────────────────────────────────────────────────────────


class TestRetrievalEvaluator:
    @pytest.fixture
    def mock_search(self):
        search = AsyncMock()
        # Return fake results: question_id matches first expected_db_id
        search.search_questions = AsyncMock(
            return_value=[
                {"question_id": "uuid-1", "full_text": "text", "similarity_score": 0.9},
                {"question_id": "uuid-2", "full_text": "text", "similarity_score": 0.8},
            ]
        )
        return search

    @pytest.fixture
    def sample_pairs(self):
        return [
            {
                "id": "ret-001",
                "query": "febre amarela",
                "expected_db_ids": ["uuid-1"],
                "expected_subjects": ["ciencias_humanas"],
            },
            {
                "id": "ret-002",
                "query": "seleção natural",
                "expected_db_ids": ["uuid-3"],
                "expected_subjects": ["ciencias_natureza"],
            },
        ]

    @pytest.mark.asyncio
    async def test_evaluate_returns_all_modes(self, mock_search, sample_pairs):
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["hybrid"])
        assert "hybrid" in results
        assert "_best_mode" in results

    @pytest.mark.asyncio
    async def test_evaluate_computes_metrics(self, mock_search, sample_pairs):
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["hybrid"])
        agg = results["hybrid"]["aggregate"]
        assert "precision_at_k" in agg
        assert "recall_at_k" in agg
        assert "mrr" in agg
        assert "hit_rate" in agg

    @pytest.mark.asyncio
    async def test_evaluate_correct_hit(self, mock_search, sample_pairs):
        # First pair has uuid-1 as expected, and mock returns uuid-1 first
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["semantic"])
        r = results["semantic"]["results"][0]
        assert r.query_id == "ret-001"
        assert r.hit_rate == 1.0
        assert r.mrr == 1.0

    @pytest.mark.asyncio
    async def test_evaluate_correct_miss(self, mock_search, sample_pairs):
        # Second pair has uuid-3 as expected, but mock returns uuid-1, uuid-2
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["semantic"])
        r = results["semantic"]["results"][1]
        assert r.query_id == "ret-002"
        assert r.hit_rate == 0.0
        assert r.mrr == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_multiple_modes(self, mock_search, sample_pairs):
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(
            sample_pairs, search_modes=["semantic", "text", "hybrid"]
        )
        assert "semantic" in results
        assert "text" in results
        assert "hybrid" in results

    @pytest.mark.asyncio
    async def test_save_results(self, mock_search, sample_pairs, tmp_path):
        evaluator = RetrievalEvaluator(search=mock_search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["hybrid"])
        filepath = evaluator.save_results(results, output_dir=str(tmp_path))
        assert filepath.exists()
        import json

        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert "modes" in data

    @pytest.mark.asyncio
    async def test_search_error_handled(self, sample_pairs):
        """If search raises, evaluator should still return results (empty)."""
        search = AsyncMock()
        search.search_questions = AsyncMock(side_effect=Exception("DB down"))
        evaluator = RetrievalEvaluator(search=search, k=5)
        results = await evaluator.evaluate(sample_pairs, search_modes=["hybrid"])
        for r in results["hybrid"]["results"]:
            assert r.hit_rate == 0.0
