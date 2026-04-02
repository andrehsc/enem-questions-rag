# Story 2.1: Embedding Generator com Cache Redis

**Status:** review
**Epic:** 2 — Pipeline de Embeddings: Geração e Ingestão
**Story ID:** 2.1
**Story Key:** `2-1-embedding-generator-com-cache-redis`
**Criado:** 2026-04-02

---

## Story

Como desenvolvedor,
Quero um módulo `embedding_generator.py` que gere embeddings via OpenAI com cache Redis,
Para que o sistema não faça chamadas desnecessárias à API ao re-ingerir questões.

---

## Acceptance Criteria

1. Chama `text-embedding-3-small` em batches de até 100 chunks por request
2. Verifica Redis cache por `content_hash` antes de chamar a API (TTL 7 dias = 604800s)
3. Armazena embedding no Redis após chamada bem-sucedida
4. Implementa retry exponencial (3 tentativas, delays: 1s, 2s, 4s) em caso de rate limit (429) ou erros 5xx
5. Registra `tokens_used` por sessão para controle de custo (acumulado via atributo da instância)
6. Lança `TokenLimitError` se `chunk.token_count > 8192`

---

## Tasks / Subtasks

- [x] **Task 1: Adicionar dependências** (pré-requisito)
  - [x] 1.1 Adicionar `openai>=1.0.0` e `redis>=4.6.0` ao `requirements.txt`

- [x] **Task 2: Criar `src/enem_ingestion/embedding_generator.py`** (AC: 1–6)
  - [x] 2.1 Definir exceção `TokenLimitError(Exception)` e dataclass `EmbeddingResult`
  - [x] 2.2 Implementar `EmbeddingGenerator.__init__` — recebe `api_key`, `redis_url`, `model`, `batch_size`, `cache_ttl`
  - [x] 2.3 Implementar `_get_from_cache(content_hash)` → `Optional[List[float]]`
  - [x] 2.4 Implementar `_save_to_cache(content_hash, embedding)` com TTL
  - [x] 2.5 Implementar `_call_openai_with_retry(texts)` → `List[List[float]]` — retry exponencial 3x
  - [x] 2.6 Implementar `generate_embeddings(chunks)` → `List[EmbeddingResult]` — orquestra cache + batch + API
  - [x] 2.7 Acumular `self.tokens_used` a cada chamada à API bem-sucedida

- [x] **Task 3: Criar `tests/test_embedding_generator.py`** (AC: 1–6, testes unit com mocks)
  - [x] 3.1 Testar `TokenLimitError` lançado para chunk com `token_count > 8192`
  - [x] 3.2 Testar cache hit: Redis retorna embedding → OpenAI NÃO é chamado
  - [x] 3.3 Testar cache miss: Redis retorna None → OpenAI é chamado, resultado armazenado no Redis
  - [x] 3.4 Testar batch de mais de 100 chunks → OpenAI chamado em múltiplos batches de ≤100
  - [x] 3.5 Testar retry exponencial: OpenAI lança `RateLimitError` → retenta até 3x
  - [x] 3.6 Testar `tokens_used` acumulado corretamente após múltiplas chamadas
  - [x] 3.7 Testar falha definitiva após 3 tentativas → exceção propagada

---

## Dev Notes

### Arquivo a criar

```
src/enem_ingestion/embedding_generator.py   ← NOVO
tests/test_embedding_generator.py           ← NOVO
requirements.txt                            ← MODIFICAR (adicionar openai, redis)
```

**NÃO modificar:** `chunk_builder.py`, `config.py`, nenhum teste existente.

### Dependências a adicionar em `requirements.txt`

```
openai>=1.0.0
redis>=4.6.0
```

> `tiktoken` já está em requirements.txt — NÃO duplicar.

### API pública do módulo

```python
# src/enem_ingestion/embedding_generator.py

from dataclasses import dataclass
from typing import List, Optional
from src.enem_ingestion.chunk_builder import ChunkData


class TokenLimitError(Exception):
    """Lançado quando chunk.token_count > 8192 (limite text-embedding-3-small)."""
    pass


@dataclass
class EmbeddingResult:
    content_hash: str          # SHA-256 hex do chunk
    embedding: List[float]     # 1536 dimensões
    tokens_used: int           # tokens consumidos nessa geração
    from_cache: bool           # True se veio do Redis


class EmbeddingGenerator:
    def __init__(
        self,
        api_key: str,
        redis_url: str = "redis://localhost:6380/1",
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        cache_ttl: int = 604800,  # 7 dias
        max_retries: int = 3,
    ): ...

    def generate_embeddings(self, chunks: List[ChunkData]) -> List[EmbeddingResult]:
        """
        Gera embeddings para lista de chunks.
        - Verifica cache Redis por content_hash antes de chamar API
        - Agrupa cache misses em batches de até batch_size chunks
        - Retry exponencial em rate limit ou 5xx
        - Acumula self.tokens_used
        - Lança TokenLimitError se chunk.token_count > 8192
        """
        ...

    @property
    def tokens_used(self) -> int:
        """Total de tokens consumidos nesta instância desde a criação."""
        ...
```

