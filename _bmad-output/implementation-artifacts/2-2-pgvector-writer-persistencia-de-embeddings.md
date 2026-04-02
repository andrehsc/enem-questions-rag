# Story 2.2: pgvector Writer — Persistência de Embeddings

**Status:** review
**Epic:** 2 — Pipeline de Embeddings: Geração e Ingestão
**Story ID:** 2.2
**Story Key:** `2-2-pgvector-writer-persistencia-de-embeddings`
**Criado:** 2026-04-02

---

## Story

Como desenvolvedor,
Quero um módulo `pgvector_writer.py` que persista embeddings na tabela `question_chunks`,
Para que os vetores fiquem disponíveis para busca semântica.

---

## Acceptance Criteria

1. Insere chunks com `ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW()`
2. Atualiza `embedding_status` na tabela `questions` para `'done'` após inserção bem-sucedida
3. Suporta inserção em batch (recebe lista de chunks + embeddings)
4. Registra erros por `question_id` sem interromper o batch inteiro (try/except individual)
5. Transação: falha em um chunk não reverte chunks já inseridos com sucesso no mesmo batch

---

## Tasks / Subtasks

- [x] **Task 1: Criar `src/enem_ingestion/pgvector_writer.py`** (AC: 1–5)
  - [x] 1.1 Definir dataclass `WriteResult` com campos: `question_id`, `chunk_hash`, `success`, `error`
  - [x] 1.2 Implementar `PgvectorWriter.__init__(database_url)` — cria engine SQLAlchemy
  - [x] 1.3 Implementar `write_chunks(chunks, embeddings)` → `List[WriteResult]` com try/except por chunk
  - [x] 1.4 Implementar `update_embedding_status(question_ids, status)` — UPDATE em batch via WHERE id = ANY(:ids)
  - [x] 1.5 Implementar `write_batch(chunks, embeddings)` — orquestra write_chunks + update_embedding_status

- [x] **Task 2: Criar `tests/test_pgvector_writer.py`** (AC: 1–5, unit tests com mocks)
  - [x] 2.1 Testar que INSERT usa ON CONFLICT na query SQL
  - [x] 2.2 Testar que `embedding_status` é atualizado para `'done'` após write_chunks bem-sucedido
  - [x] 2.3 Testar batch: 3 chunks → 3 INSERTs individuais
  - [x] 2.4 Testar que falha em 1 chunk não impede inserção dos outros (try/except por chunk)
  - [x] 2.5 Testar que `WriteResult.success=False` e `error` preenchido para chunk com erro
  - [x] 2.6 Testar `update_embedding_status` com lista de question_ids

---

## Dev Notes

### Arquivo a criar

```
src/enem_ingestion/pgvector_writer.py   ← NOVO
tests/test_pgvector_writer.py           ← NOVO
```

**NÃO modificar:** `chunk_builder.py`, `embedding_generator.py`, `config.py`, nenhum teste existente.

### API pública do módulo

```python
# src/enem_ingestion/pgvector_writer.py

from dataclasses import dataclass
from typing import List, Optional
from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingResult


@dataclass
class WriteResult:
    question_id: Optional[str]  # pode ser None se chunk.question_id for None
    chunk_hash: str              # content_hash do chunk
    success: bool
    error: Optional[str] = None  # mensagem de erro se success=False


class PgvectorWriter:
    def __init__(self, database_url: str) -> None:
        """Cria engine SQLAlchemy com a URL fornecida."""
        ...

    def write_chunks(
        self, chunks: List[ChunkData], embeddings: List[EmbeddingResult]
    ) -> List[WriteResult]:
        """
        Insere cada (chunk, embedding) individualmente com try/except.
        Usa ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW().
        Falha em um chunk NÃO interrompe os demais.
        """
        ...

    def update_embedding_status(
        self, question_ids: List[str], status: str = "done"
    ) -> None:
        """
        Atualiza embedding_status na tabela enem_questions.questions
        para todos os question_ids fornecidos.
        """
        ...

    def write_batch(
        self, chunks: List[ChunkData], embeddings: List[EmbeddingResult]
    ) -> List[WriteResult]:
        """
        Orquestra write_chunks + update_embedding_status.
        Atualiza status apenas dos question_ids que tiveram sucesso.
        """
        ...
```

