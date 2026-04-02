# Story 1.3: Testes de Integração do Schema

**Status:** review
**Epic:** 1 — Fundação Vetorial: pgvector + Chunk Builder
**Story ID:** 1.3
**Story Key:** `1-3-testes-de-integracao-do-schema`
**Criado:** 2026-04-02

---

## Story

Como desenvolvedor,
Quero testes de integração que validem o fluxo completo entre `chunk_builder.py` e o schema pgvector com dados reais,
Para garantir que a construção de chunks e sua persistência no banco funcionam corretamente de ponta a ponta.

---

## Contexto Crítico — Leia Antes de Implementar

### ⚠️ ACs da Epic já cobertos pela Story 1.1

Os 4 critérios de aceite originais da epics.md para esta story **já foram implementados** em `tests/test_pgvector_schema.py` como parte da Story 1.1:

| AC original | Teste existente em `test_pgvector_schema.py` |
|---|---|
| Insere chunk com embedding mock e valida recuperação por `question_id` | `TestChunkCRUD.test_insert_chunk_with_mock_embedding` |
| Valida constraint UNIQUE em `content_hash` | `TestChunkCRUD.test_content_hash_unique_constraint` |
| Valida índice HNSW com busca de similaridade básica | `TestHNSWSimilaritySearch.test_hnsw_similarity_search_ordering` |
| Valida cascade delete | `TestCascadeDelete.test_cascade_delete_chunks` |

**NÃO duplicar esses testes.** Esta story foca na camada de integração que a Story 1.1 não cobre: o fluxo **`chunk_builder.py` → banco de dados real**, usando dados reais do banco.

### Objetivo real desta story

Criar `tests/test_chunk_builder_integration.py` com testes de integração que:
1. Leem questões reais do banco via SQL
2. Chamam `build_chunks_from_db_row()` com esses dados
3. Inserem os `ChunkData` resultantes na tabela `question_chunks`
4. Verificam que os dados persistidos correspondem ao que o `chunk_builder.py` produziu

---

## Acceptance Criteria

1. `test_build_chunks_from_real_db_question`: lê questão real do banco, chama `build_chunks_from_db_row()`, verifica `question_id`, tipos de chunks e formato do `content_hash` (64 chars hex)
2. `test_chunk_content_hash_is_deterministic`: mesma questão → mesmos hashes em duas chamadas consecutivas
3. `test_insert_chunk_built_by_chunk_builder`: constrói chunk com `build_chunks_from_db_row()` → insere via SQL INSERT → lê de volta e valida `content`, `content_hash`, `token_count` e `chunk_type`
4. `test_idempotency_via_on_conflict`: inserir o mesmo chunk duas vezes via `ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW()` não lança erro e deixa apenas 1 linha
5. `test_build_chunks_with_dict_alternatives_from_db`: constrói dicionário no formato `[{"letter": "A", "text": "..."}]` a partir de dados de `question_alternatives`, chama `build_chunks_from_db_row()`, verifica que as letras corretas aparecem no conteúdo do chunk
6. `test_build_chunks_from_question_with_context_text` (opcional, skip se não houver questão com `context_text` no banco): questão com `context_text` → 2 chunks (`full` + `context`) inseridos com sucesso

---

## Tasks / Subtasks

- [x] **Task 1: Criar `tests/test_chunk_builder_integration.py`** (AC: 1–6)
  - [x] 1.1 Configurar guard de integração (`RUN_INTEGRATION_TESTS=true` ou `--integration`)
  - [x] 1.2 Copiar estrutura de fixtures de `tests/test_pgvector_schema.py` (engine scope=module, db com rollback, sample_question_id, sample_question_row)
  - [x] 1.3 Adicionar fixture `sample_question_row` — query com JOIN para obter todos os campos necessários para `build_chunks_from_db_row()`
  - [x] 1.4 Implementar `TestChunkBuilderWithRealData` (ACs 1, 2, 5, 6)
  - [x] 1.5 Implementar `TestChunkInsertRoundTrip` (ACs 3, 4)

---

## Dev Notes

### Arquivo a criar

```
tests/test_chunk_builder_integration.py   ← NOVO arquivo
tests/test_pgvector_schema.py             ← NÃO modificar
src/enem_ingestion/chunk_builder.py       ← NÃO modificar
```

### Como executar os testes

```bash
# Requer Docker rodando com o banco
# docker-compose up -d postgres

RUN_INTEGRATION_TESTS=true pytest tests/test_chunk_builder_integration.py -v

# Ou com a flag customizada:
pytest tests/test_chunk_builder_integration.py -v --integration
```

### Conexão com o banco

Usar exatamente o mesmo padrão de `tests/test_pgvector_schema.py`:

```python
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
)
```

**IMPORTANTE:** Não usar `enem_rag_service` — essa role não existe. Usar `postgres:postgres123`.

### Guard de integração

Copiar o padrão exato de `tests/test_pgvector_schema.py`:

```python
import os
import pytest

def is_integration_env():
    return (
        os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")
        or "--integration" in os.sys.argv
    )

pytestmark = pytest.mark.skipif(
    not is_integration_env(),
    reason="Testes de integração — set RUN_INTEGRATION_TESTS=true para executar"
)
```

### Fixtures necessárias

```python
@pytest.fixture(scope="module")
def engine():
    eng = create_engine(DATABASE_URL, echo=False)
    yield eng
    eng.dispose()

@pytest.fixture
def db(engine):
    """Sessão com rollback garantido após cada teste."""
    with Session(engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="module")
def sample_question_row(engine):
    """
    Retorna dict com todos os campos para build_chunks_from_db_row().
    
    Inclui alternatives como list[dict] via JOIN com question_alternatives.
    """
    with Session(engine) as session:
        # Buscar questão com pelo menos 1 alternativa
        row = session.execute(text("""
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
            WHERE q.question_text IS NOT NULL AND q.question_text <> ''
            LIMIT 1
        """)).fetchone()
        if row is None:
            pytest.skip("Banco sem questões. Execute o pipeline de ingestão first.")
        
        q_id = str(row.id)
        
        # Buscar alternativas para essa questão
        alt_rows = session.execute(text("""
            SELECT alternative_letter, alternative_text
            FROM enem_questions.question_alternatives
            WHERE question_id = :qid
            ORDER BY alternative_order, alternative_letter
        """), {"qid": q_id}).fetchall()
        
        alternatives = [
            {"letter": r.alternative_letter, "text": r.alternative_text}
            for r in alt_rows
        ]
        
        return {
            "id": q_id,
            "question_text": row.question_text,
            "context_text": row.context_text,
            "subject": row.subject,
            "question_number": row.question_number,
            "has_images": row.has_images or False,
            "year": row.year,
            "alternatives": alternatives,
        }
```

### API do `build_chunks_from_db_row()`

```python
from src.enem_ingestion.chunk_builder import build_chunks_from_db_row, ChunkData

# row_dict esperado:
row = {
    "id": "uuid-string",           # obrigatório — question_id dos chunks
    "question_text": "...",        # obrigatório
    "alternatives": [              # list[str] OU list[dict]
        {"letter": "A", "text": "..."},  # formato dict
        # OU: "A) texto..."              # formato string
    ],
    "context_text": "..." or None, # opcional
    "subject": "matematica",       # metadado
    "year": 2023,                  # metadado
    "question_number": 42,         # metadado
    "has_images": False,           # metadado
}

chunks: list[ChunkData] = build_chunks_from_db_row(row)
# chunks[0].chunk_type == "full"
# chunks[0].content_hash  — SHA-256 hex, 64 chars
# chunks[0].token_count   — > 0
# chunks[0].question_id   == row["id"]
```

### Como inserir um ChunkData no banco (SQL puro)

```python
from sqlalchemy import text

def insert_chunk(db, chunk: ChunkData) -> None:
    db.execute(
        text("""
            INSERT INTO enem_questions.question_chunks
                (question_id, chunk_type, content, content_hash, token_count)
            VALUES (:qid, :ctype, :content, :hash, :tokens)
        """),
        {
            "qid": chunk.question_id,
            "ctype": chunk.chunk_type,
            "content": chunk.content,
            "hash": chunk.content_hash,
            "tokens": chunk.token_count,
        }
    )
    db.flush()
```

### Como testar idempotência via ON CONFLICT

```python
# A mesma query com ON CONFLICT deve rodar 2x sem erro:
db.execute(
    text("""
        INSERT INTO enem_questions.question_chunks
            (question_id, chunk_type, content, content_hash, token_count)
        VALUES (:qid, :ctype, :content, :hash, :tokens)
        ON CONFLICT (content_hash) DO UPDATE
            SET updated_at = NOW()
    """),
    {
        "qid": chunk.question_id,
        "ctype": chunk.chunk_type,
        "content": chunk.content,
        "hash": chunk.content_hash,
        "tokens": chunk.token_count,
    }
)
db.flush()

# Verificar que há apenas 1 linha com esse hash
count = db.execute(
    text("SELECT COUNT(*) FROM enem_questions.question_chunks WHERE content_hash = :h"),
    {"h": chunk.content_hash}
).scalar()
assert count == 1
```

### Schema do banco — referência rápida

