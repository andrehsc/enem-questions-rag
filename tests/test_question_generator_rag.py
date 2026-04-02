#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for RAGQuestionGenerator — Story 4.2
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.rag_features.question_generator import RAGQuestionGenerator, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


SAMPLE_LLM_RESPONSE = json.dumps([{
    "stem": "Questao sobre funcoes quadraticas...",
    "context_text": "Texto-base sobre funcoes.",
    "alternatives": {"A": "opt1", "B": "opt2", "C": "opt3", "D": "opt4", "E": "opt5"},
    "answer": "B",
    "explanation": "A alternativa B eh correta porque...",
}])


@pytest.fixture
def mock_pgvector():
    m = AsyncMock()
    m.search_questions = AsyncMock(return_value=[
        {"question_id": 1, "full_text": "Contexto ENEM real 1", "subject": "matematica", "year": 2023},
        {"question_id": 2, "full_text": "Contexto ENEM real 2", "subject": "matematica", "year": 2022},
    ])
    return m


@pytest.fixture
def generator(mock_pgvector):
    with patch("src.rag_features.question_generator.create_engine") as mock_engine:
        mock_engine.return_value = MagicMock()
        with patch("src.rag_features.question_generator.AsyncOpenAI") as mock_openai_cls:
            mock_client = AsyncMock()
            mock_openai_cls.return_value = mock_client
            gen = RAGQuestionGenerator(
                database_url="postgresql://test:test@localhost/test",
                openai_api_key="test-key",
                pgvector_search=mock_pgvector,
                model="gpt-4o",
            )
            gen._mock_openai_client = mock_client
    return gen


class TestFetchContextChunks:
    async def test_returns_context_chunks_for_subject(self, generator, mock_pgvector):
        result = await generator._fetch_context_chunks("matematica", "funcoes")
        assert len(result) == 2
        assert result[0]["subject"] == "matematica"

    async def test_passes_subject_filter_to_pgvector(self, generator, mock_pgvector):
        await generator._fetch_context_chunks("historia", "segunda guerra")
        mock_pgvector.search_questions.assert_called_once_with(
            query="historia segunda guerra",
            limit=5,
            subject="historia",
        )

    async def test_returns_empty_list_when_no_pgvector(self):
        with patch("src.rag_features.question_generator.create_engine"):
            with patch("src.rag_features.question_generator.AsyncOpenAI"):
                gen = RAGQuestionGenerator(
                    database_url="postgresql://test:test@localhost/test",
                    openai_api_key="test-key",
                    pgvector_search=None,
                )
        result = await gen._fetch_context_chunks("matematica", "funcoes")
        assert result == []


class TestBuildGenerationPrompt:
    def test_includes_system_prompt(self, generator):
        messages = generator._build_generation_prompt(
            topic="funcoes", subject="matematica", difficulty="medium",
            count=1, style="enem", context_chunks=[],
        )
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT

    def test_includes_context_chunks_in_user_prompt(self, generator):
        chunks = [{"full_text": "Texto ENEM sobre funcoes"}]
        messages = generator._build_generation_prompt(
            topic="funcoes", subject="matematica", difficulty="medium",
            count=1, style="enem", context_chunks=chunks,
        )
        assert "Texto ENEM sobre funcoes" in messages[1]["content"]

    def test_includes_subject_topic_difficulty(self, generator):
        messages = generator._build_generation_prompt(
            topic="Segunda Guerra", subject="historia", difficulty="hard",
            count=2, style="enem", context_chunks=[],
        )
        user_msg = messages[1]["content"]
        assert "historia" in user_msg
        assert "Segunda Guerra" in user_msg
        assert "hard" in user_msg

    def test_handles_empty_context_gracefully(self, generator):
        messages = generator._build_generation_prompt(
            topic="tema", subject="mat", difficulty="easy",
            count=1, style="enem", context_chunks=[],
        )
        assert "(Nenhum contexto encontrado no corpus)" in messages[1]["content"]


