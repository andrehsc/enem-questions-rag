#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for PgVectorSearch — Story 3.1
100% mocked: no real database, no OpenAI, no Redis
"""

import pytest
import json
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestPgVectorSearchInit:
    """AC6: Factory function selects implementation based on VECTOR_STORE env var"""

    def test_factory_returns_pgvector_when_env_set(self, monkeypatch):
        """VECTOR_STORE=pgvector should return PgVectorSearch instance"""
        monkeypatch.setenv("VECTOR_STORE", "pgvector")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from rag_features.semantic_search import create_semantic_search, PgVectorSearch

        instance = create_semantic_search()
        assert isinstance(instance, PgVectorSearch)

    def test_factory_returns_chromadb_fallback(self, monkeypatch):
        """VECTOR_STORE=chromadb should NOT return PgVectorSearch"""
        monkeypatch.setenv("VECTOR_STORE", "chromadb")

        from rag_features.semantic_search import create_semantic_search, PgVectorSearch

        instance = create_semantic_search()
        assert not isinstance(instance, PgVectorSearch)


class TestSearchQuestions:
    """AC1-5: PgVectorSearch.search_questions functionality"""

    @pytest.fixture
    def pgvector_search(self):
        """Create PgVectorSearch with mocked dependencies"""
        from rag_features.semantic_search import PgVectorSearch

        search = PgVectorSearch(
            database_url="postgresql://test:test@localhost:5432/test",
            openai_api_key="sk-test",
            redis_url="redis://localhost:6379/0",
        )
        # Mock the engine and redis
        search._engine = MagicMock()
        search._redis = MagicMock()
        search._openai = MagicMock()
        return search

    @pytest.mark.asyncio
    async def test_returns_results_with_required_fields(self, pgvector_search):
        """AC1,4: Results contain question_id, full_text, subject, year, similarity_score"""
        mock_embedding = [0.1] * 1536

        # Mock Redis cache miss
        pgvector_search._redis.get.return_value = None

        # Mock OpenAI embedding
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        # Mock DB results
        mock_row = MagicMock()
        mock_row._mapping = {
            "question_id": 42,
            "question_text": "Sobre fotossíntese...\nA) opt1\nB) opt2",
            "subject": "ciencias_natureza",
            "year": 2023,
            "chunk_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "chunk_type": "full",
            "chunk_content": "Sobre fotossíntese...",
            "similarity_score": 0.91,
        }
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        results = await pgvector_search.search_questions("fotossíntese", limit=5)

        assert len(results) == 1
        r = results[0]
        assert r["question_id"] == 42
        assert r["full_text"] == "Sobre fotossíntese..."  # from chunk_content, not question_text
        assert "chunk_id" in r
        assert r["subject"] == "ciencias_natureza"
        assert r["year"] == 2023
        assert r["similarity_score"] == 0.91

    @pytest.mark.asyncio
    async def test_filter_by_subject_adds_where_clause(self, pgvector_search):
        """AC3: Passing subject= adds SQL filter"""
        mock_embedding = [0.1] * 1536
        pgvector_search._redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        await pgvector_search.search_questions(
            "fotossíntese", limit=5, subject="ciencias_natureza"
        )

        # Verify the SQL executed contains subject filter
        call_args = mock_conn.execute.call_args
        sql_text = str(call_args[0][0])
        assert "subject" in sql_text.lower()

    @pytest.mark.asyncio
    async def test_filter_by_year_adds_where_clause(self, pgvector_search):
        """AC3: Passing year= adds SQL filter"""
        mock_embedding = [0.1] * 1536
        pgvector_search._redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        await pgvector_search.search_questions("fotossíntese", limit=5, year=2023)

        call_args = mock_conn.execute.call_args
        sql_text = str(call_args[0][0])
        assert "year" in sql_text.lower()

    @pytest.mark.asyncio
    async def test_deduplicates_by_question_id(self, pgvector_search):
        """AC5: Two chunks from same question_id result in 1 question"""
        mock_embedding = [0.1] * 1536
        pgvector_search._redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        # Two rows with same question_id (full + context chunks)
        row1 = MagicMock()
        row1._mapping = {
            "question_id": 42,
            "question_text": "Texto questão 42",
            "subject": "ciencias_natureza",
            "year": 2023,
            "chunk_id": "aaaaaaaa-0000-0000-0000-000000000001",
            "chunk_type": "full",
            "chunk_content": "Texto completo",
            "similarity_score": 0.91,
        }
        row2 = MagicMock()
        row2._mapping = {
            "question_id": 42,
            "question_text": "Texto questão 42",
            "subject": "ciencias_natureza",
            "year": 2023,
            "chunk_id": "aaaaaaaa-0000-0000-0000-000000000002",
            "chunk_type": "context",
            "chunk_content": "Texto base",
            "similarity_score": 0.85,
        }

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row1, row2]
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        results = await pgvector_search.search_questions("fotossíntese", limit=5)

        assert len(results) == 1
        assert results[0]["question_id"] == 42

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self, pgvector_search):
        """AC5: Empty result set returns empty list"""
        mock_embedding = [0.1] * 1536
        pgvector_search._redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        results = await pgvector_search.search_questions("algo inexistente", limit=5)

        assert results == []


class TestQueryEmbeddingCache:
    """AC: Redis cache for query embeddings"""

    @pytest.fixture
    def pgvector_search(self):
        from rag_features.semantic_search import PgVectorSearch

        search = PgVectorSearch(
            database_url="postgresql://test:test@localhost:5432/test",
            openai_api_key="sk-test",
            redis_url="redis://localhost:6379/0",
        )
        search._engine = MagicMock()
        search._redis = MagicMock()
        search._openai = MagicMock()
        return search

    @pytest.mark.asyncio
    async def test_cache_hit_skips_openai_call(self, pgvector_search):
        """Cache hit should skip OpenAI API call"""
        cached_embedding = [0.5] * 1536
        pgvector_search._redis.get.return_value = json.dumps(cached_embedding).encode()

        # Mock DB to return empty to keep test simple
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        await pgvector_search.search_questions("fotossíntese", limit=5)

        # OpenAI should NOT have been called
        pgvector_search._openai.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_openai_and_stores(self, pgvector_search):
        """Cache miss should call OpenAI and store in Redis"""
        mock_embedding = [0.1] * 1536
        pgvector_search._redis.get.return_value = None  # cache miss

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        pgvector_search._openai.embeddings.create.return_value = mock_response

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        pgvector_search._engine.connect.return_value = mock_conn

        await pgvector_search.search_questions("fotossíntese", limit=5)

        # OpenAI should have been called
        pgvector_search._openai.embeddings.create.assert_called_once()

        # Redis should have stored the result
        pgvector_search._redis.setex.assert_called_once()


class TestAddQuestionsToIndex:
    """AC1: add_questions_to_index raises NotImplementedError"""

    @pytest.mark.asyncio
    async def test_raises_not_implemented(self):
        from rag_features.semantic_search import PgVectorSearch

        search = PgVectorSearch(
            database_url="postgresql://test:test@localhost:5432/test",
            openai_api_key="sk-test",
        )
        search._engine = MagicMock()
        search._redis = MagicMock()
        search._openai = MagicMock()

        with pytest.raises(NotImplementedError, match="IngestionPipeline"):
            await search.add_questions_to_index([{"id": 1}])