```
enem_questions.questions
  id                UUID PK
  question_text     TEXT
  context_text      TEXT (nullable)
  subject           VARCHAR
  question_number   INTEGER
  has_images        BOOLEAN
  exam_metadata_id  UUID FK → exam_metadata
  embedding_status  VARCHAR(20) DEFAULT 'pending'

enem_questions.exam_metadata
  id    UUID PK
  year  INTEGER

enem_questions.question_alternatives
  id                  UUID PK
  question_id         UUID FK → questions (ON DELETE CASCADE)
  alternative_letter  CHAR(1)  CHECK IN ('A','B','C','D','E')
  alternative_text    TEXT
  alternative_order   INTEGER

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

> **ATENÇÃO:** Sempre qualificar com schema: `enem_questions.question_chunks` (não apenas `question_chunks`).

### Aprendizados da Story 1.1 (padrões a seguir)

- Usar `CAST(:emb AS vector)` em vez de `:emb::vector` — SQLAlchemy interpreta `::` como parâmetro nomeado e quebra
- `db.flush()` após cada INSERT para forçar envio ao banco dentro da transação (o rollback do fixture desfaz ao final)
- Fixtures com `scope="module"` (engine, sample_question_id, sample_question_row) e `scope="function"` (db com rollback) — manter este padrão
- Pytest usa `IntegrityError` de `sqlalchemy.exc` para validar violações de constraint

### Aprendizados da Story 1.2 (comportamento do chunk_builder)

- `content_hash` é calculado **antes** do truncamento — representa o conteúdo original integral
- Alternativas dict `{"letter": "A", "text": "..."}` → `build_chunks_from_db_row()` preserva a letra do campo (não usa posição)
- `token_count` = `len(tiktoken.get_encoding("cl100k_base").encode(content))`
- `chunk.question_id` é sempre `str(row["id"])` (string UUID)

### Dependências

- Docker rodando: `docker-compose up -d postgres`
- Migration aplicada: `database/pgvector-migration.sql`
- Banco com ao menos 1 questão ingerida na tabela `enem_questions.questions`
- Python packages: `sqlalchemy`, `psycopg2-binary` (já no `requirements.txt`)

---

## Estrutura Tests

```python
# tests/test_chunk_builder_integration.py

class TestChunkBuilderWithRealData:
    """
    Build chunks a partir de dados reais do banco (sem inserção).
    Não modifica o banco (nenhum INSERT/UPDATE).
    """
    def test_build_chunks_from_real_db_question(self, sample_question_row): ...
    def test_chunk_content_hash_is_deterministic(self, sample_question_row): ...
    def test_build_chunks_with_dict_alternatives_from_db(self, sample_question_row): ...
    def test_build_chunks_from_question_with_context_text(self, engine): ...


class TestChunkInsertRoundTrip:
    """
    Insere chunks construídos pelo chunk_builder no banco (rollback garantido).
    """
    def test_insert_chunk_built_by_chunk_builder(self, db, sample_question_row): ...
    def test_idempotency_via_on_conflict(self, db, sample_question_row): ...
```

---

## Não faz parte desta story

- Modelos SQLAlchemy (ORM) para `question_chunks` → Story 2.2
- Geração de embeddings reais (OpenAI) → Story 2.1
- Lógica de pipeline de ingestão → Story 2.3
- Modificações em `chunk_builder.py` — **NÃO modificar**
- Modificações em `test_pgvector_schema.py` — **NÃO modificar**

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6)

### Debug Log References

Sem bloqueios. Implementação direta seguindo os padrões de `test_pgvector_schema.py`.

### Completion Notes List

- Criado `tests/test_chunk_builder_integration.py` com 6 testes em 2 classes
- Guard de integração idêntico ao de `test_pgvector_schema.py` — skip automático sem `RUN_INTEGRATION_TESTS=true`
- `TestChunkBuilderWithRealData`: testa build de chunks com dados reais SEM modificar banco (ACs 1, 2, 5, 6)
- `TestChunkInsertRoundTrip`: testa inserção e leitura de volta com rollback garantido (ACs 3, 4)
- Fixture `sample_question_row` usa JOIN com `exam_metadata` para obter `year` e com `question_alternatives` para obter alternativas no formato `list[dict]`
- AC 6 (context_text) implementado com `pytest.skip` quando não há questão com context_text no banco
- Helpers `_insert_chunk` e `_insert_chunk_idempotent` mantidos privados no módulo (uso único)
- 166 testes existentes passam, 0 regressões

### File List

- `tests/test_chunk_builder_integration.py` (NOVO)

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Criado `tests/test_chunk_builder_integration.py` com 6 testes de integração cobrindo ACs 1–6 (Story 1.3) |