class TestParseLlmResponse:
    def test_parses_valid_json_array(self, generator):
        content = '[{"stem": "Q1", "answer": "A"}]'
        result = generator._parse_llm_response(content)
        assert isinstance(result, list)
        assert result[0]["stem"] == "Q1"

    def test_parses_single_object_as_array(self, generator):
        content = '{"stem": "Q1", "answer": "A"}'
        result = generator._parse_llm_response(content)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_extracts_json_from_markdown_block(self, generator):
        content = 'Here is the result:\n```json\n[{"stem": "Q1", "answer": "A"}]\n```'
        result = generator._parse_llm_response(content)
        assert len(result) == 1

    def test_raises_on_invalid_content(self, generator):
        with pytest.raises(ValueError, match="JSON válido"):
            generator._parse_llm_response("This is not JSON at all")


class TestGenerateQuestions:
    async def test_returns_questions_with_required_fields(self, generator):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=SAMPLE_LLM_RESPONSE))]
        generator.openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(generator, "_persist_generated", return_value=["uuid-1"]):
            result = await generator.generate_questions(
                subject="matematica", topic="funcoes", count=1,
            )

        assert len(result) == 1
        q = result[0]
        assert "stem" in q
        assert "alternatives" in q
        assert "answer" in q
        assert "explanation" in q
        assert "source_context_ids" in q

    async def test_source_context_ids_populated(self, generator):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=SAMPLE_LLM_RESPONSE))]
        generator.openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(generator, "_persist_generated", return_value=["uuid-1"]):
            result = await generator.generate_questions(
                subject="matematica", topic="funcoes", count=1,
            )

        assert len(result[0]["source_context_ids"]) == 2  # 2 context chunks from mock

    async def test_respects_count_parameter(self, generator):
        two_questions = json.dumps([
            {"stem": "Q1", "context_text": None, "alternatives": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"}, "answer": "A", "explanation": "exp1"},
            {"stem": "Q2", "context_text": None, "alternatives": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"}, "answer": "B", "explanation": "exp2"},
            {"stem": "Q3", "context_text": None, "alternatives": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"}, "answer": "C", "explanation": "exp3"},
        ])
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=two_questions))]
        generator.openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(generator, "_persist_generated", return_value=["u1", "u2", "u3"]):
            result = await generator.generate_questions(
                subject="matematica", topic="funcoes", count=2,
            )

        assert len(result) == 2

    async def test_calls_gpt4o_with_correct_model(self, generator):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=SAMPLE_LLM_RESPONSE))]
        generator.openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(generator, "_persist_generated", return_value=["uuid-1"]):
            await generator.generate_questions(subject="matematica", topic="funcoes", count=1)

        call_kwargs = generator.openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    async def test_persists_to_generated_questions_table(self, generator):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=SAMPLE_LLM_RESPONSE))]
        generator.openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(generator, "_persist_generated", return_value=["uuid-1"]) as mock_persist:
            await generator.generate_questions(subject="matematica", topic="funcoes", count=1)

        mock_persist.assert_called_once()
        args = mock_persist.call_args
        assert args[0][1] == "matematica"  # subject
        assert args[0][2] == "funcoes"  # topic


class TestPersistGenerated:
    def test_inserts_into_generated_questions_table(self, generator):
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value="uuid-generated")
        mock_conn.execute = MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        generator.engine.begin = MagicMock(return_value=mock_ctx)

        questions = [{"stem": "Q1", "alternatives": {"A": "a"}, "answer": "A", "explanation": "exp"}]
        ids = generator._persist_generated(questions, "matematica", "funcoes", "medium")

        assert len(ids) == 1
        mock_conn.execute.assert_called_once()

    def test_returns_list_of_uuids(self, generator):
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value="uuid-1")
        mock_conn.execute = MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        generator.engine.begin = MagicMock(return_value=mock_ctx)

        questions = [{"stem": "Q1", "alternatives": {}, "answer": "A", "explanation": "e"}]
        ids = generator._persist_generated(questions, "mat", "t", "easy")
        assert ids == ["uuid-1"]
