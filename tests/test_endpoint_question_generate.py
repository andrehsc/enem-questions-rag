#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for POST /api/v1/questions/generate — Story 4.2
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient


SAMPLE_GENERATE_RESULT = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "stem": "Questao sobre funcoes quadraticas no estilo ENEM...",
        "context_text": "Texto-base sobre funcoes.",
        "alternatives": {"A": "opt1", "B": "opt2", "C": "opt3", "D": "opt4", "E": "opt5"},
        "answer": "B",
        "explanation": "A alternativa B eh correta porque...",
        "source_context_ids": ["chunk-uuid-1", "chunk-uuid-2"],
    }
]


class TestQuestionGenerateEndpoint:
    def test_valid_request_returns_200(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate_questions = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.rag_question_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": "funcoes quadraticas"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert len(body["data"]) == 1
        assert body["data"][0]["stem"] == SAMPLE_GENERATE_RESULT[0]["stem"]

    def test_count_exceeds_max_returns_422(self):
        import api.fastapi_app as app_module
        app_module.rag_question_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": "funcoes", "count": 6},
        )
        assert response.status_code == 422

    def test_empty_subject_returns_422(self):
        import api.fastapi_app as app_module
        app_module.rag_question_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "", "topic": "funcoes"},
        )
        assert response.status_code == 422

    def test_empty_topic_returns_422(self):
        import api.fastapi_app as app_module
        app_module.rag_question_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": ""},
        )
        assert response.status_code == 422

    def test_invalid_difficulty_returns_422(self):
        import api.fastapi_app as app_module
        app_module.rag_question_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": "funcoes", "difficulty": "extreme"},
        )
        assert response.status_code == 422

    def test_service_unavailable_returns_503(self):
        import api.fastapi_app as app_module
        app_module.rag_question_generator = None

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": "funcoes"},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "GENERATION_UNAVAILABLE"

    def test_response_includes_source_context_ids(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate_questions = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.rag_question_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/questions/generate",
            json={"subject": "matematica", "topic": "funcoes"},
        )

        body = response.json()
        assert body["data"][0]["source_context_ids"] == ["chunk-uuid-1", "chunk-uuid-2"]

    def test_meta_contains_generation_metadata(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate_questions = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.rag_question_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/questions/generate",
            json={
                "subject": "historia",
                "topic": "Segunda Guerra",
                "difficulty": "hard",
                "count": 1,
            },
        )

        body = response.json()
        meta = body["meta"]
        assert meta["subject"] == "historia"
        assert meta["topic"] == "Segunda Guerra"
        assert meta["difficulty"] == "hard"
        assert meta["model"] == "gpt-4o"
        assert "generated_at" in meta
