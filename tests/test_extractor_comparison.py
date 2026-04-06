"""
Tests for extractor comparison and auto-selection (Story 8.5).

Covers:
- compare_extractors.py logic
- _EXTRACTOR_MATRIX in pipeline_v2
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2


# ---------------------------------------------------------------------------
# Extractor decision matrix
# ---------------------------------------------------------------------------

class TestExtractorMatrix:

    def test_matrix_is_dict(self):
        assert isinstance(ExtractionPipelineV2._EXTRACTOR_MATRIX, dict)

    def test_matrix_entries_are_tuples(self):
        for key in ExtractionPipelineV2._EXTRACTOR_MATRIX:
            assert isinstance(key, tuple)
            assert len(key) == 2
            year, day = key
            assert isinstance(year, int)
            assert isinstance(day, int)

    def test_matrix_values_are_valid_extractors(self):
        valid = {'pymupdf4llm', 'pdfplumber'}
        for value in ExtractionPipelineV2._EXTRACTOR_MATRIX.values():
            assert value in valid

    def test_2021_entries_prefer_pymupdf4llm(self):
        """2021 PDFs produce (cid:XX) with pdfplumber."""
        assert ExtractionPipelineV2._EXTRACTOR_MATRIX.get((2021, 1)) == 'pymupdf4llm'
        assert ExtractionPipelineV2._EXTRACTOR_MATRIX.get((2021, 2)) == 'pymupdf4llm'


# ---------------------------------------------------------------------------
# compare_extractors.py — compare_pdf
# ---------------------------------------------------------------------------

class TestComparePdf:

    @patch("scripts.compare_extractors.EnemPDFParser")
    @patch("scripts.compare_extractors.Pymupdf4llmExtractor")
    def test_compare_returns_recommended(self, mock_pymupdf, mock_pdfplumber, tmp_path):
        """compare_pdf should return a dict with recommended extractor."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

        # Create mock with extract_questions
        mock_ext_instance = MagicMock()
        mock_pymupdf.return_value = mock_ext_instance

        # Create fake questions with score method
        from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
        q1 = Question(
            number=1, text="X" * 120,
            alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"],
            metadata=QuestionMetadata(year=2024, day=1, caderno="CD1", application_type="regular"),
            subject=Subject.LINGUAGENS,
        )
        mock_ext_instance.extract_questions.return_value = [q1]

        mock_parser_instance = MagicMock()
        mock_pdfplumber.return_value = mock_parser_instance
        mock_parser_instance.parse_questions.return_value = [q1]

        # Mock the scorer
        from src.enem_ingestion.confidence_scorer import ConfidenceResult
        mock_score = ConfidenceResult(score=0.90, passed=True, routing="accept")

        with patch("scripts.compare_extractors.ExtractionConfidenceScorer") as mock_scorer_cls:
            mock_scorer = MagicMock()
            mock_scorer_cls.return_value = mock_scorer
            mock_scorer.score.return_value = mock_score

            from scripts.compare_extractors import compare_pdf
            pdf = tmp_path / "test.pdf"
            pdf.write_bytes(b"fake")
            result = compare_pdf(pdf)

        assert 'pdf' in result
        assert 'pymupdf4llm' in result
        assert 'pdfplumber' in result
        assert 'recommended' in result
        assert result['recommended'] in ('pymupdf4llm', 'pdfplumber')

    def test_generate_report_creates_file(self, tmp_path):
        """generate_report should create a markdown file."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from scripts.compare_extractors import generate_report

        results = [
            {
                'pdf': 'test.pdf',
                'pymupdf4llm': {'count': 45, 'avg_score': 0.90},
                'pdfplumber': {'count': 40, 'avg_score': 0.85},
                'recommended': 'pymupdf4llm',
            }
        ]

        out_path = generate_report(results, str(tmp_path))
        assert Path(out_path).exists()
        content = Path(out_path).read_text(encoding='utf-8')
        assert '# Extractor Decision Matrix' in content
        assert 'test.pdf' in content
        assert '**pymupdf4llm**' in content

    def test_generate_report_multiple_pdfs(self, tmp_path):
        from scripts.compare_extractors import generate_report

        results = [
            {'pdf': f'test{i}.pdf',
             'pymupdf4llm': {'count': 45, 'avg_score': 0.90},
             'pdfplumber': {'count': 40, 'avg_score': 0.85},
             'recommended': 'pymupdf4llm'}
            for i in range(5)
        ]

        out_path = generate_report(results, str(tmp_path))
        content = Path(out_path).read_text(encoding='utf-8')
        for i in range(5):
            assert f'test{i}.pdf' in content
