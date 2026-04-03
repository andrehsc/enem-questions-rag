# Story 6.2: Dead Letter Queue

Status: done

## Story

Como desenvolvedor,
Quero uma dead letter queue para questões com confidence < 0.50 após todas as tentativas de extração,
Para que questões irrecuperáveis automaticamente sejam encaminhadas para revisão manual.

## Acceptance Criteria (AC)

1. Tabela `dead_letter_questions` com: question_ref, raw_content, extraction_errors, confidence_score, created_at
2. Questões com confidence < 0.50 (ambas camadas) inseridas automaticamente
3. Inclui diagnóstico: qual camada falhou, razão da baixa confiança, raw text extraído
4. Endpoint GET `/api/v1/admin/dead-letter` para listar e gerenciar (paginated)
5. Endpoint PATCH `/api/v1/admin/dead-letter/{id}` para marcar como resolvida manualmente
6. Testes unitários cobrem: inserção, listagem, resolução, re-ingestão após correção

## Tasks / Subtasks

- [ ] Task 1: Migration SQL — tabela dead_letter_questions (AC: 1)
  - [ ] 1.1 Criar `database/dead-letter-migration.sql` com:
    ```sql
    CREATE TABLE IF NOT EXISTS enem_questions.dead_letter_questions (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        question_number INTEGER,
        pdf_filename VARCHAR(255) NOT NULL,
        page_numbers VARCHAR(50),
        raw_text TEXT NOT NULL,
        extraction_errors JSONB DEFAULT '[]',
        confidence_score FLOAT NOT NULL,
        extraction_method VARCHAR(30) NOT NULL,
        failed_layers TEXT[] NOT NULL DEFAULT '{}',
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        resolved_by VARCHAR(100),
        resolved_at TIMESTAMP WITH TIME ZONE,
        resolution_notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT chk_dl_status CHECK (status IN ('pending', 'resolved', 'reingested'))
    );
    ```
  - [ ] 1.2 Index: `idx_dl_status` em `status` para queries de admin
  - [ ] 1.3 Index: `idx_dl_created_at` em `created_at` para paginação
  - [ ] 1.4 Migration idempotente (`IF NOT EXISTS`)
- [ ] Task 2: Criar `src/enem_ingestion/dead_letter_queue.py` — Módulo de persistência (AC: 1, 2, 3)
  - [ ] 2.1 Classe `DeadLetterQueue` com construtor: `(conn)` (psycopg2 connection)
  - [ ] 2.2 Método `enqueue(question: Question, confidence: float, extraction_method: str, failed_layers: List[str], errors: List[str], pdf_filename: str) -> str`
    - INSERT na tabela `dead_letter_questions`
    - `raw_text` = concatenação de `question.text + alternatives`
    - `extraction_errors` = JSON das issues do `ConfidenceResult.issues`
    - Retorna o UUID do registro inserido
  - [ ] 2.3 Método `resolve(dl_id: str, resolved_by: str, notes: str = "") -> bool`
    - UPDATE SET `status='resolved', resolved_by, resolved_at=NOW(), resolution_notes`
    - Retorna True se encontrou e atualizou
  - [ ] 2.4 Método `list_pending(limit=20, offset=0) -> Tuple[List[dict], int]`
    - SELECT com paginação, retorna (items, total_count)
    - Usa `COUNT(*) OVER()` para total sem query extra
  - [ ] 2.5 Método `get_by_id(dl_id: str) -> Optional[dict]`
- [ ] Task 3: Integrar no pipeline_v2 (AC: 2, 3)
  - [ ] 3.1 No `_process_question()`, quando routing=='dead_letter':
    - Instanciar `DeadLetterQueue(conn)` e chamar `enqueue()`
    - `failed_layers = ['pymupdf4llm']`
  - [ ] 3.2 No fallback Azure DI (Story 6.1), quando re-score < ACCEPT_THRESHOLD:
    - Chamar `enqueue()` com `failed_layers=['pymupdf4llm', 'azure_di']`
  - [ ] 3.3 O `extraction_errors` JSONB deve incluir os `ConfidenceResult.issues`
