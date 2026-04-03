"""
Dead Letter Queue for irrecoverable ENEM questions (Story 6.2).

Persists questions with confidence < 0.50 (or Azure DI re-score < 0.80)
for manual review via admin API endpoints.
"""

import json
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """Persist and manage irrecoverable extraction failures."""

    def __init__(self, conn):
        """
        Args:
            conn: psycopg2 connection object.
        """
        self._conn = conn

    def enqueue(
        self,
        question,
        confidence: float,
        extraction_method: str,
        failed_layers: List[str],
        errors: List[str],
        pdf_filename: str,
        page_numbers: Optional[str] = None,
    ) -> str:
        """Insert a question into the dead letter queue.

        Args:
            question: parser.Question dataclass instance.
            confidence: Final confidence score.
            extraction_method: Last extraction method attempted.
            failed_layers: List of layers that failed (e.g. ['pymupdf4llm', 'azure_di']).
            errors: List of issue strings from ConfidenceResult.
            pdf_filename: Source PDF filename.
            page_numbers: Estimated page range (e.g. "5-7").

        Returns:
            UUID string of the inserted dead letter record.
        """
        raw_text = question.text
        if question.alternatives:
            raw_text += "\n" + "\n".join(question.alternatives)

        with self._conn.cursor() as cur:
            cur.execute("""
                INSERT INTO enem_questions.dead_letter_questions
                    (question_number, pdf_filename, page_numbers, raw_text,
                     extraction_errors, confidence_score, extraction_method,
                     failed_layers)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
            """, (
                question.number,
                pdf_filename,
                page_numbers,
                raw_text,
                json.dumps(errors),
                confidence,
                extraction_method,
                failed_layers,
            ))
            dl_id = str(cur.fetchone()[0])
            self._conn.commit()

        logger.info(
            "[DEAD_LETTER] Enqueued Q%d from %s — confidence=%.2f layers=%s",
            question.number, pdf_filename, confidence, failed_layers,
        )
        return dl_id

    def resolve(
        self,
        dl_id: str,
        resolved_by: str,
        notes: str = "",
    ) -> bool:
        """Mark a dead letter record as resolved.

        Returns:
            True if the record was found and updated.
        """
        with self._conn.cursor() as cur:
            cur.execute("""
                UPDATE enem_questions.dead_letter_questions
                SET status = 'resolved',
                    resolved_by = %s,
                    resolved_at = NOW(),
                    resolution_notes = %s,
                    updated_at = NOW()
                WHERE id = %s AND status = 'pending'
            """, (resolved_by, notes, dl_id))
            updated = cur.rowcount > 0
            self._conn.commit()

        if updated:
            logger.info("[DEAD_LETTER] Resolved %s by %s", dl_id, resolved_by)
        return updated

    def list_pending(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str = "pending",
    ) -> Tuple[List[dict], int]:
        """List dead letter records with pagination.

        Returns:
            Tuple of (items, total_count).
        """
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, question_number, pdf_filename, page_numbers,
                       raw_text, extraction_errors, confidence_score,
                       extraction_method, failed_layers, status,
                       resolved_by, resolved_at, resolution_notes,
                       created_at, updated_at,
                       COUNT(*) OVER() AS total_count
                FROM enem_questions.dead_letter_questions
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (status, limit, offset))

            rows = cur.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][15]  # COUNT(*) OVER()
        items = []
        for row in rows:
            items.append({
                "id": str(row[0]),
                "question_number": row[1],
                "pdf_filename": row[2],
                "page_numbers": row[3],
                "raw_text": row[4],
                "extraction_errors": row[5] if isinstance(row[5], list) else json.loads(row[5] or "[]"),
                "confidence_score": row[6],
                "extraction_method": row[7],
                "failed_layers": row[8],
                "status": row[9],
                "resolved_by": row[10],
                "resolved_at": str(row[11]) if row[11] else None,
                "resolution_notes": row[12],
                "created_at": str(row[13]),
                "updated_at": str(row[14]),
            })

        return items, total_count

    def get_by_id(self, dl_id: str) -> Optional[dict]:
        """Get a single dead letter record by ID."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, question_number, pdf_filename, page_numbers,
                       raw_text, extraction_errors, confidence_score,
                       extraction_method, failed_layers, status,
                       resolved_by, resolved_at, resolution_notes,
                       created_at, updated_at
                FROM enem_questions.dead_letter_questions
                WHERE id = %s
            """, (dl_id,))
            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": str(row[0]),
            "question_number": row[1],
            "pdf_filename": row[2],
            "page_numbers": row[3],
            "raw_text": row[4],
            "extraction_errors": row[5] if isinstance(row[5], list) else json.loads(row[5] or "[]"),
            "confidence_score": row[6],
            "extraction_method": row[7],
            "failed_layers": row[8],
            "status": row[9],
            "resolved_by": row[10],
            "resolved_at": str(row[11]) if row[11] else None,
            "resolution_notes": row[12],
            "created_at": str(row[13]),
            "updated_at": str(row[14]),
        }
