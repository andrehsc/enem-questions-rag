"""
Confidence scoring for extracted ENEM questions (Story 5.2, updated Story 8.3).

Scores each question 0.0-1.0 based on structural quality indicators and
routes to accept / fallback / dead_letter.

v2 changes (Story 8.3):
- New contamination check (cid, InDesign, headers)
- Placeholder detection in alt_quality
- Cascade detection in alt_quality
- Recalibrated weights and thresholds
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Literal

from pydantic import ValidationError

from .models import ENEMQuestion
from .parser import Question
from .text_sanitizer import TextSanitizer

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Result of confidence scoring for a single question."""

    score: float
    passed: bool
    issues: List[str] = field(default_factory=list)
    routing: Literal["accept", "fallback", "dead_letter"] = "accept"


class ExtractionConfidenceScorer:
    """Score extraction quality and route questions accordingly.

    Weights (total = 1.0) — v2:
        alt_count       0.20 — exactly 5 alternatives A-E
        text_quality    0.20 — enunciado >= 50 chars, readable
        alt_quality     0.25 — no placeholder, no cascade, each alt >= 3 chars
        sequence        0.15 — question_number in expected range
        contamination   0.10 — no cid, no InDesign, no headers
        pydantic        0.10 — full Pydantic validation passes
    """

    ACCEPT_THRESHOLD = 0.85
    FALLBACK_THRESHOLD = 0.55

    _PLACEHOLDER_PATTERNS = re.compile(
        r'\[Alternative not found\]|\[Alternativa não encontrada\]',
        re.IGNORECASE,
    )

    def __init__(self):
        self._sanitizer = TextSanitizer()

    def score(self, question: Question) -> ConfidenceResult:
        """Score a question and determine routing."""
        total = 0.0
        issues: List[str] = []

        total += self._score_alt_count(question, issues)
        total += self._score_text_quality(question, issues)
        total += self._score_alt_quality(question, issues)
        total += self._score_sequence(question, issues)
        total += self._score_contamination(question, issues)
        total += self._score_pydantic(question, issues)

        routing = self._determine_routing(total)
        passed = routing == "accept"

        logger.info(
            "[%s] Q%d — confidence=%.2f issues=%s",
            routing.upper(),
            question.number,
            total,
            issues or "none",
        )

        return ConfidenceResult(
            score=round(total, 4),
            passed=passed,
            issues=issues,
            routing=routing,
        )

    # ------------------------------------------------------------------ #
    # Scoring components
    # ------------------------------------------------------------------ #

    @staticmethod
    def _score_alt_count(question: Question, issues: List[str]) -> float:
        """0.20 — exactly 5 alternatives."""
        if len(question.alternatives) == 5:
            return 0.20
        issues.append(f"alternatives_count={len(question.alternatives)}")
        return 0.0

    @staticmethod
    def _score_text_quality(question: Question, issues: List[str]) -> float:
        """0.20 — enunciado >= 50 chars."""
        text = question.text or ""
        if len(text) >= 50:
            return 0.20
        issues.append(f"text_too_short={len(text)}")
        return 0.0

    def _score_alt_quality(self, question: Question, issues: List[str]) -> float:
        """0.25 — no placeholders, no cascade, reasonable length."""
        if not question.alternatives:
            return 0.0

        # Placeholder check
        for alt in question.alternatives:
            if self._PLACEHOLDER_PATTERNS.search(alt):
                issues.append("placeholder_detected")
                return 0.0

        # Cascade check
        if len(question.alternatives) >= 3:
            texts = [a for a in question.alternatives]
            # confirmed cascade: B in A and C in B
            if len(texts) >= 3 and texts[1] in texts[0] and texts[2] in texts[1]:
                issues.append("cascade_confirmed")
                return 0.0
            # suspected cascade: A much longer than E
            if (len(texts) >= 5 and
                    len(texts[0]) > 3 * len(texts[4]) and
                    len(texts[4]) > 0):
                issues.append("cascade_suspected")
                return 0.05

        # Length check
        short = [i for i, a in enumerate(question.alternatives) if len(a) < 3]
        if short:
            issues.append(f"short_alternatives={short}")
            return 0.10

        return 0.25

    @staticmethod
    def _score_sequence(question: Question, issues: List[str]) -> float:
        """0.15 — question_number in expected range."""
        if 1 <= question.number <= 180:
            return 0.15
        issues.append(f"number_out_of_range={question.number}")
        return 0.0

    def _score_contamination(self, question: Question, issues: List[str]) -> float:
        """0.10 — no cid, InDesign, headers in text or alternatives."""
        full_text = (question.text or "") + " " + " ".join(question.alternatives)
        if self._sanitizer.has_contamination(full_text):
            issues.append("contamination_detected")
            return 0.0
        return 0.10

    @staticmethod
    def _score_pydantic(question: Question, issues: List[str]) -> float:
        """0.10 — Pydantic validation passes."""
        try:
            ENEMQuestion.from_dataclass(question)
            return 0.10
        except (ValidationError, Exception) as exc:
            issues.append(f"pydantic_error={exc}")
            return 0.0

    # ------------------------------------------------------------------ #
    # Routing
    # ------------------------------------------------------------------ #

    def _determine_routing(
        self, score: float
    ) -> Literal["accept", "fallback", "dead_letter"]:
        if score >= self.ACCEPT_THRESHOLD:
            return "accept"
        if score >= self.FALLBACK_THRESHOLD:
            return "fallback"
        return "dead_letter"