### Redis: configuração e chave de cache

```python
import redis

# URL padrão do projeto (redis_port=6380, db=1 conforme config.py)
redis_url = "redis://localhost:6380/1"

# Padrão de chave de cache
cache_key = f"emb:{content_hash}"  # ex: "emb:a3f4b2..."

# Armazenar embedding como JSON serializado
import json
client.setex(cache_key, cache_ttl, json.dumps(embedding))

# Recuperar
raw = client.get(cache_key)
if raw:
    embedding = json.loads(raw)
```

### OpenAI client (API v1.0+)

```python
from openai import OpenAI, RateLimitError, APIStatusError

client = OpenAI(api_key=api_key)

response = client.embeddings.create(
    input=texts,          # List[str], máximo 100 por chamada
    model="text-embedding-3-small",
)

# Extrair embeddings da resposta
embeddings = [item.embedding for item in response.data]
tokens = response.usage.total_tokens
```

> **IMPORTANTE:** A API `openai>=1.0.0` usa `OpenAI()` (não `openai.Embedding.create`). O estilo antigo (`openai.Embedding.create`) foi **removido** na v1.0. Sempre usar o novo cliente.

### Retry exponencial

```python
import time
import logging

logger = logging.getLogger(__name__)

def _call_openai_with_retry(self, texts: List[str]) -> tuple[List[List[float]], int]:
    """Retorna (embeddings, tokens_used). Retry 3x em RateLimitError ou 5xx."""
    delay = 1.0
    for attempt in range(self.max_retries):
        try:
            response = self._client.embeddings.create(
                input=texts,
                model=self.model,
            )
            return [item.embedding for item in response.data], response.usage.total_tokens
        except RateLimitError as e:
            if attempt == self.max_retries - 1:
                raise
            logger.warning("RateLimitError attempt %d/%d, sleeping %.1fs", attempt+1, self.max_retries, delay)
            time.sleep(delay)
            delay *= 2
        except APIStatusError as e:
            if e.status_code < 500 or attempt == self.max_retries - 1:
                raise
            logger.warning("APIStatusError %d attempt %d/%d, sleeping %.1fs", e.status_code, attempt+1, self.max_retries, delay)
            time.sleep(delay)
            delay *= 2
```

### Limite de tokens

- `text-embedding-3-small` aceita até **8191 tokens** por texto
- A Story usa 8192 como limite de guarda (inclusive)
- O `token_count` já está calculado em `ChunkData.token_count` pelo `chunk_builder.py`
- **Não recalcular com tiktoken** — usar `chunk.token_count` diretamente

```python
if chunk.token_count > 8192:
    raise TokenLimitError(
        f"Chunk excede limite: question_id={chunk.question_id} "
        f"chunk_type={chunk.chunk_type} tokens={chunk.token_count}"
    )
```

### Lógica de `generate_embeddings` (pseudo-código)

```python
def generate_embeddings(self, chunks: List[ChunkData]) -> List[EmbeddingResult]:
    results: List[EmbeddingResult] = []
    cache_misses: List[ChunkData] = []

    # 1) Validar token limit e verificar cache
    for chunk in chunks:
        if chunk.token_count > 8192:
            raise TokenLimitError(...)

        cached = self._get_from_cache(chunk.content_hash)
        if cached is not None:
            results.append(EmbeddingResult(
                content_hash=chunk.content_hash,
                embedding=cached,
                tokens_used=0,
                from_cache=True,
            ))
        else:
            cache_misses.append(chunk)

    # 2) Processar cache misses em batches
    for i in range(0, len(cache_misses), self.batch_size):
        batch = cache_misses[i : i + self.batch_size]
        texts = [c.content for c in batch]

        embeddings, tokens = self._call_openai_with_retry(texts)
        self._tokens_used += tokens

        for chunk, embedding in zip(batch, embeddings):
            self._save_to_cache(chunk.content_hash, embedding)
            results.append(EmbeddingResult(
                content_hash=chunk.content_hash,
                embedding=embedding,
                tokens_used=tokens // len(batch),  # aproximação por chunk
                from_cache=False,
            ))

    return results
```

