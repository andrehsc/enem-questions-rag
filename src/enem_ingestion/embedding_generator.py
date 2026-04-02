"""
embedding_generator.py — Geração de embeddings via OpenAI com cache Redis.

Produz embeddings para ChunkData usando text-embedding-3-small em batches
de até 100 chunks, com cache Redis para evitar chamadas redundantes.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import redis as redis_module
from openai import OpenAI, RateLimitError, APIStatusError

from src.enem_ingestion.chunk_builder import ChunkData

logger = logging.getLogger(__name__)

TOKEN_LIMIT = 8192  # text-embedding-3-small máximo por texto


class TokenLimitError(Exception):
    """Lançado quando chunk.token_count excede o limite da API."""
    pass


@dataclass
class EmbeddingResult:
    content_hash: str       # SHA-256 hex — identifica o chunk
    embedding: List[float]  # 1536 dimensões (text-embedding-3-small)
    tokens_used: int        # tokens consumidos (0 se veio do cache)
    from_cache: bool        # True se embedding veio do Redis


class EmbeddingGenerator:
    """
    Gera embeddings OpenAI com cache Redis.

    Uso típico:
        gen = EmbeddingGenerator(api_key=os.environ["OPENAI_API_KEY"])
        results = gen.generate_embeddings(chunks)
        print(gen.tokens_used)
    """

    def __init__(
        self,
        api_key: str,
        redis_url: str = "redis://localhost:6380/1",
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        cache_ttl: int = 604800,  # 7 dias em segundos
        max_retries: int = 3,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._redis = redis_module.from_url(redis_url, decode_responses=True)
        self.model = model
        self.batch_size = batch_size
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self._tokens_used: int = 0

    # ------------------------------------------------------------------
    # Propriedade pública
    # ------------------------------------------------------------------

    @property
    def tokens_used(self) -> int:
        """Total de tokens consumidos via API nesta instância."""
        return self._tokens_used

    # ------------------------------------------------------------------
    # Cache Redis
    # ------------------------------------------------------------------

    def _cache_key(self, content_hash: str) -> str:
        return f"emb:{content_hash}"

    def _get_from_cache(self, content_hash: str) -> Optional[List[float]]:
        """Retorna embedding do Redis ou None se não encontrado."""
        raw = self._redis.get(self._cache_key(content_hash))
        if raw is None:
            return None
        return json.loads(raw)

    def _save_to_cache(self, content_hash: str, embedding: List[float]) -> None:
        """Persiste embedding no Redis com TTL configurado."""
        self._redis.setex(
            self._cache_key(content_hash),
            self.cache_ttl,
            json.dumps(embedding),
        )

    # ------------------------------------------------------------------
    # Chamada OpenAI com retry exponencial
    # ------------------------------------------------------------------

    def _call_openai_with_retry(self, texts: List[str]) -> tuple[List[List[float]], int]:
        """
        Chama a API OpenAI para gerar embeddings.

        Retorna (embeddings, tokens_used).
        Retry exponencial em RateLimitError ou APIStatusError 5xx.
        Delay inicial: 1s, dobra a cada tentativa.
        Lança exceção se todas as tentativas falharem.
        """
        delay = 1.0
        last_exc: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self._client.embeddings.create(
                    input=texts,
                    model=self.model,
                )
                embeddings = [item.embedding for item in response.data]
                tokens = response.usage.total_tokens
                return embeddings, tokens

            except RateLimitError as exc:
                last_exc = exc
                if attempt == self.max_retries - 1:
                    break
                logger.warning(
                    "RateLimitError tentativa %d/%d — aguardando %.1fs",
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                time.sleep(delay)
                delay *= 2

            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code < 500 or attempt == self.max_retries - 1:
                    raise
                logger.warning(
                    "APIStatusError %d tentativa %d/%d — aguardando %.1fs",
                    exc.status_code,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                time.sleep(delay)
                delay *= 2

        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # API pública principal
    # ------------------------------------------------------------------

    def generate_embeddings(self, chunks: List[ChunkData]) -> List[EmbeddingResult]:
        """
        Gera embeddings para lista de ChunkData.

        Fluxo:
          1. Valida token_count de todos os chunks (lança TokenLimitError se > 8192)
          2. Verifica o cache Redis por content_hash
          3. Agrupa cache misses em batches de até batch_size
          4. Chama OpenAI com retry, armazena no cache, acumula tokens_used

        Retorna EmbeddingResult para cada chunk na mesma ordem de entrada.
        """
        results: List[EmbeddingResult] = []
        cache_misses: List[ChunkData] = []
        miss_indices: List[int] = []  # índice original em `chunks`

        # Fase 1: validar + verificar cache
        for idx, chunk in enumerate(chunks):
            if chunk.token_count > TOKEN_LIMIT:
                raise TokenLimitError(
                    f"Chunk excede limite de {TOKEN_LIMIT} tokens: "
                    f"question_id={chunk.question_id} "
                    f"chunk_type={chunk.chunk_type} "
                    f"tokens={chunk.token_count}"
                )

            cached = self._get_from_cache(chunk.content_hash)
            if cached is not None:
                results.append(EmbeddingResult(
                    content_hash=chunk.content_hash,
                    embedding=cached,
                    tokens_used=0,
                    from_cache=True,
                ))
                logger.debug("cache hit: %s", chunk.content_hash[:12])
            else:
                # placeholder — será preenchido após chamadas à API
                results.append(None)  # type: ignore[arg-type]
                cache_misses.append(chunk)
                miss_indices.append(idx)

        # Fase 2: processar cache misses em batches
        for batch_start in range(0, len(cache_misses), self.batch_size):
            batch = cache_misses[batch_start : batch_start + self.batch_size]
            texts = [c.content for c in batch]

            logger.info(
                "Gerando embeddings: batch %d-%d de %d cache misses",
                batch_start,
                batch_start + len(batch) - 1,
                len(cache_misses),
            )

            embeddings, tokens = self._call_openai_with_retry(texts)
            self._tokens_used += tokens

            tokens_per_chunk = max(1, tokens // len(batch))

            for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                self._save_to_cache(chunk.content_hash, embedding)
                original_idx = miss_indices[batch_start + i]
                results[original_idx] = EmbeddingResult(
                    content_hash=chunk.content_hash,
                    embedding=embedding,
                    tokens_used=tokens_per_chunk,
                    from_cache=False,
                )
                logger.debug(
                    "embedding gerado: %s tokens_usados=%d",
                    chunk.content_hash[:12],
                    tokens_per_chunk,
                )

        return results