### SQL de inserção (ON CONFLICT)

```python
INSERT_SQL = text("""
    INSERT INTO enem_questions.question_chunks
        (question_id, chunk_type, content, content_hash, embedding, token_count)
    VALUES (:qid, :ctype, :content, :hash, CAST(:emb AS vector), :tokens)
    ON CONFLICT (content_hash) DO UPDATE
        SET updated_at = NOW()
""")

# Parâmetros para cada chunk
params = {
    "qid": chunk.question_id,
    "ctype": chunk.chunk_type,
    "content": chunk.content,
    "hash": chunk.content_hash,
    "emb": "[" + ",".join(map(str, embedding.embedding)) + "]",
    "tokens": chunk.token_count,
}
```

> **IMPORTANTE:** Usar `CAST(:emb AS vector)` — nunca `::vector`. SQLAlchemy interpreta `::` como parâmetro nomeado e quebra (aprendizado da Story 1.1).

### Embedding como string para pgvector

```python
# Converter List[float] → string no formato pgvector "[0.1,0.2,...,0.3]"
emb_str = "[" + ",".join(map(str, embedding.embedding)) + "]"
```

### SQL de atualização de status

```python
UPDATE_STATUS_SQL = text("""
    UPDATE enem_questions.questions
    SET embedding_status = :status
    WHERE id = ANY(CAST(:ids AS uuid[]))
""")

# Parâmetros
params = {
    "status": status,     # ex: 'done'
    "ids": question_ids,  # List[str] de UUIDs
}
```

> Usar `CAST(:ids AS uuid[])` para passar lista de UUIDs via SQLAlchemy.

### Padrão de escrita individual com try/except

```python
def write_chunks(self, chunks, embeddings) -> List[WriteResult]:
    results = []
    # Indexar embeddings por content_hash para lookup O(1)
    emb_map = {e.content_hash: e for e in embeddings}

    for chunk in chunks:
        embedding = emb_map.get(chunk.content_hash)
        if embedding is None:
            results.append(WriteResult(
                question_id=chunk.question_id,
                chunk_hash=chunk.content_hash,
                success=False,
                error="Embedding não encontrado para este chunk",
            ))
            continue

        try:
            with Session(self._engine) as session:
                session.execute(INSERT_SQL, params)
                session.commit()
            results.append(WriteResult(
                question_id=chunk.question_id,
                chunk_hash=chunk.content_hash,
                success=True,
            ))
        except Exception as exc:
            logger.error(
                "Erro ao inserir chunk question_id=%s hash=%s: %s",
                chunk.question_id,
                chunk.content_hash[:12],
                exc,
            )
            results.append(WriteResult(
                question_id=chunk.question_id,
                chunk_hash=chunk.content_hash,
                success=False,
                error=str(exc),
            ))

    return results
```

### Como mockar nas unit tests

```python
import pytest
from unittest.mock import MagicMock, patch, call
from src.enem_ingestion.pgvector_writer import PgvectorWriter, WriteResult
from src.enem_ingestion.chunk_builder import ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingResult

@pytest.fixture
def writer(mocker):
    mocker.patch("src.enem_ingestion.pgvector_writer.create_engine")
    return PgvectorWriter(database_url="postgresql://fake/db")

def make_chunk(content_hash="a" * 64, question_id="uuid-1") -> ChunkData:
    return ChunkData(
        chunk_type="full",
        content="texto",
        content_hash=content_hash,
        token_count=50,
        question_id=question_id,
    )

def make_embedding(content_hash="a" * 64) -> EmbeddingResult:
    return EmbeddingResult(
        content_hash=content_hash,
        embedding=[0.1] * 1536,
        tokens_used=20,
        from_cache=False,
    )
```

