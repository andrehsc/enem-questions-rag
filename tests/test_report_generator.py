"""Tests for report generator and E2E pipeline config."""

import pytest

from src.rag_evaluation.report_generator import (
    generate_markdown_report,
    _header,
    _executive_summary,
    _retrieval_scores_table,
    _search_mode_comparison,
    _generation_scores_table,
    _worst_cases,
    _recommendations,
)
from src.rag_evaluation.retrieval_metrics import RetrievalResult


@pytest.fixture
def sample_retrieval_results():
    """Mock retrieval results for report testing."""
    results = [
        RetrievalResult("q1", "febre amarela", [], [], 0.80, 0.60, 1.0, 1.0),
        RetrievalResult("q2", "seleção natural", [], [], 0.40, 0.40, 0.50, 1.0),
        RetrievalResult("q3", "criptografia", [], [], 0.00, 0.00, 0.00, 0.0),
    ]
    return {
        "semantic": {
            "results": results,
            "aggregate": {
                "precision_at_k": {"mean": 0.35, "stdev": 0.20, "min": 0.0, "max": 0.80},
                "recall_at_k": {"mean": 0.30, "stdev": 0.15, "min": 0.0, "max": 0.60},
                "mrr": {"mean": 0.45, "stdev": 0.25, "min": 0.0, "max": 1.0},
                "hit_rate": {"mean": 0.60, "stdev": 0.20, "min": 0.0, "max": 1.0},
            },
        },
        "text": {
            "results": results,
            "aggregate": {
                "precision_at_k": {"mean": 0.30, "stdev": 0.15, "min": 0.0, "max": 0.60},
                "recall_at_k": {"mean": 0.25, "stdev": 0.12, "min": 0.0, "max": 0.50},
                "mrr": {"mean": 0.40, "stdev": 0.20, "min": 0.0, "max": 0.80},
                "hit_rate": {"mean": 0.55, "stdev": 0.18, "min": 0.0, "max": 1.0},
            },
        },
        "hybrid": {
            "results": results,
            "aggregate": {
                "precision_at_k": {"mean": 0.45, "stdev": 0.18, "min": 0.0, "max": 0.80},
                "recall_at_k": {"mean": 0.40, "stdev": 0.16, "min": 0.0, "max": 0.60},
                "mrr": {"mean": 0.55, "stdev": 0.22, "min": 0.0, "max": 1.0},
                "hit_rate": {"mean": 0.70, "stdev": 0.15, "min": 0.0, "max": 1.0},
            },
        },
        "_best_mode": "hybrid",
    }


@pytest.fixture
def sample_generation_results():
    """Mock generation results for report testing."""
    return {
        "count": 3,
        "faithfulness_aggregate": {
            "mean": 0.82,
            "stdev": 0.10,
            "min": 0.65,
            "max": 0.95,
        },
        "enem_geval_aggregate": {
            "mean": 0.68,
            "stdev": 0.15,
            "min": 0.40,
            "max": 0.90,
        },
        "worst_cases": [
            {"ref_id": "gen-003", "input_topic": "química orgânica", "enem_geval_score": 0.40},
            {"ref_id": "gen-007", "input_topic": "ecologia", "enem_geval_score": 0.50},
        ],
        "results": [],
    }


@pytest.fixture
def sample_config():
    return {
        "date": "2026-04-06",
        "provider": "ollama/llama3",
        "k": 5,
        "dataset_version": "1.0",
    }


class TestReportHeader:
    def test_contains_date(self, sample_config):
        header = _header(sample_config)
        assert "2026-04-06" in header

    def test_contains_provider(self, sample_config):
        header = _header(sample_config)
        assert "ollama/llama3" in header

    def test_contains_k(self, sample_config):
        header = _header(sample_config)
        assert "5" in header


class TestExecutiveSummary:
    def test_contains_metrics(self, sample_retrieval_results, sample_generation_results):
        summary = _executive_summary(sample_retrieval_results, sample_generation_results)
        assert "MRR=" in summary
        assert "Precision@K=" in summary
        assert "Faithfulness:" in summary


class TestRetrievalScoresTable:
    def test_has_table_rows(self, sample_retrieval_results):
        table = _retrieval_scores_table(sample_retrieval_results)
        assert "Precision@K" in table
        assert "Recall@K" in table
        assert "MRR" in table
        assert "Hit Rate" in table

    def test_has_two_decimal_places(self, sample_retrieval_results):
        table = _retrieval_scores_table(sample_retrieval_results)
        assert "0.45" in table  # precision mean
        assert "0.55" in table  # mrr mean


class TestSearchModeComparison:
    def test_has_all_modes(self, sample_retrieval_results):
        table = _search_mode_comparison(sample_retrieval_results)
        assert "Semantic" in table
        assert "Text" in table
        assert "Hybrid" in table

    def test_highlights_best_mode(self, sample_retrieval_results):
        table = _search_mode_comparison(sample_retrieval_results)
        assert "**" in table  # Bold formatting for best mode


class TestGenerationScoresTable:
    def test_has_metrics(self, sample_generation_results):
        table = _generation_scores_table(sample_generation_results)
        assert "Faithfulness" in table
        assert "ENEM G-Eval" in table

    def test_empty_results(self):
        table = _generation_scores_table({})
        assert "No generation results" in table


class TestWorstCases:
    def test_has_retrieval_worst(self, sample_retrieval_results, sample_generation_results):
        wc = _worst_cases(sample_retrieval_results, sample_generation_results)
        assert "Retrieval" in wc

    def test_has_generation_worst(self, sample_retrieval_results, sample_generation_results):
        wc = _worst_cases(sample_retrieval_results, sample_generation_results)
        assert "Generation" in wc
        assert "gen-003" in wc


class TestRecommendations:
    def test_low_mrr_recommendation(self):
        retrieval = {"hybrid": {"aggregate": {"mrr": {"mean": 0.3}, "precision_at_k": {"mean": 0.6}, "recall_at_k": {"mean": 0.6}}}}
        generation = {}
        recs = _recommendations(retrieval, generation)
        assert "hybrid search" in recs.lower() or "MRR" in recs

    def test_no_issues(self):
        retrieval = {"hybrid": {"aggregate": {"mrr": {"mean": 0.8}, "precision_at_k": {"mean": 0.8}, "recall_at_k": {"mean": 0.8}}}}
        generation = {"faithfulness_aggregate": {"mean": 0.9}, "enem_geval_aggregate": {"mean": 0.8}}
        recs = _recommendations(retrieval, generation)
        assert "No critical issues" in recs


class TestFullReport:
    def test_generate_complete_report(
        self, sample_retrieval_results, sample_generation_results, sample_config
    ):
        report = generate_markdown_report(
            sample_retrieval_results, sample_generation_results, sample_config
        )
        assert "# RAG Evaluation Report" in report
        assert "Resumo Executivo" in report
        assert "Retrieval Metrics" in report
        assert "Search Mode Comparison" in report
        assert "Generation Metrics" in report
        assert "Worst Cases" in report
        assert "Recommendations" in report

    def test_report_has_two_decimal_precision(
        self, sample_retrieval_results, sample_generation_results, sample_config
    ):
        report = generate_markdown_report(
            sample_retrieval_results, sample_generation_results, sample_config
        )
        # Check decimal formatting (0.XX pattern)
        assert "0.45" in report or "0.55" in report

    def test_report_with_empty_results(self, sample_config):
        report = generate_markdown_report({}, {}, sample_config)
        assert "# RAG Evaluation Report" in report
