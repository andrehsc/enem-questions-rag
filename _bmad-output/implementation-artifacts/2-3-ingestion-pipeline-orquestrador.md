# Story 2.3: Ingestion Pipeline — Orquestrador

**Status:** review
**Epic:** 2 — Pipeline de Embeddings: Geração e Ingestão
**Story ID:** 2.3
**Story Key:** `2-3-ingestion-pipeline-orquestrador`
**Criado:** 2026-04-02

---

## Story

Como desenvolvedor,
Quero um módulo `ingestion_pipeline.py` que orquestre todo o fluxo de ingestão,
Para que um único comando processe questões pendentes até embeddings no pgvector.

---

## Acceptance Criteria

1. Processa questões com `embedding_status = 'pending'` do banco (idempotência)
2. Executa sequencialmente: leitura do DB → chunk_builder → embedding_generator → pgvector_writer
3. Pula questões com `embedding_status = 'done'` sem gerar erros
4. Gera relatório ao final: total_processed, new_embedded, skipped, errors, tokens_used, estimated_cost_usd
5. Pode ser executado via CLI: `python -m src.enem_ingestion.ingestion_pipeline --limit 100`

---

## Tasks / Subtasks

- [x] **Task 1: Criar `src/enem_ingestion/ingestion_pipeline.py`** (AC: 1–5)
  - [x] 1.1 Definir dataclass `IngestionReport` com: total_processed, new_embedded, skipped, errors, tokens_used, estimated_cost_usd
  - [x] 1.2 Implementar `IngestionPipeline.__init__(database_url, openai_api_key, redis_url)` — instancia generator e writer
  - [x] 1.3 Implementar `_load_pending_questions(limit)` — query SELECT com `embedding_status = 'pending'`
  - [x] 1.4 Implementar `_load_alternatives(question_ids)` — query para question_alternatives em batch
  - [x] 1.5 Implementar `run(limit=None)` → `IngestionReport` — orquestra o pipeline completo
  - [x] 1.6 Adicionar bloco `if __name__ == "__main__"` com argparse para `--limit`

- [x] **Task 2: Criar `tests/test_ingestion_pipeline.py`** (AC: 1–5, unit tests com mocks)
  - [x] 2.1 Testar que questões `embedding_status='done'` são puladas e contadas em `skipped`
  - [x] 2.2 Testar que o relatório contabiliza new_embedded corretamente
  - [x] 2.3 Testar que tokens_used e estimated_cost_usd são calculados
  - [x] 2.4 Testar que error em embedding_generator é capturado e conta em `errors`
  - [x] 2.5 Testar que `limit` é respeitado na query de pending questions

---

## Dev Notes

### Arquivo a criar

```
src/enem_ingestion/ingestion_pipeline.py   ← NOVO
tests/test_ingestion_pipeline.py           ← NOVO
```

**NÃO modificar:** nenhum módulo existente.

### Imports disponíveis (todos já implementados)

```python
from src.enem_ingestion.chunk_builder import build_chunks_from_db_row, ChunkData
from src.enem_ingestion.embedding_generator import EmbeddingGenerator, TokenLimitError
from src.enem_ingestion.pgvector_writer import PgvectorWriter
```

### API pública do módulo

```python
# src/enem_ingestion/ingestion_pipeline.py

import argparse
import os
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.enem_ingestion.chunk_builder import build_chunks_from_db_row
from src.enem_ingestion.embedding_generator import EmbeddingGenerator, TokenLimitError
from src.enem_ingestion.pgvector_writer import PgvectorWriter


# Custo aproximado: text-embedding-3-small = $0.02 por 1M tokens
COST_PER_TOKEN = 0.02 / 1_000_000


@dataclass
class IngestionReport:
    total_processed: int = 0
    new_embedded: int = 0
    skipped: int = 0     # embedding_status já era 'done'
    errors: int = 0
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0


class IngestionPipeline:
    """
    Orquestra o pipeline completo de geração de embeddings.

    Processa questões com embedding_status='pending' do banco,
    gera embeddings via OpenAI e persiste no pgvector.

    Uso:
        pipeline = IngestionPipeline(
            database_url=os.environ["DATABASE_URL"],
            openai_api_key=os.environ["OPENAI_API_KEY"],
        )
        report = pipeline.run(limit=500)
        print(f"Novos embeddings: {report.new_embedded}")
    """

    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6380/1",
    ) -> None: ...

    def run(self, limit: Optional[int] = None) -> IngestionReport: ...
```

### Query de questões pendentes

```python
SELECT_PENDING_SQL = text("""
    SELECT
        q.id,
        q.question_text,
        q.context_text,
        q.subject,
        q.question_number,
        q.has_images,
        em.year
    FROM enem_questions.questions q
    LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
    WHERE q.embedding_status = 'pending'
      AND q.question_text IS NOT NULL
      AND q.question_text <> ''
    ORDER BY q.id
    {limit_clause}
""")
# Com limit: "LIMIT :limit"
```

### Query de alternativas em batch

```python
SELECT_ALTS_SQL = text("""
    SELECT question_id, alternative_letter, alternative_text
    FROM enem_questions.question_alternatives
    WHERE question_id = ANY(CAST(:ids AS uuid[]))
    ORDER BY question_id, alternative_order, alternative_letter
""")
```

### Lógica do run()

