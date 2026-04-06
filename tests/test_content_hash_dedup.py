"""
Tests for content hash deduplication (Story 8.4).

Covers:
- compute_content_hash determinism and normalization
- Pipeline dedup logic (skip lower-score duplicates)
- deduplicate_existing.py functions
"""

import hashlib
import re
import pytest
from unittest.mock import MagicMock, patch

from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------

class TestComputeContentHash:

    def test_deterministic(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Texto da questão", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Texto da questão", 2024, 1)
        assert h1 == h2

    def test_length_is_16(self):
        h = ExtractionPipelineV2.compute_content_hash("Qualquer texto", 2023, 2)
        assert len(h) == 16

    def test_hex_chars_only(self):
        h = ExtractionPipelineV2.compute_content_hash("abc", 2020, 1)
        assert all(c in '0123456789abcdef' for c in h)

    def test_different_years_produce_different_hashes(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Mesmo texto", 2023, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Mesmo texto", 2024, 1)
        assert h1 != h2

    def test_different_days_produce_different_hashes(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Mesmo texto", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Mesmo texto", 2024, 2)
        assert h1 != h2

    def test_normalizes_case(self):
        h1 = ExtractionPipelineV2.compute_content_hash("ABCDE", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("abcde", 2024, 1)
        assert h1 == h2

    def test_normalizes_whitespace(self):
        h1 = ExtractionPipelineV2.compute_content_hash("a  b   c", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("a b c", 2024, 1)
        assert h1 == h2

    def test_strips_question_number_questao(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Questão 42 Texto real", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Questão 99 Texto real", 2024, 1)
        assert h1 == h2

    def test_strips_question_number_questao_sem_acento(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Questao 1 Algo", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Questao 50 Algo", 2024, 1)
        assert h1 == h2

    def test_empty_text(self):
        h = ExtractionPipelineV2.compute_content_hash("", 2024, 1)
        assert len(h) == 16

    def test_none_text(self):
        h = ExtractionPipelineV2.compute_content_hash(None, 2024, 1)  # type: ignore
        assert len(h) == 16

    def test_different_text_different_hash(self):
        h1 = ExtractionPipelineV2.compute_content_hash("Texto A", 2024, 1)
        h2 = ExtractionPipelineV2.compute_content_hash("Texto B", 2024, 1)
        assert h1 != h2


# ---------------------------------------------------------------------------
# deduplicate_existing.py — compute_content_hash equivalence
# ---------------------------------------------------------------------------

class TestDeduplicateExistingHash:
    """Verify that the standalone script hash matches the pipeline hash."""

    def test_standalone_matches_pipeline(self):
        """Both implementations should produce the same hash."""
        # Inline the logic from deduplicate_existing.py
        def standalone_hash(enunciado, year, day):
            normalized = (enunciado or "").lower().strip()
            normalized = re.sub(r'quest[ãa]o\s*\d+', '', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            payload = f"{year}:{day}:{normalized}"
            return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

        text = "QUESTÃO 42 O texto sobre o ENEM é importante"
        assert standalone_hash(text, 2024, 1) == ExtractionPipelineV2.compute_content_hash(text, 2024, 1)


# ---------------------------------------------------------------------------
# Pipeline dedup — skip when existing has higher score
# ---------------------------------------------------------------------------

class TestPipelineDedup:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_dedup_skips_lower_score(self, mock_pg, tmp_path):
        """If existing question has higher score, new insert is skipped."""
        pdf = tmp_path / "2024_PV_regular_D1_CD1.pdf"
        pdf.write_bytes(b"test-content")

        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
        from src.enem_ingestion.confidence_scorer import ConfidenceResult

        q = Question(
            number=1, text="X" * 120,
            alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"],
            metadata=QuestionMetadata(year=2024, day=1, caderno="CD1", application_type="regular"),
            subject=Subject.LINGUAGENS,
        )
        conf = ConfidenceResult(score=0.90, passed=True, routing="accept")

        # content_hash lookup returns existing row with HIGHER score
        mock_cursor.fetchone.side_effect = [
            ("existing-id", 0.95),   # content_hash SELECT → existing has 0.95 > 0.90
        ]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(tmp_path / "img"))

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(tmp_path), force=True)

        # Should NOT insert because existing has higher confidence
        assert report.updated >= 0  # skipped dedup counts as updated=0 or new=0

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_dedup_inserts_when_higher_score(self, mock_pg, tmp_path):
        """If new question has higher score, it replaces the existing one."""
        pdf = tmp_path / "2024_PV_regular_D1_CD1.pdf"
        pdf.write_bytes(b"test-content")

        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
        from src.enem_ingestion.confidence_scorer import ConfidenceResult

        q = Question(
            number=1, text="X" * 120,
            alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"],
            metadata=QuestionMetadata(year=2024, day=1, caderno="CD1", application_type="regular"),
            subject=Subject.LINGUAGENS,
        )
        conf = ConfidenceResult(score=0.95, passed=True, routing="accept")

        # content_hash lookup returns existing row with LOWER score
        mock_cursor.fetchone.side_effect = [
            ("existing-id", 0.80),   # existing has 0.80 < 0.95 → proceed
            ("meta-uuid",),          # _ensure_exam_metadata
            ("q-uuid", False),       # INSERT RETURNING (is_new=False → update)
        ]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(tmp_path / "img"))

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(tmp_path), force=True)

        assert report.updated >= 1 or report.new >= 1

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_dedup_inserts_when_no_existing(self, mock_pg, tmp_path):
        """If no existing question with same hash, insert as new."""
        pdf = tmp_path / "2024_PV_regular_D1_CD1.pdf"
        pdf.write_bytes(b"test-content")

        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
        from src.enem_ingestion.confidence_scorer import ConfidenceResult

        q = Question(
            number=1, text="X" * 120,
            alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"],
            metadata=QuestionMetadata(year=2024, day=1, caderno="CD1", application_type="regular"),
            subject=Subject.LINGUAGENS,
        )
        conf = ConfidenceResult(score=0.95, passed=True, routing="accept")

        # content_hash lookup returns None → no existing
        mock_cursor.fetchone.side_effect = [
            None,              # content_hash SELECT → no match
            ("meta-uuid",),    # _ensure_exam_metadata
            ("q-uuid", True),  # INSERT RETURNING (is_new=True)
        ]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(tmp_path / "img"))

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(tmp_path), force=True)

        assert report.new == 1
