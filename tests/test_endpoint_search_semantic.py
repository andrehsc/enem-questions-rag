#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for POST /api/v1/search/semantic — Story 3.2
All mocked: no real DB, OpenAI, or Redis.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _patch_pgvector(monkeypatch):
    """Patch PgVectorSearch before importing app to avoid real connections."""
    # Prevent startup from creating real PgVectorSearch
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")


@pytest.fixture
def client():
    """TestClient with pgvector_search mocked."""
    import api.fastapi_app as app_module

    mock_search = AsyncMock()
    mock_search.search_questions = AsyncMock(return_value=[])
    app_module.pgvector_search = mock_search

    return TestClient(app_module.app)


@pytest.fixture
def mock_search():
    return AsyncMock()


SAMPLE_RESULTS = [
    {
        "question_id": 42,
        "full_text": "Sobre fotossíntese...\nA) opt1\nB) opt2",
        "subject": "ciencias_natureza",
        "year": 2023,
        "similarity_score": 0.9134,
    }
]


class TestSemanticSearchEndpoint:
    def test_valid_request_returns_200(self):
        import api.fastapi_app as app_module

        mock_search = AsyncMock()
        mock_search.search_questions = AsyncMock(return_value=SAMPLE_RESULTS)
        app_module.pgvector_search = mock_search

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "fotossíntese", "limit": 5},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert len(body["data"]) == 1
        assert body["data"][0]["question_id"] == 42
        assert body["meta"]["total"] == 1
        assert body["meta"]["query"] == "fotossíntese"

    def test_empty_query_returns_422(self, client):
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "", "limit": 5},
        )
        assert response.status_code == 422

    def test_limit_out_of_range_returns_422(self, client):
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "teste", "limit": 51},
        )
        assert response.status_code == 422

    def test_include_answer_false_omits_correct_answer(self):
        import api.fastapi_app as app_module

        mock_search = AsyncMock()
        mock_search.search_questions = AsyncMock(return_value=SAMPLE_RESULTS)
        app_module.pgvector_search = mock_search

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "fotossíntese", "include_answer": False},
        )

        assert response.status_code == 200
        assert response.json()["data"][0]["correct_answer"] is None

    @patch("api.fastapi_app._get_correct_answer", return_value="C")
    def test_include_answer_true_includes_correct_answer(self, mock_answer):
        import api.fastapi_app as app_module

        mock_search = AsyncMock()
        mock_search.search_questions = AsyncMock(return_value=SAMPLE_RESULTS)
        app_module.pgvector_search = mock_search

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "fotossíntese", "include_answer": True},
        )

        assert response.status_code == 200
        assert response.json()["data"][0]["correct_answer"] == "C"

    def test_search_unavailable_returns_503(self):
        import api.fastapi_app as app_module

        app_module.pgvector_search = None

        client = TestClient(app_module.app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "fotossíntese"},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "SEARCH_UNAVAILABLE"

    def test_filters_passed_to_pgvector_search(self):
        import api.fastapi_app as app_module

        mock_search = AsyncMock()
        mock_search.search_questions = AsyncMock(return_value=[])
        app_module.pgvector_search = mock_search

        client = TestClient(app_module.app)
        client.post(
            "/api/v1/search/semantic",
            json={
                "query": "fotossíntese",
                "subject": "ciencias_natureza",
                "year": 2023,
                "limit": 5,
            },
        )

        mock_search.search_questions.assert_called_once_with(
            query="fotossíntese",
            limit=5,
            year=2023,
            subject="ciencias_natureza",
        )
