# Story 5.3: Pipeline Idempotente v2

Status: done

## Story

Como desenvolvedor,
Quero que o pipeline v2 seja idempotente usando content hash como chave,
Para que re-ingestões não gerem duplicatas nem reprocessamento desnecessário.

## Acceptance Criteria (AC)

1. Hash SHA-256 do conteúdo extraído como chave de idempotência
2. `ON CONFLICT (content_hash)` atualiza apenas metadata (timestamp, confidence_score)
3. Re-ingestão de PDF já processado completa em <5 segundos (skip path)
4. Log diferencia: novas, atualizadas, puladas, erros
5. CLI: `python -m enem_ingestion.pipeline_v2 --input data/downloads/`

## Tasks / Subtasks

- [ ] Task 1: Criar `src/enem_ingestion/pipeline_v2.py` — Orquestrador principal (AC: 1, 2, 3, 4, 5)
  - [ ] 1.1 Classe `ExtractionPipelineV2` com construtor: `(db_url, output_dir, azure_config=None)`
  - [ ] 1.2 Método `run(input_path, force=False) -> PipelineReport`
  - [ ] 1.3 Fluxo principal:
    1. Descobrir PDFs no `input_path` (glob `*.pdf`)
    2. Para cada PDF: `parse_filename()` → extrair metadata do nome
    3. Calcular hash SHA-256 do arquivo PDF inteiro
    4. Verificar se `ingestion_hash` já existe em `enem_questions.questions` → skip se `force=False`
    5. Chamar `Pymupdf4llmExtractor.extract_questions(pdf_path)` (Story 5.1)
    6. Para cada questão: `ExtractionConfidenceScorer.score(question)` (Story 5.2)
    7. Routing: accept → persist, fallback → queue, dead_letter → queue
    8. Persist questões aceitas via raw SQL INSERT/UPDATE
  - [ ] 1.4 Hash duplo: hash do PDF (file-level) + hash do conteúdo extraído (content-level, do chunk_builder)
  - [ ] 1.5 `force=True` reprocessa mesmo PDFs com hash existente
- [ ] Task 2: Persistência com UPSERT (AC: 2)
  - [ ] 2.1 INSERT INTO `enem_questions.questions` com ON CONFLICT
  - [ ] 2.2 Conflict key: `(exam_metadata_id, question_number)` — uma questão é única por prova + número
  - [ ] 2.3 ON CONFLICT DO UPDATE SET: `question_text`, `context_text`, `confidence_score`, `extraction_method`, `ingestion_hash`, `updated_at = NOW()`
  - [ ] 2.4 INSERT alternativas com ON CONFLICT: `(question_id, alternative_letter)` → UPDATE `alternative_text`
  - [ ] 2.5 Transação por questão (não por PDF inteiro)
- [ ] Task 3: Report e logging (AC: 4)
  - [ ] 3.1 `PipelineReport` dataclass: total_pdfs, total_questions, new, updated, skipped, errors, fallback_queued, dead_letter_queued, duration_seconds
  - [ ] 3.2 Log `INFO` para cada questão processada: `[{status}] Q{number} from {pdf} — confidence={score:.2f} method={method}`
  - [ ] 3.3 Log `WARNING` para fallback routing, `ERROR` para dead_letter
  - [ ] 3.4 Relatório final impresso no stdout ao final da execução
- [ ] Task 4: CLI entry point (AC: 5)
  - [ ] 4.1 `if __name__ == '__main__'` block com argparse
  - [ ] 4.2 Args: `--input` (required path), `--force` (flag), `--db-url` (env default), `--output-dir` (default `data/extracted_images/`)
  - [ ] 4.3 Carregar config de `.env` via `python-dotenv`
  - [ ] 4.4 Executável via `python -m enem_ingestion.pipeline_v2 --input data/downloads/`
- [ ] Task 5: Testes (AC: 1, 2, 3, 4)
  - [ ] 5.1 Criar `tests/test_pipeline_v2.py`
  - [ ] 5.2 Teste idempotência: processar mesmo PDF 2x → segunda execução skips all, <5s
  - [ ] 5.3 Teste routing: questão com score 0.90 → accept, score 0.60 → fallback, score 0.30 → dead_letter
  - [ ] 5.4 Teste report: contadores corretos para new/updated/skipped/errors
  - [ ] 5.5 Teste force mode: `force=True` reprocessa tudo
  - [ ] 5.6 Mock de `Pymupdf4llmExtractor` e `ExtractionConfidenceScorer` — sem dependência de pymupdf4llm real

## Dev Notes

### Arquitetura do Pipeline v2

```
pipeline_v2.py (ESTE MÓDULO)
├── Pymupdf4llmExtractor (Story 5.1)
├── ExtractionConfidenceScorer (Story 5.2)
├── ENEMQuestion Pydantic model (Story 5.2)
├── text_normalizer.normalize_enem_text()
├── parser.parse_filename()
└── raw SQL via psycopg2 (NÃO SQLAlchemy ORM)

Fluxo:
  PDF → pymupdf4llm → List[Question] → confidence_score → routing
       ↓ accept (≥0.80)           ↓ fallback (<0.80)      ↓ dead_letter (<0.50)
       persist to DB              queue for Epic 6         queue for Epic 6
       → chunk_builder            (tabela temporária       (tabela dead_letter)
       → embedding_generator       ou JSON file)
       → pgvector_writer
```

