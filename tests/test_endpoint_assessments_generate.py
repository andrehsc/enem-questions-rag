#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for POST /api/v1/assessments/generate — Story 4.1
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient


SAMPLE_GENERATE_RESULT = {
    "assessment_id": "a3f1c9e2-7b8d-4e5f-9a1b-2c3d4e5f6a7b",
    "title": "Avaliacao Matematica — medium",
    "questions": [
        {
            "question_id": 42,
            "full_text": "Questao sobre funcoes quadraticas...\nA) opt1\nB) opt2",
            "subject": "matematica",
            "year": 2023,
            "images": [],
        },
        {
            "question_id": 87,
            "full_text": "Questao sobre graficos...\nA) opt1\nB) opt2",
            "subject": "matematica",
            "year": 2022,
            "images": [],
        },
    ],
    "answer_key": {1: "C", 2: "A"},
}


class TestAssessmentEndpoint:
    def test_valid_request_returns_200(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.assessment_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "difficulty": "medium", "question_count": 2},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert body["data"]["assessment_id"] == "a3f1c9e2-7b8d-4e5f-9a1b-2c3d4e5f6a7b"

    def test_response_contains_questions_and_answer_key(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.assessment_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "difficulty": "medium", "question_count": 2},
        )

        body = response.json()
        assert len(body["data"]["questions"]) == 2
        assert body["data"]["questions"][0]["question_order"] == 1
        assert "1" in body["data"]["answer_key"]

    def test_question_count_zero_returns_422(self):
        import api.fastapi_app as app_module
        app_module.assessment_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "question_count": 0},
        )
        assert response.status_code == 422

    def test_question_count_51_returns_422(self):
        import api.fastapi_app as app_module
        app_module.assessment_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "question_count": 51},
        )
        assert response.status_code == 422

    def test_invalid_difficulty_returns_422(self):
        import api.fastapi_app as app_module
        app_module.assessment_generator = AsyncMock()
        client = TestClient(app_module.app)

        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "difficulty": "extreme", "question_count": 5},
        )
        assert response.status_code == 422

    def test_insufficient_questions_returns_400(self):
        import api.fastapi_app as app_module
        from rag_features.assessment_generator import InsufficientQuestionsError

        mock_gen = AsyncMock()
        mock_gen.generate = AsyncMock(
            side_effect=InsufficientQuestionsError("Apenas 2 questoes encontradas")
        )
        app_module.assessment_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "filosofia", "difficulty": "hard", "question_count": 10},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "INSUFFICIENT_QUESTIONS"

    def test_generator_unavailable_returns_503(self):
        import api.fastapi_app as app_module
        app_module.assessment_generator = None

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"subject": "matematica", "question_count": 5},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "ASSESSMENT_UNAVAILABLE"

    def test_meta_contains_filters(self):
        import api.fastapi_app as app_module

        mock_gen = AsyncMock()
        mock_gen.generate = AsyncMock(return_value=SAMPLE_GENERATE_RESULT)
        app_module.assessment_generator = mock_gen

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/assessments/generate",
            json={
                "subject": "matematica",
                "difficulty": "medium",
                "question_count": 2,
                "years": [2022, 2023],
            },
        )

        body = response.json()
        assert body["meta"]["subject"] == "matematica"
        assert body["meta"]["difficulty"] == "medium"
        assert body["meta"]["years"] == [2022, 2023]