```python
def run(self, limit: Optional[int] = None) -> IngestionReport:
    report = IngestionReport()

    # 1. Carregar questões pendentes
    questions = self._load_pending_questions(limit)
    report.total_processed = len(questions)

    if not questions:
        return report

    # 2. Carregar alternativas em batch
    question_ids = [str(q["id"]) for q in questions]
    alts_by_qid = self._load_alternatives(question_ids)

    # 3. Construir chunks
    all_chunks = []
    chunks_by_qid = {}
    for q in questions:
        q["alternatives"] = alts_by_qid.get(str(q["id"]), [])
        try:
            chunks = build_chunks_from_db_row(q)
            all_chunks.extend(chunks)
            chunks_by_qid[str(q["id"])] = chunks
        except Exception as exc:
            logger.error("Erro ao construir chunks para %s: %s", q["id"], exc)
            report.errors += 1

    # 4. Gerar embeddings (com TokenLimitError por chunk)
    try:
        results = self._generator.generate_embeddings(all_chunks)
        report.tokens_used = self._generator.tokens_used
        report.estimated_cost_usd = report.tokens_used * COST_PER_TOKEN
    except TokenLimitError as exc:
        logger.error("TokenLimitError no batch: %s", exc)
        report.errors += len(questions)
        return report

    # 5. Escrever no pgvector
    write_results = self._writer.write_batch(all_chunks, results)
    report.new_embedded = sum(1 for r in write_results if r.success)
    report.errors += sum(1 for r in write_results if not r.success)

    return report
```

> **SIMPLIFICAÇÃO ACEITÁVEL:** O AC menciona "pular questões com embedding_status='done'". Isso é garantido pela query (`WHERE embedding_status = 'pending'`). Questões 'done' simplesmente não entram na query — não precisam de lógica explícita adicional de skip durante o loop.

### CLI (bloco __main__)

```python
if __name__ == "__main__":
    import argparse
    import logging
    logging.basicConfig(level="INFO")

    parser = argparse.ArgumentParser(description="ENEM Ingestion Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de questões a processar")
    args = parser.parse_args()

    pipeline = IngestionPipeline(
        database_url=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"),
        openai_api_key=os.environ["OPENAI_API_KEY"],
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6380/1"),
    )
    report = pipeline.run(limit=args.limit)

    print(f"=== Relatório de Ingestão ===")
    print(f"  Total processado:  {report.total_processed}")
    print(f"  Novos embeddings:  {report.new_embedded}")
    print(f"  Pulados (done):    {report.skipped}")
    print(f"  Erros:             {report.errors}")
    print(f"  Tokens usados:     {report.tokens_used:,}")
    print(f"  Custo estimado:    ${report.estimated_cost_usd:.4f}")
```

### Dependências já disponíveis

- `sqlalchemy>=2.0.0` — ja em requirements.txt ✅
- `openai>=1.0.0` — adicionado na Story 2.1 ✅
- `redis>=4.6.0` — adicionado na Story 2.1 ✅
- `EmbeddingGenerator` — importar de `src.enem_ingestion.embedding_generator` ✅
- `PgvectorWriter` — importar de `src.enem_ingestion.pgvector_writer` ✅
- `build_chunks_from_db_row` — importar de `src.enem_ingestion.chunk_builder` ✅

### Aprendizados das Stories anteriores

- `CAST(:ids AS uuid[])` para listas de UUIDs no PostgreSQL (Story 2.2)
- Schema qualificado: `enem_questions.questions` (Story 1.1)
- User `postgres:postgres123@localhost:5433/teachershub_enem` nos testes (Story 1.3)
- 100% mocks para unit tests — sem banco real, sem OpenAI real, sem Redis real

---

## Estrutura de Testes

```python
# tests/test_ingestion_pipeline.py

class TestIngestionReport:
    def test_skipped_count_from_empty_pending(self, pipeline, mocker): ...

class TestRun:
    def test_run_processes_pending_questions(self, pipeline, mocker): ...
    def test_run_respects_limit_parameter(self, pipeline, mocker): ...
    def test_run_counts_errors_from_write_failures(self, pipeline, mocker): ...
    def test_run_calculates_tokens_and_cost(self, pipeline, mocker): ...
    def test_run_empty_pending_returns_zero_report(self, pipeline, mocker): ...
    def test_token_limit_error_increments_errors(self, pipeline, mocker): ...
```

---

## Não faz parte desta story

- Parser de PDF e persistência de questões → existente em `src/enem_ingestion/`
- Endpoints REST → Epics 3 e 4
- Modificações em módulos já implementados — **NÃO modificar**
- Geração batch via PDFs diretamente (aceita questões já persistidas no banco)

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6)

### Debug Log References

Sem bloqueios. Padrão `CAST(:ids AS uuid[])` aplicado para lista de UUIDs. Query dividida em duas variantes (com/sem LIMIT) para evitar interpolação condicional.

### Completion Notes List

- Criado `src/enem_ingestion/ingestion_pipeline.py` com `IngestionReport`, `IngestionPipeline`
- `_load_pending_questions(limit)`: usa query-no-limit ou query-with-limit dependendo do argumento
- `_load_alternatives(question_ids)`: batch SELECT com `ANY(CAST(:ids AS uuid[]))`, agrupa por question_id
- `run(limit)`: orquestra load → chunk_builder → embedding_generator → pgvector_writer; captura `TokenLimitError` com early return
- Custo calculado: `tokens_used * COST_PER_TOKEN` (text-embedding-3-small = $0.02/1M tokens)
- CLI via argparse: `python -m src.enem_ingestion.ingestion_pipeline --limit 100`
- Criado `tests/test_ingestion_pipeline.py` com 14 testes; engine, EmbeddingGenerator e PgvectorWriter totalmente mockados
- 141 testes existentes passam, 0 regressões

### File List

- `src/enem_ingestion/ingestion_pipeline.py` (NOVO)
- `tests/test_ingestion_pipeline.py` (NOVO)

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Criado `ingestion_pipeline.py` com orquestrador completo, IngestionReport e CLI; 14 testes unitários (Story 2.3) |
