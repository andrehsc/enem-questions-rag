"""
Tests for confidence_scorer.py and models.py (Story 5.2).
"""

import pytest
from pydantic import ValidationError

from src.enem_ingestion.parser import Question, QuestionMetadata, Subject
from src.enem_ingestion.models import ENEMQuestion, ENEMAlternative
from src.enem_ingestion.confidence_scorer import ExtractionConfidenceScorer, ConfidenceResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scorer():
    return ExtractionConfidenceScorer()


@pytest.fixture
def metadata():
    return QuestionMetadata(
        year=2024, day=1, caderno="CD1",
        application_type="regular", exam_type="ENEM",
    )


def _make_question(number=1, text_len=100, num_alts=5, alt_len=20, metadata=None, subject=None):
    """Helper to create Question with variable quality."""
    if metadata is None:
        metadata = QuestionMetadata(
            year=2024, day=1, caderno="CD1",
            application_type="regular", exam_type="ENEM",
        )
    text = "A" * text_len
    alternatives = [f"Alt {'ABCDE'[i]}: " + "x" * alt_len for i in range(num_alts)]
    return Question(
        number=number,
        text=text,
        alternatives=alternatives,
        metadata=metadata,
        subject=subject or Subject.LINGUAGENS,
        context=None,
    )


# ---------------------------------------------------------------------------
# ENEMQuestion Pydantic model tests
# ---------------------------------------------------------------------------

class TestENEMQuestion:

    def test_valid_question(self):
        q = ENEMQuestion(
            question_number=1,
            question_text="A" * 60,
            alternatives=[
                ENEMAlternative(letter="A", text="Opção A"),
                ENEMAlternative(letter="B", text="Opção B"),
                ENEMAlternative(letter="C", text="Opção C"),
                ENEMAlternative(letter="D", text="Opção D"),
                ENEMAlternative(letter="E", text="Opção E"),
            ],
            subject="linguagens",
        )
        assert q.question_number == 1

    def test_invalid_alternatives_order(self):
        with pytest.raises(ValidationError):
            ENEMQuestion(
                question_number=1,
                question_text="A" * 60,
                alternatives=[
                    ENEMAlternative(letter="B", text="Opção B"),
                    ENEMAlternative(letter="A", text="Opção A"),
                    ENEMAlternative(letter="C", text="Opção C"),
                    ENEMAlternative(letter="D", text="Opção D"),
                    ENEMAlternative(letter="E", text="Opção E"),
                ],
                subject="linguagens",
            )

    def test_too_few_alternatives(self):
        with pytest.raises(ValidationError):
            ENEMQuestion(
                question_number=1,
                question_text="A" * 60,
                alternatives=[
                    ENEMAlternative(letter="A", text="A"),
                    ENEMAlternative(letter="B", text="B"),
                ],
                subject="linguagens",
            )

    def test_invalid_question_number(self):
        with pytest.raises(ValidationError):
            ENEMQuestion(
                question_number=0,
                question_text="A" * 60,
                alternatives=[
                    ENEMAlternative(letter=l, text=f"Opt {l}")
                    for l in "ABCDE"
                ],
                subject="linguagens",
            )

    def test_text_too_short(self):
        with pytest.raises(ValidationError):
            ENEMQuestion(
                question_number=1,
                question_text="Short",
                alternatives=[
                    ENEMAlternative(letter=l, text=f"Opt {l}")
                    for l in "ABCDE"
                ],
                subject="linguagens",
            )

    def test_from_dataclass(self, metadata):
        q = Question(
            number=10,
            text="A" * 60,
            alternatives=["Opt A", "Opt B", "Opt C", "Opt D", "Opt E"],
            metadata=metadata,
            subject=Subject.LINGUAGENS,
        )
        result = ENEMQuestion.from_dataclass(q)
        assert result.question_number == 10
        assert len(result.alternatives) == 5
        assert result.subject == "linguagens"

    def test_from_dataclass_wrong_alt_count_fails(self, metadata):
        q = Question(
            number=10,
            text="A" * 60,
            alternatives=["A", "B"],
            metadata=metadata,
            subject=Subject.LINGUAGENS,
        )
        with pytest.raises(ValidationError):
            ENEMQuestion.from_dataclass(q)

    def test_repeated_letter_fails(self):
        with pytest.raises(ValidationError):
            ENEMQuestion(
                question_number=1,
                question_text="A" * 60,
                alternatives=[
                    ENEMAlternative(letter="A", text="Opt A"),
                    ENEMAlternative(letter="A", text="Opt A2"),
                    ENEMAlternative(letter="C", text="Opt C"),
                    ENEMAlternative(letter="D", text="Opt D"),
                    ENEMAlternative(letter="E", text="Opt E"),
                ],
                subject="linguagens",
            )


# ---------------------------------------------------------------------------
# Confidence Scorer tests
# ---------------------------------------------------------------------------

class TestConfidenceScorer:

    def test_score_perfect_question(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        result = scorer.score(q)
        assert result.score >= 0.90
        assert result.routing == "accept"
        assert result.passed is True
        assert result.issues == []

    def test_score_partial_question(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=3, alt_len=30)
        result = scorer.score(q)
        assert 0.20 <= result.score < 0.80
        assert result.routing == "fallback"
        assert result.passed is False

    def test_score_corrupted_question(self, scorer):
        q = _make_question(number=999, text_len=10, num_alts=0, alt_len=0)
        result = scorer.score(q)
        assert result.score < 0.50
        assert result.routing == "dead_letter"
        assert result.passed is False

    def test_score_short_alternatives(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=2)
        result = scorer.score(q)
        # Should get partial credit for alt_length
        assert result.score > 0.50

    def test_issues_list_populated(self, scorer):
        q = _make_question(number=5, text_len=20, num_alts=2, alt_len=1)
        result = scorer.score(q)
        assert len(result.issues) > 0

    def test_accept_threshold(self, scorer):
        assert scorer.ACCEPT_THRESHOLD == 0.80
        assert scorer.FALLBACK_THRESHOLD == 0.50


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

class TestRouting:

    def test_accept_route(self, scorer):
        q = _make_question(number=50, text_len=200, num_alts=5, alt_len=50)
        result = scorer.score(q)
        assert result.routing == "accept"

    def test_fallback_route(self, scorer):
        # 3 alternatives => score ~0.55 (text+seq+partial_pydantic)
        q = _make_question(number=50, text_len=200, num_alts=3, alt_len=50)
        result = scorer.score(q)
        assert result.routing in ("fallback", "dead_letter")

    def test_dead_letter_route(self, scorer):
        q = _make_question(number=999, text_len=5, num_alts=0, alt_len=0)
        result = scorer.score(q)
        assert result.routing == "dead_letter"
