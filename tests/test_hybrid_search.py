"""
Hybrid Search Tests — Story 7.2.

Unit tests for PgVectorSearch hybrid search: semantic, text, and hybrid modes
with Reciprocal Rank Fusion (RRF).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.rag_features.semantic_search import PgVectorSearch


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_pgvector_search():
    """Create PgVectorSearch with mocked internals."""
    search = PgVectorSearch(
        database_url="postgresql://test:test@localhost:5432/test",
        openai_api_key="sk-test",
        redis_url="redis://localhost:6379/0",
    )
    search._engine = MagicMock()
    search._redis = MagicMock()
    search._openai = MagicMock()
    # Default: Redis cache miss
    search._redis.get.return_value = None
    # Default: OpenAI returns a 1536-dim embedding
    mock_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    search._openai.embeddings.create.return_value = mock_response
    return search


def _make_db_row(**kwargs):
    """Create a mock DB row with _mapping attribute."""
    row = MagicMock()
    row._mapping = kwargs
    return row


def _setup_db_mock(search, rows):
    """Configure search._engine.connect() to return given rows."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    search._engine.connect.return_value = mock_conn
    return mock_conn


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
class TestSearchModeSemantic:
    """Mode 'semantic' uses only vector search."""

    async def test_search_mode_semantic_only(self):
        search = _make_pgvector_search()
        rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", similarity_score=0.95,
            ),
        ]
        _setup_db_mock(search, rows)

        results = await search.search_questions("test", search_mode="semantic")

        assert len(results) == 1
        assert results[0]["similarity_score"] == 0.95
        # OpenAI embeddings should be called (semantic needs embeddings)
        search._openai.embeddings.create.assert_called_once()


@pytest.mark.asyncio
class TestSearchModeText:
    """Mode 'text' uses only tsvector search."""

    async def test_search_mode_text_only(self):
        search = _make_pgvector_search()
        rows = [
            _make_db_row(
                question_id=2, question_text="Q2", subject="linguagens",
                year=2023, chunk_id="c2", chunk_type="full",
                chunk_content="Content 2", text_score=0.75,
            ),
        ]
        _setup_db_mock(search, rows)

        results = await search.search_questions("fotossíntese", search_mode="text")

        assert len(results) == 1
        assert results[0]["similarity_score"] == 0.75
        # OpenAI embeddings should NOT be called (text mode doesn't need embeddings)
        search._openai.embeddings.create.assert_not_called()