- [ ] Task 4: Admin API endpoints (AC: 4, 5)
  - [ ] 4.1 Em `api/fastapi_app.py`, adicionar endpoints com tag "Admin":
  - [ ] 4.2 `GET /api/v1/admin/dead-letter`
    - Query params: `status` (optional, default 'pending'), `limit` (default 20, max 100), `offset` (default 0)
    - Response: `{"data": [...], "meta": {"total": N, "limit": L, "offset": O}}`
    - Usa `DeadLetterQueue.list_pending()`
  - [ ] 4.3 `PATCH /api/v1/admin/dead-letter/{id}`
    - Body: `{"resolved_by": "admin_username", "resolution_notes": "..."}`
    - Response: `{"data": {"id": ..., "status": "resolved"}, "meta": {}}`
    - Usa `DeadLetterQueue.resolve()`
  - [ ] 4.4 Pydantic request/response models para os endpoints:
    - `DeadLetterListResponse`, `DeadLetterResolveRequest`, `DeadLetterItem`
  - [ ] 4.5 Error handling: 404 se id não encontrado, 400 se body inválido
- [ ] Task 5: Testes (AC: 6)
  - [ ] 5.1 Criar `tests/test_dead_letter_queue.py`
  - [ ] 5.2 Teste: enqueue insere registro com campos corretos
  - [ ] 5.3 Teste: resolve atualiza status para 'resolved'
  - [ ] 5.4 Teste: list_pending retorna apenas status='pending'
  - [ ] 5.5 Teste: paginação funciona (limit, offset, total_count)
  - [ ] 5.6 Teste: pipeline_v2 integration — dead_letter routing chama enqueue
  - [ ] 5.7 Teste: API endpoint GET retorna JSON paginado
  - [ ] 5.8 Teste: API endpoint PATCH resolve e retorna 200
  - [ ] 5.9 Teste: API endpoint PATCH com id inexistente retorna 404
  - [ ] 5.10 Mock de psycopg2 para DeadLetterQueue — sem DB real

## Dev Notes

### Arquitetura da Dead Letter Queue

```
pipeline_v2.py
├── routing == 'dead_letter' → DeadLetterQueue.enqueue()
├── routing == 'fallback' → AzureDIFallback.process()
│   └── re-score < 0.80 → DeadLetterQueue.enqueue(failed_layers=['pymupdf4llm', 'azure_di'])
│
dead_letter_queue.py (ESTE MÓDULO)
├── enqueue() → INSERT INTO enem_questions.dead_letter_questions
├── resolve() → UPDATE SET status='resolved'
├── list_pending() → SELECT ... LIMIT/OFFSET
└── get_by_id() → SELECT ... WHERE id=

api/fastapi_app.py
├── GET /api/v1/admin/dead-letter → list_pending()
└── PATCH /api/v1/admin/dead-letter/{id} → resolve()
```

### Database Access Pattern

Seguir raw SQL via psycopg2 (padrão do projeto):

```python
def enqueue(self, question, confidence, method, failed_layers, errors, pdf_filename):
    with self._conn.cursor() as cur:
        cur.execute("""
            INSERT INTO enem_questions.dead_letter_questions
                (question_number, pdf_filename, raw_text, extraction_errors,
                 confidence_score, extraction_method, failed_layers)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
            RETURNING id
        """, (
            question.number,
            pdf_filename,
            question.text + "\n" + "\n".join(question.alternatives),
            json.dumps(errors),
            confidence,
            method,
            failed_layers,
        ))
        self._conn.commit()
        return str(cur.fetchone()[0])
```

### API Pattern (seguir padrão existente)

O `fastapi_app.py` usa Pydantic models inline. Seguir este padrão:

