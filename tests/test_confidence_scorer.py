"""
Tests for confidence_scorer.py v2 (Story 8.3).
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
# Confidence Scorer v2 tests
# ---------------------------------------------------------------------------

class TestConfidenceScorer:

    def test_score_perfect_question(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        result = scorer.score(q)
        assert result.score >= 0.85
        assert result.routing == "accept"
        assert result.passed is True
        assert result.issues == []

    def test_score_partial_question(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=3, alt_len=30)
        result = scorer.score(q)
        assert result.score < 0.85
        assert result.routing in ("fallback", "dead_letter")
        assert result.passed is False

    def test_score_corrupted_question(self, scorer):
        q = _make_question(number=999, text_len=10, num_alts=0, alt_len=0)
        result = scorer.score(q)
        assert result.score < 0.55
        assert result.routing == "dead_letter"
        assert result.passed is False

    def test_score_short_alternatives(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=1)
        result = scorer.score(q)
        # partial credit for alt_quality due to short alts
        assert result.score > 0.30

    def test_issues_list_populated(self, scorer):
        q = _make_question(number=5, text_len=20, num_alts=2, alt_len=1)
        result = scorer.score(q)
        assert len(result.issues) > 0

    def test_v2_thresholds(self, scorer):
        assert scorer.ACCEPT_THRESHOLD == 0.85
        assert scorer.FALLBACK_THRESHOLD == 0.55


# ---------------------------------------------------------------------------
# Placeholder detection (AC: 1)
# ---------------------------------------------------------------------------

class TestPlaceholderDetection:

    def test_placeholder_in_alt_fails(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=3, alt_len=30)
        q.alternatives.append("D) [Alternative not found]")
        q.alternatives.append("E) [Alternative not found]")
        result = scorer.score(q)
        assert "placeholder_detected" in result.issues
        assert result.routing != "accept"

    def test_pt_br_placeholder_detected(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=4, alt_len=30)
        q.alternatives.append("E) [Alternativa não encontrada]")
        result = scorer.score(q)
        assert "placeholder_detected" in result.issues


# ---------------------------------------------------------------------------
# Contamination detection (AC: 2)
# ---------------------------------------------------------------------------

class TestContaminationDetection:

    def test_cid_tokens_detected(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.text = "Texto com tokens (cid:3)(cid:10) de fontes."
        result = scorer.score(q)
        assert "contamination_detected" in result.issues

    def test_indesign_detected(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.text = "Texto com PP22__11__DDiiaa..iinndddd artefato InDesign."
        result = scorer.score(q)
        assert "contamination_detected" in result.issues

    def test_header_detected(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.text = "Texto normal com ENEM2024 17 header residual no meio."
        result = scorer.score(q)
        assert "contamination_detected" in result.issues

    def test_clean_text_passes(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        result = scorer.score(q)
        assert "contamination_detected" not in result.issues

    def test_contaminated_question_below_085(self, scorer):
        """Story 9.3: contaminated question scores < 0.85 → fallback."""
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.text = "Texto normal com ENEM2024 17 header residual " + "x" * 80
        result = scorer.score(q)
        assert result.score < 0.85
        assert result.routing != "accept"

    def test_raw_alternatives_in_enunciado_detected(self, scorer):
        """Story 9.3: raw alternatives in enunciado → contamination."""
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.text = "Qual é o valor?\nA 4,00.\nB 4,87.\nC 5,00.\nD 5,83.\nE 6,00."
        result = scorer.score(q)
        assert "raw_alternatives_in_enunciado" in result.issues

    def test_guardrails_failed_penalized(self, scorer):
        """Story 9.4: guardrails_failed → contamination score 0."""
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        q.guardrails_failed = True
        result = scorer.score(q)
        assert "guardrails_validation_failed" in result.issues
        assert result.score < 0.85

    def test_guardrails_not_failed_no_impact(self, scorer):
        """Story 9.4: guardrails_failed=False has no impact."""
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        result = scorer.score(q)
        assert "guardrails_validation_failed" not in result.issues


# ---------------------------------------------------------------------------
# Cascade detection (AC: 3)
# ---------------------------------------------------------------------------

class TestCascadeDetection:

    def test_confirmed_cascade(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=0, alt_len=0)
        q.alternatives = [
            "opção A opção B opção C opção D opção E",
            "opção B opção C opção D opção E",
            "opção C opção D opção E",
            "opção D opção E",
            "opção E",
        ]
        result = scorer.score(q)
        assert "cascade_confirmed" in result.issues

    def test_suspected_cascade(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=0, alt_len=0)
        q.alternatives = [
            "x" * 500,
            "y" * 200,
            "z" * 100,
            "w" * 50,
            "v" * 30,
        ]
        result = scorer.score(q)
        assert "cascade_suspected" in result.issues

    def test_normal_alts_no_cascade(self, scorer):
        q = _make_question(number=5, text_len=120, num_alts=5, alt_len=30)
        result = scorer.score(q)
        assert "cascade_confirmed" not in result.issues
        assert "cascade_suspected" not in result.issues


# ---------------------------------------------------------------------------
# Threshold routing (AC: 5, 6)
# ---------------------------------------------------------------------------

class TestThresholdRouting:

    def test_accept_route(self, scorer):
        q = _make_question(number=50, text_len=200, num_alts=5, alt_len=50)
        result = scorer.score(q)
        assert result.routing == "accept"

    def test_dead_letter_route(self, scorer):
        q = _make_question(number=999, text_len=5, num_alts=0, alt_len=0)
        result = scorer.score(q)
        assert result.routing == "dead_letter"

    def test_boundary_scores(self, scorer):
        """Verify threshold boundary behavior."""
        # Score exactly 0.85 should accept
        # Score exactly 0.55 should fallback
        # Score below 0.55 should dead_letter
        assert scorer._determine_routing(0.85) == "accept"
        assert scorer._determine_routing(0.84) == "fallback"
        assert scorer._determine_routing(0.55) == "fallback"
        assert scorer._determine_routing(0.54) == "dead_letter"
