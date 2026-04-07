"""Tests for generation evaluation: rubric, evaluator, and metrics."""

import pytest
from unittest.mock import MagicMock, patch

from src.rag_evaluation.enem_rubric import ENEM_RUBRIC
from src.rag_evaluation.generation_evaluator import (
    GenerationEvaluator,
    GenerationResult,
)


# ──────────────────────────────────────────────────────────
# Unit tests (no DeepEval/Ollama required)
# ──────────────────────────────────────────────────────────


class TestENEMRubric:
    def test_rubric_contains_scale(self):
        assert "1:" in ENEM_RUBRIC
        assert "2:" in ENEM_RUBRIC
        assert "3:" in ENEM_RUBRIC
        assert "4:" in ENEM_RUBRIC

    def test_rubric_contains_criteria(self):
        assert "Formato ENEM" in ENEM_RUBRIC
        assert "alternativas" in ENEM_RUBRIC
        assert "pedagógica" in ENEM_RUBRIC or "Qualidade" in ENEM_RUBRIC

    def test_rubric_is_string(self):
        assert isinstance(ENEM_RUBRIC, str)
        assert len(ENEM_RUBRIC) > 100


class TestGenerationResult:
    def test_to_dict(self):
        result = GenerationResult(
            ref_id="gen-001",
            input_topic="meio ambiente",
            faithfulness_score=0.85,
            faithfulness_reason="All claims supported",
            enem_geval_score=0.75,
            enem_geval_reason="Good format, could improve distrators",
        )
        d = result.to_dict()
        assert d["ref_id"] == "gen-001"
        assert d["faithfulness_score"] == 0.85
        assert d["enem_geval_score"] == 0.75

    def test_to_dict_with_none_scores(self):
        result = GenerationResult(ref_id="gen-002", input_topic="biologia")
        d = result.to_dict()
        assert d["faithfulness_score"] is None
        assert d["enem_geval_score"] is None


class TestGenerationEvaluator:
    @pytest.fixture
    def mock_llm(self):
        return MagicMock()

    @pytest.fixture
    def sample_refs(self):
        return [
            {
                "id": "gen-001",
                "input_topic": "meio ambiente e febre amarela",
                "input_subject": "ciencias_humanas",
                "source_question_id": "gs-001",
                "evaluation_criteria": ["formato_enem"],
            },
            {
                "id": "gen-002",
                "input_topic": "seleção natural e evolução",
                "input_subject": "ciencias_natureza",
                "source_question_id": "gs-024",
                "evaluation_criteria": ["formato_enem"],
            },
        ]

    @pytest.fixture
    def sample_golden_map(self):
        return {
            "gs-001": {
                "question_text": "Uma questão sobre febre amarela e meio ambiente...",
                "alternatives": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            },
            "gs-024": {
                "question_text": "Uma questão sobre seleção natural...",
                "alternatives": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            },
        }

    def test_init(self, mock_llm):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        assert evaluator.faithfulness_threshold == 0.7
        assert evaluator.geval_threshold == 0.5

    def test_build_summary_empty(self, mock_llm):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        summary = evaluator._build_summary([])
        assert summary["count"] == 0

    def test_build_summary_with_results(self, mock_llm):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        results = [
            GenerationResult("g1", "topic1", enem_geval_score=0.75),
            GenerationResult("g2", "topic2", enem_geval_score=0.50),
            GenerationResult("g3", "topic3", enem_geval_score=0.25),
        ]
        summary = evaluator._build_summary(results)
        assert summary["count"] == 3
        assert "enem_geval_aggregate" in summary
        assert summary["enem_geval_aggregate"]["mean"] == 0.5
        assert summary["enem_geval_aggregate"]["min"] == 0.25
        assert summary["enem_geval_aggregate"]["max"] == 0.75

    def test_build_summary_worst_cases(self, mock_llm):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        results = [
            GenerationResult("g1", "t1", enem_geval_score=0.9),
            GenerationResult("g2", "t2", enem_geval_score=0.1),
            GenerationResult("g3", "t3", enem_geval_score=0.5),
        ]
        summary = evaluator._build_summary(results)
        assert len(summary["worst_cases"]) == 3
        assert summary["worst_cases"][0]["ref_id"] == "g2"  # lowest score first

    def test_build_summary_faithfulness_aggregate(self, mock_llm):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        results = [
            GenerationResult("g1", "t1", faithfulness_score=0.8),
            GenerationResult("g2", "t2", faithfulness_score=0.6),
        ]
        summary = evaluator._build_summary(results)
        assert "faithfulness_aggregate" in summary
        assert summary["faithfulness_aggregate"]["mean"] == 0.7

    def test_evaluate_batch_no_golden(self, mock_llm, sample_refs):
        """Batch eval without golden questions uses placeholder text."""
        evaluator = GenerationEvaluator(eval_llm=mock_llm)

        # Patch the metric calls to avoid needing DeepEval
        with patch.object(evaluator, "evaluate_question") as mock_eval:
            mock_eval.return_value = GenerationResult(
                "gen-001", "topic", enem_geval_score=0.75
            )
            summary = evaluator.evaluate_batch(sample_refs)
            assert summary["count"] == 2

    def test_evaluate_batch_with_golden(self, mock_llm, sample_refs, sample_golden_map):
        """Batch eval with golden questions uses real question text."""
        evaluator = GenerationEvaluator(eval_llm=mock_llm)

        with patch.object(evaluator, "evaluate_question") as mock_eval:
            mock_eval.return_value = GenerationResult(
                "gen-001", "topic", enem_geval_score=0.75
            )
            summary = evaluator.evaluate_batch(sample_refs, sample_golden_map)
            # Check that the golden question text was passed
            calls = mock_eval.call_args_list
            assert "febre amarela" in calls[0].kwargs.get("generated_question", "")

    def test_save_results(self, mock_llm, tmp_path):
        evaluator = GenerationEvaluator(eval_llm=mock_llm)
        results = {
            "count": 1,
            "results": [{"ref_id": "gen-001", "enem_geval_score": 0.75}],
        }
        filepath = evaluator.save_results(results, output_dir=str(tmp_path))
        assert filepath.exists()
        import json

        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert data["count"] == 1