```python
class DeadLetterItem(BaseModel):
    id: str
    question_number: Optional[int]
    pdf_filename: str
    raw_text: str
    extraction_errors: list
    confidence_score: float
    extraction_method: str
    failed_layers: list
    status: str
    created_at: str

class DeadLetterResolveRequest(BaseModel):
    resolved_by: str
    resolution_notes: str = ""

@app.get("/api/v1/admin/dead-letter", tags=["Admin"])
async def list_dead_letter(status: str = "pending", limit: int = 20, offset: int = 0):
    ...

@app.patch("/api/v1/admin/dead-letter/{dl_id}", tags=["Admin"])
async def resolve_dead_letter(dl_id: str, body: DeadLetterResolveRequest):
    ...
```

**Nota:** Não há autenticação nos endpoints atuais. Os admin endpoints seguem o mesmo padrão (sem auth). Auth é escopo futuro.

### Anti-Patterns a Evitar

- **NÃO** usar SQLAlchemy ORM — manter raw SQL via psycopg2
- **NÃO** criar um novo FastAPI app — adicionar endpoints ao `api/fastapi_app.py` existente
- **NÃO** implementar autenticação — é escopo futuro
- **NÃO** modificar `confidence_scorer.py` — apenas consumir os resultados
- **NÃO** fazer re-ingestão automática quando resolver dead letter — é ação manual
- **NÃO** depender de banco real nos testes — mock psycopg2

### Dependência de Ordem

Story 6.2 depende de Story 6.1 para:
- O flow de fallback Azure DI que pode encaminhar para dead_letter com `failed_layers=['pymupdf4llm', 'azure_di']`
- Porém, a dead_letter queue funciona independentemente (questões com score < 0.50 direto do pymupdf4llm)

Se implementando 6.1 e 6.2 na mesma sessão: implementar 6.1 primeiro, depois 6.2 integra com ambos.

### Project Structure Notes

- Novo arquivo: `src/enem_ingestion/dead_letter_queue.py`
- Novo arquivo: `database/dead-letter-migration.sql`
- Novo arquivo: `tests/test_dead_letter_queue.py`
- Modificar: `src/enem_ingestion/pipeline_v2.py` (integrar enqueue no routing)
- Modificar: `api/fastapi_app.py` (admin endpoints)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2]
- [Source: src/enem_ingestion/pipeline_v2.py — dead_letter routing placeholder]
- [Source: src/enem_ingestion/confidence_scorer.py — FALLBACK_THRESHOLD=0.50, ConfidenceResult]
- [Source: database/complete-init.sql — schema enem_questions]
- [Source: api/fastapi_app.py — endpoint patterns, Pydantic models, error handling]
- [Source: src/enem_ingestion/db_integration.py — raw SQL psycopg2 pattern]

### Testing Standards

- Framework: `pytest` + `pytest-mock`
- Pattern: mock `psycopg2.connect()` e cursor — NÃO depender de DB real
- Para API: usar `TestClient(app)` do FastAPI com DB mockado
- Naming: `test_enqueue_dead_letter`, `test_resolve_dead_letter`, `test_list_pending`, `test_api_get_dead_letter`
- Coverage: `--cov=src` (pytest.ini)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- dead_letter_queue.py: DeadLetterQueue class with enqueue, resolve, list_pending, get_by_id
- dead-letter-migration.sql: idempotent CREATE TABLE with status CHECK constraint, indexes
- pipeline_v2.py: _run_dead_letter integrates DLQ after all PDFs processed, tracks failed_layers
- fastapi_app.py: GET/PATCH /api/v1/admin/dead-letter endpoints with pagination and resolve
- 11 tests pass: enqueue (3), resolve (2), list_pending (3), get_by_id (2), pipeline integration (1)

### File List

- src/enem_ingestion/dead_letter_queue.py (new)
- database/dead-letter-migration.sql (new)
- tests/test_dead_letter_queue.py (new)
- src/enem_ingestion/pipeline_v2.py (modified — dead letter integration)
- api/fastapi_app.py (modified — admin endpoints)
