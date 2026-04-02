#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for AssessmentGenerator — Story 4.1
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.rag_features.assessment_generator import (
    AssessmentGenerator,
    InsufficientQuestionsError,
    DIFFICULTY_DISTRIBUTION,
)


def _make_question(qid, subject="matematica", year=2023, difficulty="medium"):
    return {
        "question_id": qid,
        "full_text": f"Questao {qid}",
        "subject": subject,
        "year": year,
        "difficulty": difficulty,
        "similarity_score": 0.9,
    }


@pytest.fixture
def mock_pgvector():
    m = AsyncMock()
    m.search_questions = AsyncMock(return_value=[])
    return m


@pytest.fixture
def generator(mock_pgvector):
    with patch("src.rag_features.assessment_generator.create_engine") as mock_engine:
        mock_engine.return_value = MagicMock()
        gen = AssessmentGenerator(
            database_url="postgresql://test:test@localhost/test",
            pgvector_search=mock_pgvector,
        )
    return gen


class TestAssessmentGeneratorInit:
    def test_creates_engine_and_stores_pgvector_search(self, mock_pgvector):
        with patch("src.rag_features.assessment_generator.create_engine") as mock_engine:
            mock_engine.return_value = MagicMock()
            gen = AssessmentGenerator(
                database_url="postgresql://test:test@localhost/test",
                pgvector_search=mock_pgvector,
            )
            mock_engine.assert_called_once_with("postgresql://test:test@localhost/test")
            assert gen.pgvector_search is mock_pgvector


class TestSelectQuestions:
    async def test_calls_pgvector_search_with_subject(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [_make_question(1)]
        result = await generator._select_questions("matematica", "medium", 10, None)
        mock_pgvector.search_questions.assert_called_once_with(
            query="questoes de matematica",
            limit=10,
            subject="matematica",
        )
        assert len(result) == 1

    async def test_filters_by_years_when_provided(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [
            _make_question(1, year=2022),
            _make_question(2, year=2023),
            _make_question(3, year=2024),
        ]
        result = await generator._select_questions("matematica", "medium", 10, [2023, 2024])
        assert len(result) == 2
        assert all(q["year"] in [2023, 2024] for q in result)

    async def test_deduplicates_by_question_id(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [
            _make_question(1),
            _make_question(1),  # dup
            _make_question(2),
        ]
        result = await generator._select_questions("matematica", "medium", 10, None)
        assert len(result) == 2
        ids = [q["question_id"] for q in result]
        assert len(ids) == len(set(ids))

    async def test_returns_empty_when_no_matches(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = []
        result = await generator._select_questions("filosofia", "hard", 10, [2025])
        assert result == []


class TestDistributeByDifficulty:
    def test_single_difficulty_returns_first_n(self, generator):
        candidates = [_make_question(i) for i in range(10)]
        result = generator._distribute_by_difficulty(candidates, "medium", 5)
        assert len(result) == 5
        assert result == candidates[:5]

    def test_mixed_fills_up_to_count(self, generator):
        candidates = [_make_question(i, difficulty="medium") for i in range(20)]
        result = generator._distribute_by_difficulty(candidates, "mixed", 10)
        assert len(result) == 10

    def test_mixed_respects_proportion_when_levels_available(self, generator):
        candidates = (
            [_make_question(i, difficulty="easy") for i in range(10)]
            + [_make_question(i + 10, difficulty="medium") for i in range(10)]
            + [_make_question(i + 20, difficulty="hard") for i in range(10)]
        )
        result = generator._distribute_by_difficulty(candidates, "mixed", 10)
        assert len(result) == 10
        # First selections should follow 30/40/30 split (3/4/3)
        easy_count = sum(1 for q in result if q["difficulty"] == "easy")
        medium_count = sum(1 for q in result if q["difficulty"] == "medium")
        hard_count = sum(1 for q in result if q["difficulty"] == "hard")
        assert easy_count == 3
        assert medium_count == 4
        assert hard_count == 3

    def test_returns_at_most_count(self, generator):
        candidates = [_make_question(i) for i in range(100)]
        result = generator._distribute_by_difficulty(candidates, "hard", 5)
        assert len(result) <= 5


class TestBuildAnswerKey:
    def test_returns_dict_with_order_and_letter(self, generator):
        questions = [_make_question(1), _make_question(2)]
        with patch.object(generator, "_get_correct_answer", side_effect=["A", "C"]):
            answer_key = generator._build_answer_key(questions)
        assert answer_key == {1: "A", 2: "C"}

    def test_skips_questions_without_answer(self, generator):
        questions = [_make_question(1), _make_question(2)]
        with patch.object(generator, "_get_correct_answer", side_effect=["B", None]):
            answer_key = generator._build_answer_key(questions)
        assert answer_key == {1: "B"}


class TestGenerate:
    async def test_returns_assessment_id_questions_answer_key(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(5)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_get_correct_answer", return_value="A"):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock):
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=5
                )

        assert "assessment_id" in result
        assert len(result["questions"]) == 5
        assert "answer_key" in result
        assert result["title"] == "Avaliacao Matematica — medium"

    async def test_raises_insufficient_when_not_enough(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [_make_question(1)]

        with pytest.raises(InsufficientQuestionsError, match="Apenas 1"):
            await generator.generate(
                subject="filosofia", difficulty="hard", question_count=10
            )

    async def test_persists_assessment_in_database(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(3)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_get_correct_answer", return_value="B"):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock) as mock_persist:
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=3
                )

        mock_persist.assert_called_once()
        args = mock_persist.call_args
        assert args[0][2] == "matematica"  # subject
        assert args[0][3] == "medium"  # difficulty
        assert len(args[0][6]) == 3  # question_ids

    async def test_questions_have_unique_ids(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(5)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_get_correct_answer", return_value="A"):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock):
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=5
                )

        ids = [q["question_id"] for q in result["questions"]]
        assert len(ids) == len(set(ids))


class TestPersistAssessment:
    async def test_calls_engine_begin(self, generator):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        generator.engine.begin = MagicMock(return_value=mock_conn)

        await generator._persist_assessment(
            "test-uuid", "Test Title", "matematica", "medium", 2, None, [1, 2]
        )

        generator.engine.begin.assert_called_once()
        assert mock_conn.execute.call_count == 3  # 1 assessment + 2 questions