### Como mockar nas unit tests

```python
import pytest
from unittest.mock import MagicMock, patch
from src.enem_ingestion.embedding_generator import EmbeddingGenerator, TokenLimitError
from src.enem_ingestion.chunk_builder import ChunkData

def make_chunk(content_hash="abc123", token_count=100) -> ChunkData:
    return ChunkData(
        chunk_type="full",
        content="texto de questão",
        content_hash=content_hash,
        token_count=token_count,
        question_id="uuid-1",
    )

@pytest.fixture
def generator(mocker):
    mocker.patch("redis.from_url")  # ou patch no __init__
    mocker.patch("openai.OpenAI")
    return EmbeddingGenerator(api_key="test-key")
```

> **NUNCA** chamar Redis real ou OpenAI real nos unit tests. Todos os testes devem usar mocks via `pytest-mock` (já em requirements.txt).

### Variáveis de ambiente esperadas

```bash
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # default
EMBEDDING_BATCH_SIZE=100                        # default
EMBEDDING_CACHE_TTL=604800                      # default (7 dias)
REDIS_URL=redis://localhost:6380/1              # padrão do projeto
```

> O `EmbeddingGenerator` deve aceitar parâmetros explícitos no construtor (com defaults). Não depender de `Settings` globalmente — receber configurações via parâmetro/injeção para facilitar testes.

### Aprendizados das Stories 1.x (padrões a seguir)

- **Não usar `enem_rag_service`** como usuário de banco — usar `postgres:postgres123` em fixtures de teste
- **`scope="module"`** para fixtures de setup custoso (engine); **`scope="function"`** com rollback para fixtures de DB
- `db.flush()` após operações de banco dentro de transação de teste
- Módulos novos ficam em `src/enem_ingestion/` — nunca em outro pacote
- Tests unitários (sem infraestrutura externa) ficam em `tests/test_*.py` na raiz de `tests/`

---

## Estrutura de Testes

```python
# tests/test_embedding_generator.py

class TestTokenLimitError:
    def test_raises_for_chunk_exceeding_8192_tokens(self, generator): ...

class TestRedisCache:
    def test_cache_hit_skips_openai_call(self, generator, mocker): ...
    def test_cache_miss_calls_openai_and_stores_result(self, generator, mocker): ...

class TestBatching:
    def test_101_chunks_split_into_two_openai_calls(self, generator, mocker): ...
    def test_exactly_100_chunks_uses_single_call(self, generator, mocker): ...

class TestRetry:
    def test_rate_limit_retries_3_times_then_raises(self, generator, mocker): ...
    def test_rate_limit_succeeds_on_second_attempt(self, generator, mocker): ...
    def test_5xx_error_retried(self, generator, mocker): ...
    def test_4xx_not_retried(self, generator, mocker): ...

class TestTokenTracking:
    def test_tokens_used_accumulates_across_calls(self, generator, mocker): ...
    def test_cache_hits_dont_add_to_tokens_used(self, generator, mocker): ...
```

---

## Não faz parte desta story

- Leitura de questões do banco / integração com `pgvector_writer.py` → Story 2.2
- Pipeline orquestrador → Story 2.3
- Modificações em `chunk_builder.py` — **NÃO modificar**
- Endpoints de API — Story 3.x e 4.x
- OCR ou extração de imagens — já implementado, não tocar

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6)

### Debug Log References

Sem bloqueios. `openai` e `redis` não estavam no venv — instalados via pip antes dos testes.

### Completion Notes List

- Adicionado `openai>=1.0.0` e `redis>=4.6.0` ao `requirements.txt`
- Criado `src/enem_ingestion/embedding_generator.py` com `TokenLimitError`, `EmbeddingResult`, `EmbeddingGenerator`
- Cache Redis: chave `emb:{content_hash}`, TTL 604800s, serialização JSON
- Retry exponencial: delays 1s → 2s → 4s em `RateLimitError` e `APIStatusError 5xx`; 4xx não retried
- `tokens_used` acumulado como `int` privado exposto via `@property`
- Criado `tests/test_embedding_generator.py` com 17 testes; Redis e OpenAI 100% mockados
- 183 testes existentes passam, 0 regressões

### File List

- `src/enem_ingestion/embedding_generator.py` (NOVO)
- `tests/test_embedding_generator.py` (NOVO)
- `requirements.txt` (MODIFICADO — adicionado openai, redis)

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Criado `embedding_generator.py` com cache Redis e retry exponencial; 17 testes unitários (Story 2.1) |
