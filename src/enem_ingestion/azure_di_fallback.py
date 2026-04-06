"""
Azure Document Intelligence Layout fallback for ENEM question extraction (Story 6.1).

Processes questions that scored < 0.80 (fallback routing) from the pymupdf4llm
primary extractor.  Uses Azure DI "prebuilt-layout" with formula add-on and
markdown output, then re-scores to decide accept vs dead_letter.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .confidence_scorer import ConfidenceResult, ExtractionConfidenceScorer
from .parser import Question, QuestionMetadata
from .pymupdf4llm_extractor import QUESTION_BOLD_RE, QUESTION_SPLIT_RE

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Result / tracking dataclasses
# ------------------------------------------------------------------

@dataclass
class FallbackResult:
    """Outcome of reprocessing a single question via Azure DI."""
    question: Question
    original_score: float
    new_score: float
    improved: bool
    method: str = "azure_di"
    errors: List[str] = field(default_factory=list)


@dataclass
class CostTracker:
    """Track Azure DI consumption against a budget."""
    pages_processed: int = 0
    estimated_cost_brl: float = 0.0
    budget_limit_brl: float = 50.0
    budget_exceeded_count: int = 0

    COST_PER_PAGE_BRL: float = 0.05  # ~R$50/1000 pages

    def can_process(self, num_pages: int) -> bool:
        additional = num_pages * self.COST_PER_PAGE_BRL
        return (self.estimated_cost_brl + additional) <= self.budget_limit_brl

    def record(self, num_pages: int) -> None:
        self.pages_processed += num_pages
        self.estimated_cost_brl += num_pages * self.COST_PER_PAGE_BRL


# ------------------------------------------------------------------
# Fallback processor
# ------------------------------------------------------------------

class AzureDIFallback:
    """Azure Document Intelligence Layout fallback extractor."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        budget_limit: float = 50.0,
    ):
        self._endpoint = endpoint or os.getenv("AZURE_DI_ENDPOINT", "")
        self._key = key or os.getenv("AZURE_DI_KEY", "")
        self._budget_limit = budget_limit
        self._scorer = ExtractionConfidenceScorer()
        self._cost = CostTracker(budget_limit_brl=budget_limit)
        self._client = None

    # ------------------------------------------------------------------
    # Lazy client initialisation
    # ------------------------------------------------------------------

    def _get_client(self):
        """Lazy-init Azure DI client (import only when needed)."""
        if self._client is not None:
            return self._client

        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        self._client = DocumentIntelligenceClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(self._key),
        )
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_fallback_questions(
        self,
        questions: List[Question],
        pdf_path: str,
        original_scores: Optional[Dict[int, float]] = None,
    ) -> List[FallbackResult]:
        """Reprocess fallback questions through Azure DI.

        Args:
            questions: Questions with fallback routing from pipeline_v2.
            pdf_path: Path to the source PDF.
            original_scores: Map of question_number → original confidence score.

        Returns:
            List of FallbackResult with re-scored outcomes.
        """
        if not self._endpoint or not self._key:
            logger.warning("Azure DI not configured — skipping fallback processing")
            return []

        original_scores = original_scores or {}
        results: List[FallbackResult] = []

        # Group questions by approximate page ranges
        page_groups = self._estimate_pages(questions, pdf_path)

        for pages_str, group_questions in page_groups.items():
            num_pages = self._count_pages(pages_str)

            if not self._cost.can_process(num_pages):
                logger.warning(
                    "[BUDGET_EXCEEDED] Skipping %d questions on pages %s — "
                    "cost %.2f + %.2f > budget %.2f",
                    len(group_questions), pages_str,
                    self._cost.estimated_cost_brl,
                    num_pages * CostTracker.COST_PER_PAGE_BRL,
                    self._cost.budget_limit_brl,
                )
                self._cost.budget_exceeded_count += len(group_questions)
                for q in group_questions:
                    results.append(FallbackResult(
                        question=q,
                        original_score=original_scores.get(q.number, 0.0),
                        new_score=0.0,
                        improved=False,
                        errors=["budget_exceeded"],
                    ))
                continue

            try:
                markdown = self._analyze_pages(pdf_path, pages_str)
                self._cost.record(num_pages)
            except Exception as exc:
                logger.error("[AZURE_DI_ERROR] pages=%s: %s", pages_str, exc)
                for q in group_questions:
                    results.append(FallbackResult(
                        question=q,
                        original_score=original_scores.get(q.number, 0.0),
                        new_score=0.0,
                        improved=False,
                        errors=[str(exc)],
                    ))
                continue

            # Parse extracted markdown into questions
            extracted = self._parse_markdown(markdown, group_questions)

            for q in group_questions:
                orig_score = original_scores.get(q.number, 0.0)
                new_q = extracted.get(q.number)

                if new_q is None:
                    logger.warning(
                        "[FALLBACK_MISSED] Q%d not found in Azure DI output", q.number,
                    )
                    results.append(FallbackResult(
                        question=q,
                        original_score=orig_score,
                        new_score=orig_score,
                        improved=False,
                        errors=["not_found_in_azure_output"],
                    ))
                    continue

                new_result = self._scorer.score(new_q)
                improved = new_result.score > orig_score

                log_fn = logger.info if improved else logger.warning
                log_fn(
                    "[FALLBACK_%s] Q%d %.2f → %.2f",
                    "IMPROVED" if improved else "FAILED",
                    q.number, orig_score, new_result.score,
                )

                results.append(FallbackResult(
                    question=new_q,
                    original_score=orig_score,
                    new_score=new_result.score,
                    improved=improved,
                    errors=new_result.issues if not improved else [],
                ))

        return results

    @property
    def cost_tracker(self) -> CostTracker:
        return self._cost

    # ------------------------------------------------------------------
    # Azure DI call
    # ------------------------------------------------------------------

    def _analyze_pages(self, pdf_path: str, pages: str) -> str:
        """Call Azure DI Layout and return markdown content."""
        from azure.ai.documentintelligence.models import (
            ContentFormat,
            DocumentAnalysisFeature,
        )

        client = self._get_client()

        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                "prebuilt-layout",
                body=f,
                content_type="application/octet-stream",
                output_content_format=ContentFormat.MARKDOWN,
                features=[
                    DocumentAnalysisFeature.FORMULAS,
                    DocumentAnalysisFeature.OCR_HIGH_RESOLUTION,
                ],
                pages=pages,
            )

        result = poller.result()
        return result.content

    # ------------------------------------------------------------------
    # Page estimation
    # ------------------------------------------------------------------

    def _estimate_pages(
        self,
        questions: List[Question],
        pdf_path: str,
    ) -> Dict[str, List[Question]]:
        """Group questions by estimated page ranges for batch Azure DI calls.

        Heuristic: ~2 questions per page for ENEM PDFs.
        Each group covers a contiguous range of pages.
        """
        if not questions:
            return {}

        # Try to determine total pages
        total_pages = self._get_pdf_page_count(pdf_path)

        # Estimate page per question (~2 questions per page for ENEM)
        groups: Dict[str, List[Question]] = {}
        for q in questions:
            if total_pages > 0:
                # Rough estimate: question N is around page N/2
                est_page = max(1, min(total_pages, q.number // 2))
                page_start = max(1, est_page - 1)
                page_end = min(total_pages, est_page + 1)
                pages_str = f"{page_start}-{page_end}"
            else:
                pages_str = "1-5"  # fallback

            groups.setdefault(pages_str, []).append(q)

        return groups

    @staticmethod
    def _get_pdf_page_count(pdf_path: str) -> int:
        try:
            import pymupdf
            with pymupdf.open(pdf_path) as doc:
                return len(doc)
        except Exception:
            return 0

    @staticmethod
    def _count_pages(pages_str: str) -> int:
        """Count number of pages in a range string like '3-7'."""
        parts = pages_str.split("-")
        if len(parts) == 2:
            try:
                return int(parts[1]) - int(parts[0]) + 1
            except ValueError:
                return 1
        return 1

    # ------------------------------------------------------------------
    # Markdown parsing (reuse patterns from pymupdf4llm_extractor)
    # ------------------------------------------------------------------

    def _parse_markdown(
        self,
        markdown: str,
        target_questions: List[Question],
    ) -> Dict[int, Question]:
        """Parse Azure DI markdown output into Question objects."""
        target_numbers = {q.number for q in target_questions}
        metadata = target_questions[0].metadata if target_questions else None

        # Split by question headers
        matches = list(QUESTION_SPLIT_RE.finditer(markdown))
        if not matches:
            matches = list(QUESTION_BOLD_RE.finditer(markdown))

        if not matches:
            return {}

        result: Dict[int, Question] = {}
        for i, m in enumerate(matches):
            q_num = int(m.group(1))
            if q_num not in target_numbers:
                continue

            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            q_text = markdown[start:end].strip()

            if not q_text:
                continue

            # Extract alternatives
            alternatives = self._extract_alternatives(q_text)

            # Extract enunciado (text before alternatives)
            enunciado = self._extract_enunciado(q_text)

            # Find original question for metadata
            orig = next((q for q in target_questions if q.number == q_num), None)

            result[q_num] = Question(
                number=q_num,
                text=enunciado,
                alternatives=alternatives,
                metadata=orig.metadata if orig else metadata,
                subject=orig.subject if orig else None,
                context=orig.context if orig else None,
            )

        return result

    @staticmethod
    def _extract_alternatives(text: str) -> List[str]:
        """Extract alternatives from markdown text."""
        pattern = re.compile(
            r'\*{0,2}\(([A-E])\)\*{0,2}\s+(.+?)(?=\s*\*{0,2}\([A-E]\)\*{0,2}\s|$)',
            re.DOTALL,
        )
        matches = pattern.findall(text)
        if len(matches) == 5:
            return [m[1].strip() for m in matches]
        return []

    @staticmethod
    def _extract_enunciado(text: str) -> str:
        """Extract question statement before alternatives."""
        lines = text.split('\n')
        enunciado_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):
                break
            enunciado_lines.append(line)
        enunciado = '\n'.join(enunciado_lines).strip()
        return enunciado if len(enunciado) >= 10 else text[:500]
