"""
Tests for dead_letter_queue.py (Story 6.2).

All DB calls are mocked — no real database in CI.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call

from src.enem_ingestion.dead_letter_queue import DeadLetterQueue
from src.enem_ingestion.parser import Question, QuestionMetadata, Subject


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_question(number=5, text="X" * 120, num_alts=5):
    meta = QuestionMetadata(
        year=2024, day=1, caderno="CD1", application_type="regular",
    )
    return Question(
        number=number,
        text=text,
        alternatives=[f"Alt {l}" + "y" * 20 for l in "ABCDE"][:num_alts],
        metadata=meta,
        subject=Subject.LINGUAGENS,
    )


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


# ---------------------------------------------------------------------------
# DeadLetterQueue.enqueue
# ---------------------------------------------------------------------------

class TestEnqueue:

    def test_enqueue_inserts_record(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("dl-uuid-123",)

        dlq = DeadLetterQueue(conn)
        q = _make_question(number=10)

        dl_id = dlq.enqueue(
            question=q,
            confidence=0.35,
            extraction_method="pymupdf4llm",
            failed_layers=["pymupdf4llm"],
            errors=["alternatives_count=3", "text_too_short=20"],
            pdf_filename="2024_PV_regular_D1_CD1.pdf",
        )

        assert dl_id == "dl-uuid-123"
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert "INSERT INTO enem_questions.dead_letter_questions" in call_args[0][0]
        conn.commit.assert_called_once()

    def test_enqueue_includes_raw_text_and_alternatives(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("dl-uuid-456",)

        dlq = DeadLetterQueue(conn)
        q = _make_question(number=7, text="My question text", num_alts=3)

        dlq.enqueue(
            question=q,
            confidence=0.20,
            extraction_method="pymupdf4llm",
            failed_layers=["pymupdf4llm"],
            errors=[],
            pdf_filename="test.pdf",
        )

        # Check that raw_text includes question text + alternatives
        call_args = cursor.execute.call_args[0][1]
        raw_text = call_args[3]  # 4th parameter is raw_text
        assert "My question text" in raw_text
        assert "Alt A" in raw_text

    def test_enqueue_failed_layers_array(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("dl-uuid-789",)

        dlq = DeadLetterQueue(conn)
        q = _make_question()

        dlq.enqueue(
            question=q,
            confidence=0.40,
            extraction_method="azure_di",
            failed_layers=["pymupdf4llm", "azure_di"],
            errors=["pydantic_error=..."],
            pdf_filename="test.pdf",
        )

        call_args = cursor.execute.call_args[0][1]
        failed_layers = call_args[7]  # 8th param
        assert failed_layers == ["pymupdf4llm", "azure_di"]


# ---------------------------------------------------------------------------
# DeadLetterQueue.resolve
# ---------------------------------------------------------------------------

class TestResolve:

    def test_resolve_updates_status(self, mock_conn):
        conn, cursor = mock_conn
        cursor.rowcount = 1

        dlq = DeadLetterQueue(conn)
        result = dlq.resolve("dl-uuid-123", resolved_by="admin", notes="Fixed manually")

        assert result is True
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0][0]
        assert "UPDATE enem_questions.dead_letter_questions" in call_args
        assert "status = 'resolved'" in call_args
        conn.commit.assert_called_once()

    def test_resolve_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.rowcount = 0

        dlq = DeadLetterQueue(conn)
        result = dlq.resolve("nonexistent-uuid", resolved_by="admin")

        assert result is False


# ---------------------------------------------------------------------------
# DeadLetterQueue.list_pending
# ---------------------------------------------------------------------------

class TestListPending:

    def test_list_pending_returns_items(self, mock_conn):
        conn, cursor = mock_conn
        # Simulate a row with 16 columns (15 data + 1 count)
        cursor.fetchall.return_value = [
            (
                "dl-uuid-1", 5, "test.pdf", "3-5",
                "raw text here", '["issue1"]', 0.35,
                "pymupdf4llm", ["pymupdf4llm"], "pending",
                None, None, None,
                "2026-04-03T10:00:00", "2026-04-03T10:00:00",
                1,  # COUNT(*) OVER()
            ),
        ]

        dlq = DeadLetterQueue(conn)
        items, total = dlq.list_pending(limit=20, offset=0)

        assert total == 1
        assert len(items) == 1
        assert items[0]["id"] == "dl-uuid-1"
        assert items[0]["question_number"] == 5
        assert items[0]["status"] == "pending"

    def test_list_pending_empty(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dlq = DeadLetterQueue(conn)
        items, total = dlq.list_pending()

        assert total == 0
        assert items == []

    def test_list_pending_pagination(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        dlq = DeadLetterQueue(conn)
        dlq.list_pending(limit=10, offset=20)

        call_args = cursor.execute.call_args[0][1]
        assert call_args[1] == 10  # limit
        assert call_args[2] == 20  # offset


# ---------------------------------------------------------------------------
# DeadLetterQueue.get_by_id
# ---------------------------------------------------------------------------

class TestGetById:

    def test_get_by_id_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (
            "dl-uuid-1", 5, "test.pdf", "3-5",
            "raw text", '[]', 0.35,
            "pymupdf4llm", ["pymupdf4llm"], "pending",
            None, None, None,
            "2026-04-03T10:00:00", "2026-04-03T10:00:00",
        )

        dlq = DeadLetterQueue(conn)
        result = dlq.get_by_id("dl-uuid-1")

        assert result is not None
        assert result["id"] == "dl-uuid-1"

    def test_get_by_id_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        dlq = DeadLetterQueue(conn)
        result = dlq.get_by_id("nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# Pipeline integration — dead letter routing
# ---------------------------------------------------------------------------

class TestPipelineDeadLetterIntegration:

    @patch("src.enem_ingestion.pipeline_v2.psycopg2")
    def test_dead_letter_route_enqueues(self, mock_pg, tmp_path):
        """Questions routed to dead_letter are persisted in DLQ table."""
        from src.enem_ingestion.pipeline_v2 import ExtractionPipelineV2
        from src.enem_ingestion.confidence_scorer import ConfidenceResult

        mock_conn = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        # DLQ enqueue: fetchone returns uuid
        mock_cursor.fetchone.return_value = ("dl-uuid-new",)

        # Create a PDF in tmp_path
        pdf = tmp_path / "2024_PV_impresso_D1_CD1.pdf"
        pdf.write_bytes(b"fake-pdf-content")

        pipeline = ExtractionPipelineV2(db_url="postgresql://x", output_dir=str(tmp_path / "img"))
        q = _make_question(number=5, text="Short", num_alts=2)
        conf = ConfidenceResult(score=0.30, passed=False, routing="dead_letter")

        with patch.object(pipeline._extractor, "extract_questions", return_value=[q]):
            with patch.object(pipeline._scorer, "score", return_value=conf):
                report = pipeline.run(str(tmp_path), force=True)

        assert report.dead_letter_queued == 1
