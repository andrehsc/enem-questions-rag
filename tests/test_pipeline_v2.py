"""
Tests for pipeline_v2.py (Story 5.3).

All DB and extractor calls are mocked — no real database or PDF needed.
"""

import hashlib
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2, PipelineReport
from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
from src.enem_ingestion.confidence_scorer import ConfidenceResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def metadata():
    return QuestionMetadata(
        year=2024, day=1, caderno="CD1",
        application_type="regular", exam_type="ENEM",
    )


def _make_question(number=1, score_routing="accept"):
    meta = QuestionMetadata(year=2024, day=1, caderno="CD1", application_type="regular")
    return Question(
        number=number,
        text="X" * 120,
        alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"],
        metadata=meta,
        subject=Subject.LINGUAGENS,
    )


@pytest.fixture
def fake_pdf(tmp_path):
    pdf = tmp_path / "2024_PV_impresso_D1_CD1.pdf"
    pdf.write_bytes(b"fake-pdf-content")
    return pdf


@pytest.fixture
def fake_dir(tmp_path, fake_pdf):
    return tmp_path


# ---------------------------------------------------------------------------
# Pipeline tests — routing
# ---------------------------------------------------------------------------

class TestPipelineRouting:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_accept_route_persists(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn

        # Each `with conn.cursor() as cur:` returns the same mock cursor
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # fetchone calls: hash_exists→None, ensure_exam_meta→(uuid,), persist→(uuid, True)
        mock_cursor.fetchone.side_effect = [
            None,              # _hash_exists
            ("meta-uuid",),    # _ensure_exam_metadata
            ("q-uuid", True),  # INSERT question RETURNING
        ]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))
        q = _make_question(number=5)
        conf = ConfidenceResult(score=0.95, passed=True, routing="accept")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                # force=True skips _hash_exists, so the first fetchone is _ensure_exam_metadata
                mock_cursor.fetchone.side_effect = [
                    ("meta-uuid",),    # _ensure_exam_metadata
                    ("q-uuid", True),  # INSERT question RETURNING
                ]
                report = pipeline.run(str(fake_dir), force=True)

        assert report.new == 1 or report.updated == 1
        assert report.fallback_queued == 0
        assert report.dead_letter_queued == 0

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_fallback_route_queues(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))

        q = _make_question(number=5)
        conf = ConfidenceResult(score=0.60, passed=False, routing="fallback")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(fake_dir), force=True)

        assert report.fallback_queued == 1
        assert len(report.fallback_questions) == 1

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_dead_letter_route_queues(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))

        q = _make_question(number=5)
        conf = ConfidenceResult(score=0.30, passed=False, routing="dead_letter")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(fake_dir), force=True)

        assert report.dead_letter_queued == 1
        assert len(report.dead_letter_questions) == 1


# ---------------------------------------------------------------------------
# Pipeline tests — idempotency
# ---------------------------------------------------------------------------

class TestPipelineIdempotency:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_skip_when_hash_exists(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # hash_exists returns a row → skip
        mock_cursor.fetchone.return_value = (1,)

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))

        with patch.object(pipeline._extractor, "extract_questions") as mock_extract:
            report = pipeline.run(str(fake_dir), force=False)

        assert report.skipped == 1
        assert report.total_questions == 0
        mock_extract.assert_not_called()

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_force_reprocesses(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # force=True skips hash check; ensure_exam_meta→uuid, insert→(uuid, True)
        mock_cursor.fetchone.side_effect = [
            ("uuid-meta",),
            ("uuid-q", True),
        ]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))
        q = _make_question(number=10)
        conf = ConfidenceResult(score=0.95, passed=True, routing="accept")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(fake_dir), force=True)

        assert report.skipped == 0
        assert report.total_questions == 1


# ---------------------------------------------------------------------------
# Pipeline tests — report
# ---------------------------------------------------------------------------

class TestPipelineReport:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_report_counters(self, mock_pg, fake_dir):
        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.side_effect = [("uuid-meta",), ("uuid-q", True)]

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(fake_dir / "img"))
        q = _make_question(number=1)
        conf = ConfidenceResult(score=0.95, passed=True, routing="accept")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(fake_dir), force=True)

        assert report.total_pdfs == 1
        assert report.duration_seconds >= 0
        assert isinstance(report, PipelineReport)

    def test_empty_directory(self, tmp_path):
        with patch("src.enem_ingestion.pipeline_v2.psycopg2") as mock_pg:
            mock_conn = MagicMock()
            mock_pg.connect.return_value = mock_conn

            pipeline = ExtractionPipelineV2(db_url="postgresql://x")
            report = pipeline.run(str(tmp_path))

        assert report.total_pdfs == 0
        assert report.total_questions == 0


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

class TestHashing:

    def test_hash_file(self, fake_pdf):
        h = ExtractionPipelineV2._hash_file(fake_pdf)
        expected = hashlib.sha256(b"fake-pdf-content").hexdigest()
        assert h == expected
