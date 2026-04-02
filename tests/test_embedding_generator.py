"""
Testes unitários para embedding_generator.py — Story 2.1.

Todos os testes usam mocks — sem Redis real nem OpenAI real.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call

from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import (
    EmbeddingGenerator,
    EmbeddingResult,
    TokenLimitError,
    TOKEN_LIMIT,
)


# ─── Helpers de fixtures ─────────────────────────────────────────────────────


def make_chunk(
    content_hash: str = "a" * 64,
    token_count: int = 100,
    content: str = "texto de questão",
    question_id: str = "uuid-1",
    chunk_type: str = "full",
) -> ChunkData:
    return ChunkData(
        chunk_type=chunk_type,
        content=content,
        content_hash=content_hash,
        token_count=token_count,
        question_id=question_id,
    )


def make_openai_response(texts: list[str], tokens: int = 50) -> MagicMock:
    """Monta resposta fake da API openai.embeddings.create()."""
    response = MagicMock()
    response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3] * 512)  # 1536 dims
        for _ in texts
    ]
    response.usage = MagicMock(total_tokens=tokens)
    return response


@pytest.fixture
def mock_redis():
    with patch("src.enem_ingestion.embedding_generator.redis_module.from_url") as mock:
        redis_client = MagicMock()
        mock.return_value = redis_client
        yield redis_client


@pytest.fixture
def mock_openai():
    with patch("src.enem_ingestion.embedding_generator.OpenAI") as MockOpenAI:
        openai_client = MagicMock()
        MockOpenAI.return_value = openai_client
        yield openai_client


@pytest.fixture
def generator(mock_redis, mock_openai):
    """EmbeddingGenerator com Redis e OpenAI totalmente mockados."""
    return EmbeddingGenerator(api_key="test-key")


# ─── TestTokenLimitError ─────────────────────────────────────────────────────


class TestTokenLimitError:
    def test_raises_for_chunk_exceeding_8192_tokens(self, generator, mock_redis):
        chunk = make_chunk(token_count=TOKEN_LIMIT + 1)
        mock_redis.get.return_value = None

        with pytest.raises(TokenLimitError, match=str(TOKEN_LIMIT)):
            generator.generate_embeddings([chunk])

    def test_raises_before_any_api_call(self, generator, mock_openai, mock_redis):
        """TokenLimitError deve ser lançado antes de qualquer chamada à API."""
        chunk = make_chunk(token_count=9000)
        mock_redis.get.return_value = None

        with pytest.raises(TokenLimitError):
            generator.generate_embeddings([chunk])

        mock_openai.embeddings.create.assert_not_called()

    def test_exactly_at_limit_does_not_raise(self, generator, mock_redis, mock_openai):
        """Chunk com exatamente 8192 tokens NÃO deve lançar TokenLimitError."""
        chunk = make_chunk(token_count=8192)
        mock_redis.get.return_value = None
        mock_openai.embeddings.create.return_value = make_openai_response([chunk.content])

        results = generator.generate_embeddings([chunk])  # não deve lançar

        assert len(results) == 1


# ─── TestRedisCache ───────────────────────────────────────────────────────────


class TestRedisCache:
    def test_cache_hit_returns_cached_embedding_without_openai_call(
        self, generator, mock_redis, mock_openai
    ):
        """Cache hit: OpenAI não deve ser chamado."""
        fake_embedding = [0.5] * 1536
        chunk = make_chunk(content_hash="b" * 64)
        mock_redis.get.return_value = json.dumps(fake_embedding)

        results = generator.generate_embeddings([chunk])

        mock_openai.embeddings.create.assert_not_called()
        assert len(results) == 1
        assert results[0].from_cache is True
        assert results[0].embedding == fake_embedding
        assert results[0].tokens_used == 0

    def test_cache_miss_calls_openai_and_stores_in_redis(
        self, generator, mock_redis, mock_openai
    ):
        """Cache miss: OpenAI chamado, resultado salvo no Redis."""
        chunk = make_chunk(content_hash="c" * 64)
        mock_redis.get.return_value = None
        mock_openai.embeddings.create.return_value = make_openai_response([chunk.content], tokens=30)

        results = generator.generate_embeddings([chunk])

        assert mock_openai.embeddings.create.call_count == 1
        assert results[0].from_cache is False

        # Verificar que o resultado foi salvo no Redis
        mock_redis.setex.assert_called_once()
        key_used = mock_redis.setex.call_args[0][0]
        assert "c" * 64 in key_used

    def test_cache_key_format(self, generator, mock_redis, mock_openai):
        """Cache key deve ter formato 'emb:{content_hash}'."""
        chunk = make_chunk(content_hash="d" * 64)
        mock_redis.get.return_value = None
        mock_openai.embeddings.create.return_value = make_openai_response([chunk.content])

        generator.generate_embeddings([chunk])

        get_key = mock_redis.get.call_args[0][0]
        assert get_key == f"emb:{'d' * 64}"


# ─── TestBatching ─────────────────────────────────────────────────────────────


class TestBatching:
    def test_101_chunks_split_into_two_openai_calls(
        self, generator, mock_redis, mock_openai
    ):
        """101 cache misses → 2 chamadas à API (100 + 1)."""
        chunks = [make_chunk(content_hash=f"{i:064d}") for i in range(101)]
        mock_redis.get.return_value = None
        mock_openai.embeddings.create.side_effect = [
            make_openai_response([c.content for c in chunks[:100]], tokens=1000),
            make_openai_response([c.content for c in chunks[100:]], tokens=10),
        ]

        results = generator.generate_embeddings(chunks)

        assert mock_openai.embeddings.create.call_count == 2
        assert len(results) == 101

        # Primeiro batch deve ter 100 itens
        first_call_texts = mock_openai.embeddings.create.call_args_list[0][1]["input"]
        assert len(first_call_texts) == 100

        # Segundo batch deve ter 1 item
        second_call_texts = mock_openai.embeddings.create.call_args_list[1][1]["input"]
        assert len(second_call_texts) == 1

    def test_exactly_100_chunks_uses_single_api_call(
        self, generator, mock_redis, mock_openai
    ):
        """Exatamente 100 cache misses → 1 única chamada à API."""
        chunks = [make_chunk(content_hash=f"{i:064d}") for i in range(100)]
        mock_redis.get.return_value = None
        mock_openai.embeddings.create.return_value = make_openai_response(
            [c.content for c in chunks], tokens=500
        )

        results = generator.generate_embeddings(chunks)

        assert mock_openai.embeddings.create.call_count == 1
        assert len(results) == 100

    def test_mixed_cache_hits_and_misses_correct_ordering(
        self, generator, mock_redis, mock_openai
    ):
        """Resultados devem preservar a ordem de entrada mesmo com mix de hits/misses."""
        cached_embedding = [0.9] * 1536
        chunks = [
            make_chunk(content_hash="hit1" + "0" * 60),   # cache hit
            make_chunk(content_hash="miss1" + "0" * 59),  # cache miss
            make_chunk(content_hash="hit2" + "0" * 60),   # cache hit
        ]

        def fake_redis_get(key: str):
            if "hit" in key:
                return json.dumps(cached_embedding)
            return None

        mock_redis.get.side_effect = fake_redis_get
        mock_openai.embeddings.create.return_value = make_openai_response(
            [chunks[1].content], tokens=20
        )

        results = generator.generate_embeddings(chunks)

        assert results[0].from_cache is True
        assert results[1].from_cache is False
        assert results[2].from_cache is True


# ─── TestRetry ────────────────────────────────────────────────────────────────


class TestRetry:
    def test_rate_limit_retried_up_to_max_retries(
        self, generator, mock_redis, mock_openai
    ):
        """RateLimitError deve ser retirado até max_retries vezes."""
        from openai import RateLimitError as OAIRateLimitError

        chunk = make_chunk()
        mock_redis.get.return_value = None

        exc = OAIRateLimitError("rate limit", response=MagicMock(status_code=429), body={})
        mock_openai.embeddings.create.side_effect = [exc, exc, exc]

        with patch("time.sleep"):
            with pytest.raises(OAIRateLimitError):
                generator.generate_embeddings([chunk])

        assert mock_openai.embeddings.create.call_count == 3

    def test_rate_limit_succeeds_on_second_attempt(
        self, generator, mock_redis, mock_openai
    ):
        """Falha na 1ª tentativa, sucesso na 2ª → deve retornar resultados."""
        from openai import RateLimitError as OAIRateLimitError

        chunk = make_chunk()
        mock_redis.get.return_value = None

        exc = OAIRateLimitError("rate limit", response=MagicMock(status_code=429), body={})
        success = make_openai_response([chunk.content], tokens=20)
        mock_openai.embeddings.create.side_effect = [exc, success]

        with patch("time.sleep"):
            results = generator.generate_embeddings([chunk])

        assert len(results) == 1
        assert results[0].from_cache is False
        assert mock_openai.embeddings.create.call_count == 2

    def test_5xx_error_is_retried(self, generator, mock_redis, mock_openai):
        """APIStatusError 500 deve ser retried."""
        from openai import APIStatusError

        chunk = make_chunk()
        mock_redis.get.return_value = None

        exc = APIStatusError("server error", response=MagicMock(status_code=500), body={})
        success = make_openai_response([chunk.content], tokens=15)
        mock_openai.embeddings.create.side_effect = [exc, success]

        with patch("time.sleep"):
            results = generator.generate_embeddings([chunk])

        assert len(results) == 1
        assert mock_openai.embeddings.create.call_count == 2

    def test_4xx_error_is_not_retried(self, generator, mock_redis, mock_openai):
        """APIStatusError 4xx (exceto 429) NÃO deve ser retried."""
        from openai import APIStatusError

        chunk = make_chunk()
        mock_redis.get.return_value = None

        exc = APIStatusError("bad request", response=MagicMock(status_code=400), body={})
        mock_openai.embeddings.create.side_effect = [exc]

        with pytest.raises(APIStatusError):
            generator.generate_embeddings([chunk])

        # Apenas 1 chamada — sem retry
        assert mock_openai.embeddings.create.call_count == 1

    def test_sleep_duration_doubles_exponentially(
        self, generator, mock_redis, mock_openai
    ):
        """Delay deve dobrar: 1s → 2s."""
        from openai import RateLimitError as OAIRateLimitError

        chunk = make_chunk()
        mock_redis.get.return_value = None

        exc = OAIRateLimitError("rate limit", response=MagicMock(status_code=429), body={})
        success = make_openai_response([chunk.content], tokens=10)
        mock_openai.embeddings.create.side_effect = [exc, exc, success]

        with patch("time.sleep") as mock_sleep:
            generator.generate_embeddings([chunk])

        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0


# ─── TestTokenTracking ────────────────────────────────────────────────────────


class TestTokenTracking:
    def test_tokens_used_accumulates_across_calls(
        self, generator, mock_redis, mock_openai
    ):
        """tokens_used deve acumular entre múltiplas chamadas a generate_embeddings."""
        chunks_1 = [make_chunk(content_hash="e" * 64)]
        chunks_2 = [make_chunk(content_hash="f" * 64)]
        mock_redis.get.return_value = None

        mock_openai.embeddings.create.side_effect = [
            make_openai_response([c.content for c in chunks_1], tokens=50),
            make_openai_response([c.content for c in chunks_2], tokens=30),
        ]

        generator.generate_embeddings(chunks_1)
        generator.generate_embeddings(chunks_2)

        assert generator.tokens_used == 80

    def test_cache_hits_do_not_add_to_tokens_used(
        self, generator, mock_redis, mock_openai
    ):
        """Cache hits não devem incrementar tokens_used."""
        chunk = make_chunk(content_hash="g" * 64)
        mock_redis.get.return_value = json.dumps([0.1] * 1536)

        generator.generate_embeddings([chunk])

        assert generator.tokens_used == 0
        mock_openai.embeddings.create.assert_not_called()

    def test_initial_tokens_used_is_zero(self, generator):
        """Novo generator começa com tokens_used == 0."""
        assert generator.tokens_used == 0
