#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for AssessmentGenerator — Story 4.1
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.rag_features.assessment_generator import (
    AssessmentGenerator,
    InsufficientQuestionsError,
)


def _make_question(qid, subject="matematica", year=2023):
    return {
        "question_id": qid,
        "full_text": f"Questao {qid}",
        "subject": subject,
        "year": year,
        "chunk_id": f"chunk-{qid}",
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
        result = await generator._select_questions("matematica", 10, None)
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
        result = await generator._select_questions("matematica", 10, [2023, 2024])
        assert len(result) == 2
        assert all(q["year"] in [2023, 2024] for q in result)

    async def test_deduplicates_by_question_id(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [
            _make_question(1),
            _make_question(1),  # dup
            _make_question(2),
        ]
        result = await generator._select_questions("matematica", 10, None)
        assert len(result) == 2
        ids = [q["question_id"] for q in result]
        assert len(ids) == len(set(ids))

    async def test_returns_empty_when_no_matches(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = []
        result = await generator._select_questions("filosofia", 10, [2025])
        assert result == []

    async def test_fetch_limit_multiplied_when_years_filter(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = []
        await generator._select_questions("matematica", 30, [2023, 2024])
        call_args = mock_pgvector.search_questions.call_args
        # fetch_limit = 30 * max(len([2023, 2024]), 1) = 30 * 2 = 60
        assert call_args[1]["limit"] == 60


class TestBuildAnswerKeyBatch:
    def test_returns_dict_and_empty_missing_when_all_found(self, generator):
        questions = [_make_question(1), _make_question(2)]
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "A"), (2, "C")]
        mock_conn.execute.return_value = mock_result
        generator.engine.connect.return_value = mock_conn

        answer_key, answers_missing = generator._build_answer_key_batch(questions)

        assert answer_key == {1: "A", 2: "C"}
        assert answers_missing == []

    def test_missing_answers_appear_in_second_list(self, generator):
        questions = [_make_question(1), _make_question(2)]
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "B")]  # question 2 has no answer
        mock_conn.execute.return_value = mock_result
        generator.engine.connect.return_value = mock_conn

        answer_key, answers_missing = generator._build_answer_key_batch(questions)

        assert answer_key == {1: "B"}
        assert answers_missing == [2]

    def test_empty_questions_returns_empty(self, generator):
        answer_key, answers_missing = generator._build_answer_key_batch([])
        assert answer_key == {}
        assert answers_missing == []


class TestGenerate:
    async def test_returns_assessment_id_questions_answer_key(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(5)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_build_answer_key_batch", return_value=({1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}, [])):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock):
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=5
                )

        assert "assessment_id" in result
        assert len(result["questions"]) == 5
        assert "answer_key" in result
        assert "answers_missing" in result
        assert result["title"] == "Avaliacao Matematica — medium"

    async def test_returns_answers_missing_in_result(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(3)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_build_answer_key_batch", return_value=({1: "A"}, [2, 3])):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock):
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=3
                )

        assert result["answers_missing"] == [2, 3]

    async def test_raises_insufficient_when_not_enough(self, generator, mock_pgvector):
        mock_pgvector.search_questions.return_value = [_make_question(1)]

        with pytest.raises(InsufficientQuestionsError, match="Apenas 1"):
            await generator.generate(
                subject="filosofia", difficulty="hard", question_count=10
            )

    async def test_persists_assessment_in_database(self, generator, mock_pgvector):
        questions = [_make_question(i) for i in range(3)]
        mock_pgvector.search_questions.return_value = questions

        with patch.object(generator, "_build_answer_key_batch", return_value=({1: "B", 2: "C", 3: "D"}, [])):
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

        with patch.object(generator, "_build_answer_key_batch", return_value=({}, [])):
            with patch.object(generator, "_persist_assessment", new_callable=AsyncMock):
                result = await generator.generate(
                    subject="matematica", difficulty="medium", question_count=5
                )

        ids = [q["question_id"] for q in result["questions"]]
        assert len(ids) == len(set(ids))


class TestSyncPersistAssessment:
    def test_calls_engine_begin(self, generator):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        generator.engine.begin = MagicMock(return_value=mock_conn)

        generator._sync_persist_assessment(
            "test-uuid", "Test Title", "matematica", "medium", 2, None, [1, 2]
        )

        generator.engine.begin.assert_called_once()
        assert mock_conn.execute.call_count == 3  # 1 assessment + 2 questions
