"""
Pydantic v2 models for ENEM question validation (Story 5.2).

These models are the single source of truth for the extraction pipeline v2.
They replace manual validation scattered across enem_structure_spec.py and
base_types.py for new data flowing through the v2 pipeline.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .parser import Question, Subject


class ENEMAlternative(BaseModel):
    """A single ENEM question alternative (A-E)."""

    letter: Literal["A", "B", "C", "D", "E"]
    text: str = Field(min_length=1)


class ENEMQuestion(BaseModel):
    """Validated ENEM question structure.

    Enforces: exactly 5 alternatives A-E in order, valid question number,
    minimum enunciado length.
    """

    question_number: int = Field(ge=1, le=180)
    question_text: str = Field(min_length=50)
    alternatives: List[ENEMAlternative] = Field(min_length=5, max_length=5)
    subject: str
    context_text: Optional[str] = None
    confidence_score: Optional[float] = None
    extraction_method: str = "pymupdf4llm"

    @field_validator("alternatives")
    @classmethod
    def validate_alternatives_order(cls, v: List[ENEMAlternative]) -> List[ENEMAlternative]:
        expected = ["A", "B", "C", "D", "E"]
        actual = [alt.letter for alt in v]
        if actual != expected:
            raise ValueError(f"Alternativas devem ser A-E em ordem, recebido: {actual}")
        return v

    @field_validator("question_number")
    @classmethod
    def validate_question_range(cls, v: int) -> int:
        if not (1 <= v <= 180):
            raise ValueError(f"Número da questão fora do range válido: {v}")
        return v

    # ------------------------------------------------------------------ #
    # Conversion from legacy dataclass
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dataclass(cls, question: Question) -> "ENEMQuestion":
        """Convert a parser.Question dataclass to a validated ENEMQuestion."""
        letters = ["A", "B", "C", "D", "E"]
        alternatives = [
            ENEMAlternative(letter=letters[i], text=alt)
            for i, alt in enumerate(question.alternatives)
        ] if len(question.alternatives) == 5 else []

        subject_str = question.subject.value if isinstance(question.subject, Subject) else str(question.subject or "unknown")

        return cls(
            question_number=question.number,
            question_text=question.text,
            alternatives=alternatives,
            subject=subject_str,
            context_text=question.context,
        )
