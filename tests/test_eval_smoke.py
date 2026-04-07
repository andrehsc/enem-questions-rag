"""Smoke tests for RAG evaluation infrastructure.

Tests that DeepEval, Ollama integration, and golden eval dataset
are correctly configured.
"""

import json
from pathlib import Path

import pytest

from src.rag_evaluation.llm_provider import OllamaEvalLLM, get_eval_llm, is_ollama_available


# ──────────────────────────────────────────────────────────
# Unit tests (no external dependencies)
# ──────────────────────────────────────────────────────────


class TestLLMProvider:
    """Tests for LLM provider factory and adapter."""

    def test_ollama_eval_llm_init(self):
        llm = OllamaEvalLLM(model="llama3")
        assert llm.model_name == "llama3"
        assert "localhost" in llm.base_url
        assert llm.get_model_name() == "ollama/llama3"

    def test_ollama_eval_llm_custom_url(self):
        llm = OllamaEvalLLM(model="llama3", base_url="http://custom:11434")
        assert llm.base_url == "http://custom:11434"

    def test_ollama_eval_llm_load_model(self):
        llm = OllamaEvalLLM()
        assert llm.load_model() == "llama3"

    def test_get_eval_llm_default_is_ollama(self):
        llm = get_eval_llm("ollama")
        assert isinstance(llm, OllamaEvalLLM)

    def test_get_eval_llm_invalid_provider(self):
        with pytest.raises(ValueError, match="Unknown EVAL_LLM_PROVIDER"):
            get_eval_llm("invalid-provider")


class TestGoldenEvalDataset:
    """Tests for golden evaluation dataset structure and content."""

    @pytest.fixture(scope="class")
    def dataset(self):
        path = Path(__file__).parent / "fixtures" / "golden_eval_dataset.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_dataset_has_metadata(self, dataset):
        assert "metadata" in dataset
        assert dataset["metadata"]["version"] == "1.0"

    def test_dataset_has_retrieval_pairs(self, dataset):
        pairs = dataset["retrieval_pairs"]
        assert len(pairs) >= 30, f"Need >= 30 retrieval pairs, got {len(pairs)}"

    def test_dataset_has_generation_references(self, dataset):
        refs = dataset["generation_references"]
        assert len(refs) >= 20, f"Need >= 20 generation refs, got {len(refs)}"

    def test_retrieval_pair_structure(self, dataset):
        pair = dataset["retrieval_pairs"][0]
        assert "id" in pair
        assert "query" in pair
        assert "expected_question_ids" in pair
        assert "expected_db_ids" in pair
        assert "expected_subjects" in pair
        assert len(pair["expected_question_ids"]) >= 1

    def test_generation_reference_structure(self, dataset):
        ref = dataset["generation_references"][0]
        assert "id" in ref
        assert "input_topic" in ref
        assert "input_subject" in ref
        assert "source_question_id" in ref
        assert "evaluation_criteria" in ref

    def test_retrieval_covers_all_subjects(self, dataset):
        subjects = set()
        for pair in dataset["retrieval_pairs"]:
            subjects.update(pair["expected_subjects"])
        expected = {"ciencias_humanas", "ciencias_natureza", "linguagens", "matematica"}
        assert subjects == expected, f"Missing subjects: {expected - subjects}"

    def test_generation_covers_all_subjects(self, dataset):
        subjects = {ref["input_subject"] for ref in dataset["generation_references"]}
        expected = {"ciencias_humanas", "ciencias_natureza", "linguagens", "matematica"}
        assert subjects == expected, f"Missing subjects: {expected - subjects}"

    def test_retrieval_ids_are_unique(self, dataset):
        ids = [p["id"] for p in dataset["retrieval_pairs"]]
        assert len(ids) == len(set(ids)), "Duplicate retrieval pair IDs"

    def test_generation_ids_are_unique(self, dataset):
        ids = [r["id"] for r in dataset["generation_references"]]
        assert len(ids) == len(set(ids)), "Duplicate generation reference IDs"


# ──────────────────────────────────────────────────────────
# Integration tests (require Ollama running)
# ──────────────────────────────────────────────────────────

pytestmark_eval = pytest.mark.eval


@pytest.mark.eval
class TestOllamaIntegration:
    """Integration tests requiring Ollama to be running."""

    @pytest.fixture(autouse=True)
    def _skip_if_ollama_unavailable(self):
        if not is_ollama_available():
            pytest.skip("Ollama is not available")

    def test_ollama_generate_sync(self):
        llm = OllamaEvalLLM()
        response = llm.generate("Say hello in one word.")
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_ollama_generate_async(self):
        llm = OllamaEvalLLM()
        response = await llm.a_generate("Say hello in one word.")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_ollama_geval_smoke(self):
        """Smoke test: G-Eval with Ollama returns a score."""
        try:
            from deepeval.metrics import GEval
            from deepeval.test_case import LLMTestCase, LLMTestCaseParams
        except ImportError:
            pytest.skip("deepeval not installed — install with: pip install -e '.[eval]'")

        llm = OllamaEvalLLM()
        metric = GEval(
            name="Simple Quality",
            criteria="Rate if the text is well-written and factually correct. Scale: 1=poor, 2=fair, 3=good, 4=excellent.",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.25,
            model=llm,
        )
        test_case = LLMTestCase(
            input="Avalie este texto",
            actual_output="O Brasil é o maior país da América do Sul, com capital em Brasília.",
        )
        metric.measure(test_case)
        assert metric.score is not None
        assert 0.0 <= metric.score <= 1.0