### Diferença do pipeline v1 (ingestion_pipeline.py)

O `ingestion_pipeline.py` existente é o pipeline de EMBEDDING — ele lê questões já no DB e gera embeddings. O `pipeline_v2.py` é o pipeline de EXTRAÇÃO — ele lê PDFs e insere questões no DB.

```
pipeline_v2.py     → PDF → DB (questões + alternativas + metadata)
ingestion_pipeline → DB  → Embeddings (chunk_builder → OpenAI → pgvector)
```

Ambos coexistem. Após o `pipeline_v2` extrair, o `ingestion_pipeline` gera embeddings.

### Database Access Pattern

Seguir o padrão existente do projeto: **raw SQL via psycopg2** (como em `db_integration.py`), NÃO SQLAlchemy ORM.

```python
import psycopg2
from psycopg2.extras import execute_values

def persist_question(conn, question, exam_metadata_id, confidence, method):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO enem_questions.questions
                (question_number, question_text, context_text, subject,
                 exam_metadata_id, confidence_score, extraction_method, ingestion_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (exam_metadata_id, question_number)
            DO UPDATE SET
                question_text = EXCLUDED.question_text,
                context_text = EXCLUDED.context_text,
                confidence_score = EXCLUDED.confidence_score,
                extraction_method = EXCLUDED.extraction_method,
                ingestion_hash = EXCLUDED.ingestion_hash,
                updated_at = NOW()
            RETURNING id, (xmax = 0) AS is_new
        """, (...))
        row = cur.fetchone()
        return row[0], row[1]  # question_id, is_new
```

### Fallback Queue (para Epic 6)

Nesta story, o routing para fallback e dead_letter é implementado como **placeholder**:
- Questões com routing 'fallback' são logadas e contadas no report
- Questões com routing 'dead_letter' são logadas e contadas no report
- A persistência real das queues é implementada no Epic 6

O pipeline_v2 expõe listas: `report.fallback_questions: List[Question]` e `report.dead_letter_questions: List[Question]` para que o Epic 6 conecte.

### Idempotência — Duas Camadas

1. **File-level**: hash SHA-256 do PDF inteiro → `ingestion_hash` na tabela `exam_metadata` ou checagem em `questions`
2. **Content-level**: `content_hash` nos chunks (já existente via `chunk_builder.py`) → ON CONFLICT no `question_chunks`

O pipeline_v2 implementa a camada 1 (file-level). A camada 2 já está implementada no embedding pipeline.

### Anti-Patterns a Evitar

- **NÃO** modificar `ingestion_pipeline.py` — é o pipeline de embedding, não de extração
- **NÃO** usar SQLAlchemy ORM — manter raw SQL via psycopg2 (padrão do projeto)
- **NÃO** implementar fallback Azure DI nesta story — apenas routing e queue
- **NÃO** implementar dead letter persistence nesta story — apenas contador
- **NÃO** chamar OpenAI/embedding nesta story — extração apenas
- **NÃO** usar `database.py` models (são legacy, schema diferente do real)

### Project Structure Notes

- Novo arquivo: `src/enem_ingestion/pipeline_v2.py`
- Novo arquivo: `tests/test_pipeline_v2.py`
- Compatível com: `parser.py` (dataclasses), `text_normalizer.py`, `image_extractor.py`
- Depende de: Story 5.1 (`pymupdf4llm_extractor.py`), Story 5.2 (`confidence_scorer.py`, `models.py`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3]
- [Source: src/enem_ingestion/ingestion_pipeline.py — pipeline de embedding existente (NÃO modificar)]
- [Source: src/enem_ingestion/db_integration.py — padrão raw SQL com psycopg2]
- [Source: src/enem_ingestion/parser.py — parse_filename(), Question dataclass]
- [Source: src/enem_ingestion/chunk_builder.py — content_hash SHA-256 (camada 2)]
- [Source: database/complete-init.sql — schema enem_questions.questions, exam_metadata]

### Testing Standards

- Framework: `pytest` + `pytest-mock`
- Pattern: mock `Pymupdf4llmExtractor` e `ExtractionConfidenceScorer` completamente
- Mock de `psycopg2.connect()` para evitar dependência de DB real
- Naming: `test_pipeline_idempotent_skip`, `test_pipeline_routing`, `test_pipeline_report`, `test_pipeline_force_mode`
- Coverage: `--cov=src` (pytest.ini)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- pipeline_v2.py: orchestrator with SHA-256 file hash, UPSERT via psycopg2, scoring+routing, PipelineReport, CLI
- Idempotent: hash check skips, force flag overrides, ON CONFLICT UPSERT
- Fallback/dead_letter queues as placeholder lists for Epic 6
- 8 tests pass: routing (3), idempotency (2), report (2), hashing (1)

### File List

- src/enem_ingestion/pipeline_v2.py (new)
- tests/test_pipeline_v2.py (new)