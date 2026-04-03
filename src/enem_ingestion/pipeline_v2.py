"""
Extraction Pipeline v2 — idempotent PDF-to-DB orchestrator (Story 5.3).

This pipeline reads ENEM PDFs, extracts questions via pymupdf4llm,
scores quality, and persists accepted questions to PostgreSQL with
UPSERT semantics.  Fallback and dead-letter routing are placeholder
hooks for Epic 6.
"""

import argparse
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import psycopg2
from dotenv import load_dotenv

from .confidence_scorer import ExtractionConfidenceScorer
from .parser import Question, QuestionMetadata
from .pymupdf4llm_extractor import Pymupdf4llmExtractor

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Report dataclass
# ------------------------------------------------------------------

@dataclass
class PipelineReport:
    total_pdfs: int = 0
    total_questions: int = 0
    new: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    fallback_queued: int = 0
    dead_letter_queued: int = 0
    duration_seconds: float = 0.0
    fallback_questions: List[Question] = field(default_factory=list)
    dead_letter_questions: List[Question] = field(default_factory=list)


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------

class ExtractionPipelineV2:
    """Orchestrator: PDF → pymupdf4llm → confidence → DB."""

    def __init__(
        self,
        db_url: str,
        output_dir: str = "data/extracted_images",
    ):
        self._db_url = db_url
        self._extractor = Pymupdf4llmExtractor(output_dir=output_dir)
        self._scorer = ExtractionConfidenceScorer()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        input_path: str,
        force: bool = False,
    ) -> PipelineReport:
        """Process all PDFs in *input_path*.

        Args:
            input_path: Directory containing ``*.pdf`` files.
            force: If *True*, reprocess even if the file hash exists.

        Returns:
            PipelineReport summarising what happened.
        """
        start = time.time()
        report = PipelineReport()

        pdfs = sorted(Path(input_path).glob("*.pdf"))
        report.total_pdfs = len(pdfs)
        logger.info("Found %d PDFs in %s", len(pdfs), input_path)

        conn = psycopg2.connect(self._db_url)
        try:
            for pdf in pdfs:
                self._process_pdf(pdf, conn, report, force)
        finally:
            conn.close()

        report.duration_seconds = round(time.time() - start, 2)
        self._print_report(report)
        return report

    # ------------------------------------------------------------------
    # Per-PDF processing
    # ------------------------------------------------------------------

    def _process_pdf(
        self,
        pdf_path: Path,
        conn,
        report: PipelineReport,
        force: bool,
    ) -> None:
        file_hash = self._hash_file(pdf_path)

        if not force and self._hash_exists(conn, file_hash):
            logger.info("[SKIP] %s — already ingested", pdf_path.name)
            report.skipped += 1
            return

        try:
            metadata = self._extractor._parser.parse_filename(pdf_path.name)
            questions = self._extractor.extract_questions(str(pdf_path), metadata)
        except Exception as exc:
            logger.error("[ERROR] %s — %s", pdf_path.name, exc)
            report.errors += 1
            return

        for q in questions:
            self._process_question(q, conn, report, file_hash, metadata)

    def _process_question(
        self,
        question: Question,
        conn,
        report: PipelineReport,
        file_hash: str,
        metadata: QuestionMetadata,
    ) -> None:
        report.total_questions += 1

        result = self._scorer.score(question)

        if result.routing == "accept":
            try:
                is_new = self._persist_question(
                    conn, question, metadata, result.score, file_hash,
                )
                if is_new:
                    report.new += 1
                else:
                    report.updated += 1
            except Exception as exc:
                logger.error(
                    "[ERROR] Q%d — persist failed: %s", question.number, exc,
                )
                report.errors += 1
        elif result.routing == "fallback":
            logger.warning(
                "[FALLBACK] Q%d — confidence=%.2f", question.number, result.score,
            )
            report.fallback_queued += 1
            report.fallback_questions.append(question)
        else:
            logger.error(
                "[DEAD_LETTER] Q%d — confidence=%.2f", question.number, result.score,
            )
            report.dead_letter_queued += 1
            report.dead_letter_questions.append(question)

    # ------------------------------------------------------------------
    # Persistence (raw SQL / psycopg2)
    # ------------------------------------------------------------------

    def _persist_question(
        self,
        conn,
        question: Question,
        metadata: QuestionMetadata,
        confidence: float,
        file_hash: str,
    ) -> bool:
        """UPSERT a question. Returns *True* if new, *False* if updated."""
        subject_str = question.subject.value if question.subject else None

        with conn.cursor() as cur:
            # Ensure exam_metadata row exists
            exam_meta_id = self._ensure_exam_metadata(cur, metadata)

            cur.execute("""
                INSERT INTO enem_questions.questions
                    (question_number, question_text, context_text, subject,
                     exam_metadata_id, confidence_score, extraction_method,
                     ingestion_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exam_metadata_id, question_number)
                DO UPDATE SET
                    question_text = EXCLUDED.question_text,
                    context_text = EXCLUDED.context_text,
                    confidence_score = EXCLUDED.confidence_score,
                    extraction_method = EXCLUDED.extraction_method,
                    ingestion_hash = EXCLUDED.ingestion_hash,
                    updated_at = NOW()
                RETURNING id, (xmax = 0) AS is_new
            """, (
                question.number,
                question.text,
                question.context,
                subject_str,
                exam_meta_id,
                confidence,
                "pymupdf4llm",
                file_hash,
            ))
            row = cur.fetchone()
            question_id = row[0]
            is_new = row[1]

            # Persist alternatives
            self._persist_alternatives(cur, question_id, question.alternatives)

            conn.commit()
        return is_new

    def _persist_alternatives(self, cur, question_id, alternatives: List[str]) -> None:
        letters = ["A", "B", "C", "D", "E"]
        for i, alt_text in enumerate(alternatives):
            if i >= 5:
                break
            cur.execute("""
                INSERT INTO enem_questions.question_alternatives
                    (question_id, alternative_letter, alternative_text, alternative_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (question_id, alternative_letter)
                DO UPDATE SET alternative_text = EXCLUDED.alternative_text
            """, (question_id, letters[i], alt_text, i + 1))

    def _ensure_exam_metadata(self, cur, metadata: QuestionMetadata) -> str:
        """Return existing exam_metadata id or insert a new row."""
        pdf_filename = f"{metadata.year}_PV_{metadata.application_type}_D{metadata.day}_{metadata.caderno}.pdf"
        cur.execute(
            "SELECT id FROM enem_questions.exam_metadata WHERE pdf_filename = %s",
            (pdf_filename,),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute("""
            INSERT INTO enem_questions.exam_metadata
                (year, day, caderno, application_type, exam_type, pdf_filename)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            metadata.year,
            metadata.day,
            metadata.caderno,
            metadata.application_type,
            metadata.exam_type or "ENEM",
            pdf_filename,
        ))
        return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # Hashing & de-duplication
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _hash_exists(conn, file_hash: str) -> bool:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM enem_questions.questions WHERE ingestion_hash = %s LIMIT 1",
                (file_hash,),
            )
            return cur.fetchone() is not None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @staticmethod
    def _print_report(report: PipelineReport) -> None:
        logger.info(
            "Pipeline report: pdfs=%d questions=%d new=%d updated=%d "
            "skipped=%d errors=%d fallback=%d dead_letter=%d duration=%.1fs",
            report.total_pdfs,
            report.total_questions,
            report.new,
            report.updated,
            report.skipped,
            report.errors,
            report.fallback_queued,
            report.dead_letter_queued,
            report.duration_seconds,
        )
        print(
            f"\n{'='*60}\n"
            f"Pipeline v2 Report\n"
            f"{'='*60}\n"
            f"  PDFs processed : {report.total_pdfs}\n"
            f"  Questions found: {report.total_questions}\n"
            f"  New inserted   : {report.new}\n"
            f"  Updated        : {report.updated}\n"
            f"  Skipped (hash) : {report.skipped}\n"
            f"  Errors         : {report.errors}\n"
            f"  Fallback queue : {report.fallback_queued}\n"
            f"  Dead letter    : {report.dead_letter_queued}\n"
            f"  Duration       : {report.duration_seconds:.1f}s\n"
            f"{'='*60}"
        )


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="ENEM extraction pipeline v2 (pymupdf4llm + confidence scoring)",
    )
    parser.add_argument("--input", required=True, help="Directory with PDF files")
    parser.add_argument("--force", action="store_true", help="Reprocess all PDFs")
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://enem_rag_service:enem_rag_pass@localhost:5433/teachershub_enem",
        ),
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--output-dir",
        default="data/extracted_images",
        help="Directory for extracted images",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pipeline = ExtractionPipelineV2(db_url=args.db_url, output_dir=args.output_dir)
    pipeline.run(input_path=args.input, force=args.force)


if __name__ == "__main__":
    main()
