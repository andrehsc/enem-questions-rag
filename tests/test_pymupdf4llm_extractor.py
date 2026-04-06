"""
Tests for pymupdf4llm_extractor module (Story 5.1).

All pymupdf4llm and pymupdf calls are mocked — no real PDFs needed in CI.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.enem_ingestion.pymupdf4llm_extractor import Pymupdf4llmExtractor
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


@pytest.fixture
def extractor(tmp_path):
    return Pymupdf4llmExtractor(output_dir=str(tmp_path / "images"))


# ---------------------------------------------------------------------------
# Helper: markdown builders
# ---------------------------------------------------------------------------

def _md_text_only():
    """Markdown for a simple text-only question (no images, no multi-column)."""
    return (
        "**QUESTÃO 1**\n\n"
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


def _md_multicolumn():
    """Markdown simulating two-column extraction merged by Layout AI."""
    return (
        "**QUESTÃO 46**\n\n"
        "A Revolução Francesa de 1789 representou um marco na história "
        "política mundial. Analise as alternativas e indique aquela que "
        "descreve corretamente uma de suas consequências.\n\n"
        "**(A)** A consolidação do absolutismo monárquico na França.\n\n"
        "**(B)** A Declaração dos Direitos do Homem e do Cidadão.\n\n"
        "**(C)** O fortalecimento do regime feudal europeu.\n\n"
        "**(D)** A expansão do Império Otomano sobre a Europa.\n\n"
        "**(E)** A unificação política da Alemanha.\n\n"
    )


def _md_with_images():
    """Markdown with image references (from write_images=True)."""
    return (
        "**QUESTÃO 2**\n\n"
        "Observe a figura a seguir.\n\n"
        "![Figura 1](images/page_0_img_1.png)\n\n"
        "Com base na imagem apresentada, podemos concluir que o fenômeno "
        "representado está relacionado a processos de erosão que ocorrem "
        "em regiões de clima tropical úmido.\n\n"
        "**(A)** A erosão fluvial é a principal responsável pela formação do relevo mostrado.\n\n"
        "**(B)** O intemperismo químico não atua na região representada.\n\n"
        "**(C)** A deposição de sedimentos é o processo predominante na figura.\n\n"
        "**(D)** O relevo apresentado é resultado exclusivo de atividade tectônica.\n\n"
        "**(E)** A cobertura vegetal não influencia os processos erosivos locais.\n\n"
    )


# ---------------------------------------------------------------------------
# Tests — text-only PDF
# ---------------------------------------------------------------------------

class TestExtractQuestionsTextOnly:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_extract_single_text_question(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_text_only()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions) == 1
        q = questions[0]
        assert q.number == 1
        assert isinstance(q, Question)
        assert q.subject == Subject.LINGUAGENS
        assert q.metadata.year == 2024

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_alternatives_extracted_correctly(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_text_only()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        q = questions[0]
        assert len(q.alternatives) == 5
        assert "antropocentrismo" in q.alternatives[2]

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_enunciado_has_text(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_text_only()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions[0].text) >= 50


# ---------------------------------------------------------------------------
# Tests — multi-column PDF
# ---------------------------------------------------------------------------

class TestExtractQuestionsMulticolumn:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_multicolumn_question_extracted(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_multicolumn()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions) == 1
        q = questions[0]
        assert q.number == 46
        assert q.subject == Subject.CIENCIAS_HUMANAS
        assert len(q.alternatives) == 5


# ---------------------------------------------------------------------------
# Tests — images
# ---------------------------------------------------------------------------

class TestExtractQuestionsWithImages:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_image_question_has_context(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_with_images()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions) == 1
        q = questions[0]
        assert q.number == 2
        # Image reference should be in context
        assert q.context is not None
        assert "img" in q.context.lower() or "imagem" in q.context.lower() or "png" in q.context.lower()

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_image_question_alternatives(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_with_images()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions[0].alternatives) == 5


# ---------------------------------------------------------------------------
# Tests — multiple questions
# ---------------------------------------------------------------------------

class TestExtractMultipleQuestions:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_multiple_questions_in_page(self, mock_p4l, extractor, metadata):
        combined = _md_text_only() + "\n\n" + _md_with_images()
        mock_p4l.to_markdown.return_value = [{"text": combined}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert len(questions) == 2
        numbers = {q.number for q in questions}
        assert numbers == {1, 2}


# ---------------------------------------------------------------------------
# Tests — failure / edge cases
# ---------------------------------------------------------------------------

class TestExtractFailureCases:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_empty_pdf_returns_empty(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": ""}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert questions == []

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_extraction_error_raises(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.side_effect = RuntimeError("PDF corrupted")

        with pytest.raises(RuntimeError):
            with patch.object(extractor, "_detect_scanned_pages", return_value=False):
                extractor.extract_questions("bad.pdf", metadata=metadata)

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_output_is_list_of_question(self, mock_p4l, extractor, metadata):
        mock_p4l.to_markdown.return_value = [{"text": _md_text_only()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            result = extractor.extract_questions("fake.pdf", metadata=metadata)

        assert isinstance(result, list)
        for q in result:
            assert isinstance(q, Question)
            assert hasattr(q, "number")
            assert hasattr(q, "text")
            assert hasattr(q, "alternatives")
            assert hasattr(q, "metadata")
            assert hasattr(q, "subject")


# ---------------------------------------------------------------------------
# Tests — OCR detection
# ---------------------------------------------------------------------------

class TestOCRDetection:

    def test_detect_scanned_pages_no_text(self, extractor):
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        with patch("pymupdf.open", return_value=mock_doc):
            assert extractor._detect_scanned_pages("scanned.pdf") is True

    def test_detect_scanned_pages_with_text(self, extractor):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "A" * 100

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        with patch("pymupdf.open", return_value=mock_doc):
            assert extractor._detect_scanned_pages("normal.pdf") is False


# ---------------------------------------------------------------------------
# Tests — filename parsing integration
# ---------------------------------------------------------------------------

class TestFilenameIntegration:

    @patch("src.enem_ingestion.pymupdf4llm_extractor.pymupdf4llm")
    def test_metadata_parsed_from_filename(self, mock_p4l, extractor):
        mock_p4l.to_markdown.return_value = [{"text": _md_text_only()}]

        with patch.object(extractor, "_detect_scanned_pages", return_value=False):
            questions = extractor.extract_questions(
                "2024_PV_impresso_D1_CD1.pdf"
            )

        assert len(questions) >= 1
        assert questions[0].metadata.year == 2024
        assert questions[0].metadata.day == 1


# ---------------------------------------------------------------------------
# Tests — raw alternative block detection (Story 9.1)
# ---------------------------------------------------------------------------

class TestLooksLikeAlternativeBlock:

    @pytest.fixture
    def inst(self, extractor):
        return extractor

    @pytest.mark.parametrize("lines,start,expected", [
        # Clear alternative block
        (["A 4,00.", "B 4,87.", "C 5,00.", "D 5,83.", "E 6,00."], 0, True),
        # Block starting at B (3 sequential)
        (["B 8", "C 10", "D 12", "E 14"], 0, True),
        # False positive: "A" as article
        (["A família que adota é mais feliz...", "E então tudo mudou..."], 0, False),
        # False positive: "E" as conjunction (standalone)
        (["E então o fenômeno se manifesta..."], 0, False),
        # Only 2 letters — insufficient
        (["A 4,00.", "B 4,87."], 0, False),
        # Non-sequential letters
        (["A 4,00.", "C 5,00.", "B 4,87."], 0, False),
    ])
    def test_looks_like_alternative_block(self, inst, lines, start, expected):
        assert Pymupdf4llmExtractor._looks_like_alternative_block(lines, start) == expected


class TestExtractEnunciadoStopsAtRawAlts:

    @pytest.fixture
    def inst(self, tmp_path):
        return Pymupdf4llmExtractor(output_dir=str(tmp_path / "images"))

    def test_strips_raw_alternatives_from_enunciado(self, inst):
        text = (
            "Qual é o valor aproximado?\n"
            "A 4,00.\n"
            "B 4,87.\n"
            "C 5,00.\n"
            "D 5,83.\n"
            "E 6,00."
        )
        result = inst._extract_enunciado(text)
        assert "4,00" not in result
        assert "Qual é o valor aproximado?" in result

    def test_preserves_enunciado_with_article_A(self, inst):
        text = (
            "A família que adota é mais feliz do que a que gera filhos naturais.\n"
            "Segundo o autor, esta afirmação é..."
        )
        result = inst._extract_enunciado(text)
        assert "A família" in result
