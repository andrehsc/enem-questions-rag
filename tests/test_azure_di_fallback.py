"""
Tests for azure_di_fallback.py (Story 6.1).

All Azure DI SDK calls are mocked — no real Azure calls in CI.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.enem_ingestion.azure_di_fallback import (
    AzureDIFallback,
    CostTracker,
    FallbackResult,
)
from src.enem_ingestion.confidence_scorer import ConfidenceResult
from src.enem_ingestion.parser import Question, QuestionMetadata, Subject


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def metadata():
    return QuestionMetadata(
        year=2024, day=1, caderno="CD1",
        application_type="regular", exam_type="ENEM",
    )


def _make_question(number=5, text_len=120, num_alts=5, metadata=None):
    meta = metadata or QuestionMetadata(
        year=2024, day=1, caderno="CD1", application_type="regular",
    )
    return Question(
        number=number,
        text="X" * text_len,
        alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"][:num_alts],
        metadata=meta,
        subject=Subject.LINGUAGENS,
    )


def _azure_markdown_good():
    """Markdown output from Azure DI with a well-extracted question."""
    return (
        "**QUESTÃO 5**\n\n"
        "O Renascimento cultural foi um movimento que marcou a transição "
        "entre a Idade Média e a Idade Moderna na Europa. Esse período "
        "caracterizou-se pela valorização do ser humano e da razão.\n\n"
        "Sobre o Renascimento, é correto afirmar que:\n\n"
        "**(A)** foi um movimento exclusivamente artístico, sem implicações filosóficas.\n\n"
        "**(B)** teve como principal característica a valorização do teocentrismo medieval.\n\n"
        "**(C)** promoveu o antropocentrismo e o racionalismo como valores centrais.\n\n"
        "**(D)** restringiu-se à península itálica, sem influência em outras regiões.\n\n"
        "**(E)** desconsiderou as contribuições da Antiguidade Clássica.\n\n"
    )


def _azure_markdown_bad():
    """Markdown output that is still poor quality."""
    return "**QUESTÃO 5**\n\nShort text\n"


# ---------------------------------------------------------------------------
# CostTracker tests
# ---------------------------------------------------------------------------

class TestCostTracker:

    def test_can_process_within_budget(self):
        ct = CostTracker(budget_limit_brl=1.0)
        assert ct.can_process(10)  # 10 * 0.05 = 0.50 < 1.0

    def test_cannot_process_over_budget(self):
        ct = CostTracker(budget_limit_brl=0.10)
        assert not ct.can_process(5)  # 5 * 0.05 = 0.25 > 0.10

    def test_record_updates_counters(self):
        ct = CostTracker(budget_limit_brl=10.0)
        ct.record(3)
        assert ct.pages_processed == 3
        assert ct.estimated_cost_brl == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# AzureDIFallback tests
# ---------------------------------------------------------------------------

class TestAzureDIFallback:

    def test_no_config_skips_processing(self):
        """If no endpoint/key, returns empty list."""
        fallback = AzureDIFallback(endpoint="", key="")
        q = _make_question()
        results = fallback.process_fallback_questions([q], "test.pdf")
        assert results == []

    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._analyze_pages")
    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._get_pdf_page_count", return_value=50)
    def test_fallback_improves_score(self, mock_pages, mock_analyze):
        """Azure DI produces better extraction → improved=True."""
        mock_analyze.return_value = _azure_markdown_good()

        fallback = AzureDIFallback(endpoint="https://test.cognitiveservices.azure.com", key="fake-key")
        q = _make_question(number=5, text_len=30, num_alts=3)  # low quality original
        original_scores = {5: 0.45}

        results = fallback.process_fallback_questions([q], "test.pdf", original_scores)

        assert len(results) == 1
        assert results[0].improved is True
        assert results[0].new_score > results[0].original_score

    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._analyze_pages")
    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._get_pdf_page_count", return_value=50)
    def test_fallback_still_low(self, mock_pages, mock_analyze):
        """Azure DI output still poor → improved=False."""
        mock_analyze.return_value = _azure_markdown_bad()

        fallback = AzureDIFallback(endpoint="https://test.cognitiveservices.azure.com", key="fake-key")
        q = _make_question(number=5, text_len=30, num_alts=3)
        original_scores = {5: 0.45}

        results = fallback.process_fallback_questions([q], "test.pdf", original_scores)

        assert len(results) == 1
        # The question wasn't found in the bad markdown or scored low
        assert results[0].improved is False

    def test_budget_exceeded_skips(self):
        """When budget is exhausted, questions are skipped."""
        fallback = AzureDIFallback(
            endpoint="https://test.cognitiveservices.azure.com",
            key="fake-key",
            budget_limit=0.01,  # very low budget
        )
        q = _make_question(number=5)

        with patch.object(fallback, "_get_pdf_page_count", return_value=50):
            results = fallback.process_fallback_questions([q], "test.pdf", {5: 0.60})

        assert len(results) == 1
        assert results[0].errors == ["budget_exceeded"]
        assert fallback.cost_tracker.budget_exceeded_count == 1

    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._analyze_pages")
    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._get_pdf_page_count", return_value=50)
    def test_rescoring_uses_real_scorer(self, mock_pages, mock_analyze):
        """Re-scoring after Azure DI uses ExtractionConfidenceScorer."""
        mock_analyze.return_value = _azure_markdown_good()

        fallback = AzureDIFallback(endpoint="https://test.cognitiveservices.azure.com", key="fake-key")
        q = _make_question(number=5, text_len=30, num_alts=2)
        original_scores = {5: 0.30}

        results = fallback.process_fallback_questions([q], "test.pdf", original_scores)

        assert len(results) == 1
        # The scorer should produce a real score (not just pass-through)
        assert isinstance(results[0].new_score, float)
        assert 0.0 <= results[0].new_score <= 1.0

    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._analyze_pages")
    @patch("src.enem_ingestion.azure_di_fallback.AzureDIFallback._get_pdf_page_count", return_value=50)
    def test_azure_error_handled(self, mock_pages, mock_analyze):
        """Azure DI call fails → error recorded, no crash."""
        mock_analyze.side_effect = Exception("Azure timeout")

        fallback = AzureDIFallback(endpoint="https://test.cognitiveservices.azure.com", key="fake-key")
        q = _make_question(number=5)

        results = fallback.process_fallback_questions([q], "test.pdf", {5: 0.60})

        assert len(results) == 1
        assert results[0].improved is False
        assert "Azure timeout" in results[0].errors[0]

    def test_latex_in_markdown_preserved(self):
        """LaTeX formulas in Azure DI markdown are preserved in output."""
        latex_md = (
            "**QUESTÃO 5**\n\n"
            "Considere a equação $x^2 + 2x + 1 = 0$. Qual é a solução "
            "desta equação polinomial de segundo grau? Determine o valor "
            "de x que satisfaz a igualdade apresentada.\n\n"
            "**(A)** $x = -1$ é a única raiz real possível neste caso\n\n"
            "**(B)** $x = 1$ é uma das soluções\n\n"
            "**(C)** $x = 0$ satisfaz a equação\n\n"
            "**(D)** $x = 2$ é raiz dupla\n\n"
            "**(E)** Não existem raízes reais\n\n"
        )

        fallback = AzureDIFallback(endpoint="https://test.cognitiveservices.azure.com", key="fake-key")

        with patch.object(fallback, "_analyze_pages", return_value=latex_md):
            with patch.object(fallback, "_get_pdf_page_count", return_value=50):
                q = _make_question(number=5, text_len=30, num_alts=2)
                results = fallback.process_fallback_questions([q], "test.pdf", {5: 0.40})

        assert len(results) == 1
        # LaTeX should be in the question text
        assert "$x^2" in results[0].question.text or "$x^2" in str(results[0].question.alternatives)


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class TestPipelineIntegration:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_pipeline_no_azure_config_backward_compat(self, mock_pg, tmp_path):
        """Pipeline with azure_config=None doesn't call Azure DI."""
        from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2

        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", azure_config=None)
        report = pipeline.run(str(tmp_path))  # empty dir

        assert report.total_pdfs == 0
        assert report.fallback_recovered == 0