@pytest.mark.asyncio
class TestSearchModeHybrid:
    """Mode 'hybrid' combines semantic + text with RRF."""

    async def test_search_mode_hybrid_rrf(self):
        search = _make_pgvector_search()

        # We need separate DB responses for semantic and text sub-queries.
        # First call = semantic, Second call = text
        semantic_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", similarity_score=0.95,
            ),
            _make_db_row(
                question_id=2, question_text="Q2", subject="linguagens",
                year=2023, chunk_id="c2", chunk_type="full",
                chunk_content="Content 2", similarity_score=0.80,
            ),
        ]
        text_rows = [
            _make_db_row(
                question_id=2, question_text="Q2", subject="linguagens",
                year=2023, chunk_id="c2", chunk_type="full",
                chunk_content="Content 2", text_score=0.90,
            ),
            _make_db_row(
                question_id=3, question_text="Q3", subject="ciencias_natureza",
                year=2023, chunk_id="c3", chunk_type="full",
                chunk_content="Content 3", text_score=0.70,
            ),
        ]

        # Sequential DB calls: first semantic, then text
        mock_conn = MagicMock()
        mock_result_semantic = MagicMock()
        mock_result_semantic.fetchall.return_value = semantic_rows
        mock_result_text = MagicMock()
        mock_result_text.fetchall.return_value = text_rows
        mock_conn.execute.side_effect = [mock_result_semantic, mock_result_text]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        search._engine.connect.return_value = mock_conn

        results = await search.search_questions("test query", search_mode="hybrid")

        # Should have 3 unique questions (1, 2, 3)
        assert len(results) == 3
        qids = [r["question_id"] for r in results]
        assert set(qids) == {1, 2, 3}

        # Q2 should rank highest (appears in both rankings)
        assert results[0]["question_id"] == 2

        # All scores should be between 0 and 1
        for r in results:
            assert 0 < r["similarity_score"] <= 1.0

    async def test_rrf_scoring(self):
        """Verify RRF score calculation with controlled ranks."""
        search = _make_pgvector_search()
        K = 60

        # Q1: rank 1 in vector, rank 2 in text
        # Q2: rank 2 in vector, rank 1 in text
        # Expected: Q1 rrf = 1/61 + 1/62, Q2 rrf = 1/62 + 1/61 → equal!
        semantic_rows = [
            _make_db_row(
                question_id=10, question_text="Q10", subject="matematica",
                year=2023, chunk_id="c10", chunk_type="full",
                chunk_content="Content 10", similarity_score=0.99,
            ),
            _make_db_row(
                question_id=20, question_text="Q20", subject="linguagens",
                year=2023, chunk_id="c20", chunk_type="full",
                chunk_content="Content 20", similarity_score=0.90,
            ),
        ]
        text_rows = [
            _make_db_row(
                question_id=20, question_text="Q20", subject="linguagens",
                year=2023, chunk_id="c20", chunk_type="full",
                chunk_content="Content 20", text_score=0.95,
            ),
            _make_db_row(
                question_id=10, question_text="Q10", subject="matematica",
                year=2023, chunk_id="c10", chunk_type="full",
                chunk_content="Content 10", text_score=0.80,
            ),
        ]

        mock_conn = MagicMock()
        mock_result_semantic = MagicMock()
        mock_result_semantic.fetchall.return_value = semantic_rows
        mock_result_text = MagicMock()
        mock_result_text.fetchall.return_value = text_rows
        mock_conn.execute.side_effect = [mock_result_semantic, mock_result_text]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        search._engine.connect.return_value = mock_conn

        results = await search.search_questions("test", limit=10, search_mode="hybrid")

        # Both should have the same RRF score (symmetric ranks)
        assert len(results) == 2
        assert results[0]["similarity_score"] == results[1]["similarity_score"]

        # Verify actual RRF score
        expected_rrf = 1 / (K + 1) + 1 / (K + 2)
        max_rrf = 1 / (K + 1) + 1 / (K + 1)
        expected_normalized = round(expected_rrf / max_rrf, 6)
        assert results[0]["similarity_score"] == expected_normalized

    async def test_hybrid_deduplication(self):
        """Hybrid results should not contain duplicate questions."""
        search = _make_pgvector_search()

        # Same question in both result sets
        semantic_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", similarity_score=0.95,
            ),
        ]
        text_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", text_score=0.80,
            ),
        ]

        mock_conn = MagicMock()
        mock_result_semantic = MagicMock()
        mock_result_semantic.fetchall.return_value = semantic_rows
        mock_result_text = MagicMock()
        mock_result_text.fetchall.return_value = text_rows
        mock_conn.execute.side_effect = [mock_result_semantic, mock_result_text]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        search._engine.connect.return_value = mock_conn

        results = await search.search_questions("test", search_mode="hybrid")

        # Only 1 result — no duplicates
        assert len(results) == 1
        assert results[0]["question_id"] == 1
        # Score should be max (rank 1 in both)
        assert results[0]["similarity_score"] == 1.0

    async def test_empty_text_results_fallback(self):
        """If tsvector returns empty, hybrid falls back to semantic only."""
        search = _make_pgvector_search()

        semantic_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", similarity_score=0.90,
            ),
        ]
        text_rows = []  # No text matches

        mock_conn = MagicMock()
        mock_result_semantic = MagicMock()
        mock_result_semantic.fetchall.return_value = semantic_rows
        mock_result_text = MagicMock()
        mock_result_text.fetchall.return_value = text_rows
        mock_conn.execute.side_effect = [mock_result_semantic, mock_result_text]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        search._engine.connect.return_value = mock_conn

        results = await search.search_questions("xyz123", search_mode="hybrid")

        # Should fall back to semantic results
        assert len(results) == 1
        assert results[0]["similarity_score"] == 0.90

    async def test_backward_compatibility(self):
        """Calling without search_mode defaults to hybrid."""
        search = _make_pgvector_search()

        semantic_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", similarity_score=0.90,
            ),
        ]
        text_rows = [
            _make_db_row(
                question_id=1, question_text="Q1", subject="matematica",
                year=2023, chunk_id="c1", chunk_type="full",
                chunk_content="Content 1", text_score=0.85,
            ),
        ]

        mock_conn = MagicMock()
        mock_result_semantic = MagicMock()
        mock_result_semantic.fetchall.return_value = semantic_rows
        mock_result_text = MagicMock()
        mock_result_text.fetchall.return_value = text_rows
        mock_conn.execute.side_effect = [mock_result_semantic, mock_result_text]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        search._engine.connect.return_value = mock_conn

        # No search_mode — should default to "hybrid"
        results = await search.search_questions("test query")

        assert len(results) == 1
        # RRF score (rank 1 in both = max = 1.0)
        assert results[0]["similarity_score"] == 1.0
