"""
Confidence scoring for extracted ENEM questions (Story 5.2).

Scores each question 0.0-1.0 based on structural quality indicators and
routes to accept / fallback / dead_letter.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Literal

from pydantic import ValidationError

from .models import ENEMQuestion
from .parser import Question

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

    Weights (total = 1.0):
        alternatives  0.30 — exactly 5 alternatives A-E
        text          0.25 — enunciado >= 50 chars, readable
        sequence      0.20 — question_number in expected range
        alt_length    0.15 — each alternative >= 5 chars
        pydantic      0.10 — full Pydantic validation passes
    """

    ACCEPT_THRESHOLD = 0.80
    FALLBACK_THRESHOLD = 0.50

    def score(self, question: Question) -> ConfidenceResult:
        """Score a question and determine routing."""
        total = 0.0
        issues: List[str] = []

        # 1. Alternatives (0.30)
        total += self._score_alternatives(question, issues)

        # 2. Text quality (0.25)
        total += self._score_text(question, issues)

        # 3. Sequence (0.20)
        total += self._score_sequence(question, issues)

        # 4. Alternative length (0.15)
        total += self._score_alt_length(question, issues)

        # 5. Pydantic validation (0.10)
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
    def _score_alternatives(question: Question, issues: List[str]) -> float:
        if len(question.alternatives) == 5:
            return 0.30
        issues.append(f"alternatives_count={len(question.alternatives)}")
        return 0.0

    @staticmethod
    def _score_text(question: Question, issues: List[str]) -> float:
        text = question.text or ""
        if len(text) >= 50:
            return 0.25
        issues.append(f"text_too_short={len(text)}")
        return 0.0

    @staticmethod
    def _score_sequence(question: Question, issues: List[str]) -> float:
        if 1 <= question.number <= 180:
            return 0.20
        issues.append(f"number_out_of_range={question.number}")
        return 0.0

    @staticmethod
    def _score_alt_length(question: Question, issues: List[str]) -> float:
        if not question.alternatives:
            return 0.0
        short = [i for i, a in enumerate(question.alternatives) if len(a) < 5]
        if not short:
            return 0.15
        issues.append(f"short_alternatives={short}")
        return 0.05  # partial credit

    @staticmethod
    def _score_pydantic(question: Question, issues: List[str]) -> float:
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