> Para testar que o SQL contém ON CONFLICT, verificar o texto da query passada ao `session.execute` via mock.

### Schema de referência (question_chunks)

```
enem_questions.question_chunks
  id              UUID PK DEFAULT gen_random_uuid()
  question_id     UUID FK → questions (ON DELETE CASCADE)
  chunk_type      VARCHAR(20) CHECK IN ('full','context')
  content         TEXT
  content_hash    VARCHAR(64) UNIQUE CONSTRAINT uk_question_chunks_hash
  embedding       vector(1536) NULL
  token_count     INTEGER
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
```

```
enem_questions.questions
  id               UUID PK
  embedding_status VARCHAR(20) CHECK IN ('pending','processing','done','error')
```

### Dependências já disponíveis

- `sqlalchemy>=2.0.0` — já em requirements.txt ✅
- `psycopg2-binary>=2.9.11` — já em requirements.txt ✅
- `ChunkData` — importar de `src.enem_ingestion.chunk_builder` ✅
- `EmbeddingResult` — importar de `src.enem_ingestion.embedding_generator` ✅

### Aprendizados das Stories anteriores

- `CAST(:emb AS vector)` não `::vector` — SQLAlchemy quebra com `::` (Story 1.1)
- `db.flush()` em testes de integração, mas em production usar `session.commit()` por chunk
- Schema qualificado sempre: `enem_questions.question_chunks` (não apenas `question_chunks`)
- User de banco em produção: ver DATABASE_URL env var; em testes mockar engine diretamente

---

## Estrutura de Testes

```python
# tests/test_pgvector_writer.py

class TestWriteChunks:
    def test_insert_uses_on_conflict_clause(self, writer, mocker): ...
    def test_batch_3_chunks_generates_3_inserts(self, writer, mocker): ...
    def test_chunk_error_does_not_stop_other_chunks(self, writer, mocker): ...
    def test_write_result_success_true_on_success(self, writer, mocker): ...
    def test_write_result_success_false_on_db_error(self, writer, mocker): ...
    def test_missing_embedding_returns_error_result(self, writer): ...

class TestUpdateEmbeddingStatus:
    def test_update_status_called_with_correct_ids(self, writer, mocker): ...
    def test_update_status_uses_correct_sql_pattern(self, writer, mocker): ...

class TestWriteBatch:
    def test_write_batch_orchestrates_write_and_status_update(self, writer, mocker): ...
    def test_write_batch_updates_only_successful_question_ids(self, writer, mocker): ...
```

---

## Não faz parte desta story

- Cache Redis (embedding_generator.py → Story 2.1, já implementado)
- Pipeline orquestrador → Story 2.3
- Busca semântica → Epic 3
- Modificações em `chunk_builder.py` ou `embedding_generator.py` — **NÃO modificar**

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6)

### Debug Log References

Sem bloqueios. Padrão `CAST(:emb AS vector)` aplicado conforme aprendizado da Story 1.1.

### Completion Notes List

- Criado `src/enem_ingestion/pgvector_writer.py` com `WriteResult`, `PgvectorWriter`
- `write_chunks`: inserção individual with try/except — falha em 1 não para os outros
- `update_embedding_status`: UPDATE em batch via `ANY(CAST(:ids AS uuid[]))`
- `write_batch`: orquestra write_chunks + update_status; só atualiza IDs com sucesso
- ON CONFLICT implementado: `ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW()`
- Criado `tests/test_pgvector_writer.py` com 13 testes; SQLAlchemy Session totalmente mockado
- 196 testes existentes passam, 0 regressões

### File List

- `src/enem_ingestion/pgvector_writer.py` (NOVO)
- `tests/test_pgvector_writer.py` (NOVO)

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Criado `pgvector_writer.py` com write_batch idempotente e update_embedding_status; 13 testes unitários (Story 2.2) |
