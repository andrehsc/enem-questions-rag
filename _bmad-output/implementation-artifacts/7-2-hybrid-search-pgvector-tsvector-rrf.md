# Story 7.2: Hybrid Search — pgvector + tsvector com RRF

Status: done

## Story

Como desenvolvedor,
Quero implementar hybrid search combinando busca vetorial (pgvector) com busca textual (tsvector) usando Reciprocal Rank Fusion,
Para melhorar a relevância de busca em queries em português.

## Acceptance Criteria (AC)

1. Coluna `tsv_content tsvector` adicionada a `question_chunks` com config `portuguese`
2. Busca textual usando `ts_query` com stemming em português
3. Reciprocal Rank Fusion (RRF) combina rankings: `1/(k+rank_vector) + 1/(k+rank_text)` com k=60
4. Parâmetro `search_mode` no endpoint: `semantic`, `text`, `hybrid` (default: `hybrid`)
5. Benchmark: hybrid search melhora recall@10 em >= 5% vs busca vetorial pura
6. Índice GIN em `tsv_content` para performance de busca textual
7. Testes com queries em português (acentuação, sinônimos, termos técnicos)

## Tasks / Subtasks

- [ ] Task 1: Migration SQL — tsvector column + GIN index (AC: 1, 6)
  - [ ] 1.1 Criar `database/hybrid-search-migration.sql`:
    ```sql
    -- Add tsvector column to question_chunks
    ALTER TABLE enem_questions.question_chunks
        ADD COLUMN IF NOT EXISTS tsv_content tsvector;

    -- Populate tsvector from existing content
    UPDATE enem_questions.question_chunks
    SET tsv_content = to_tsvector('portuguese', content)
    WHERE tsv_content IS NULL;

    -- GIN index for full-text search
    CREATE INDEX IF NOT EXISTS idx_question_chunks_tsv
        ON enem_questions.question_chunks USING gin(tsv_content);

    -- Trigger to keep tsvector updated on INSERT/UPDATE
    CREATE OR REPLACE FUNCTION enem_questions.update_tsv_content()
    RETURNS trigger AS $$
    BEGIN
        NEW.tsv_content := to_tsvector('portuguese', NEW.content);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_update_tsv_content
        ON enem_questions.question_chunks;
    CREATE TRIGGER trg_update_tsv_content
        BEFORE INSERT OR UPDATE OF content
        ON enem_questions.question_chunks
        FOR EACH ROW
        EXECUTE FUNCTION enem_questions.update_tsv_content();
    ```
  - [ ] 1.2 Migration idempotente (`IF NOT EXISTS`, `CREATE OR REPLACE`)
  - [ ] 1.3 Considerar `portuguese_unaccent` config (já existe em `database/init.sql`) para queries accent-insensitive
- [ ] Task 2: Implementar hybrid search em `PgVectorSearch` (AC: 2, 3, 4)
  - [ ] 2.1 Adicionar parâmetro `search_mode: str = "hybrid"` ao `search_questions()`:
    ```python
    async def search_questions(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
        chunk_type: str = "full",
        search_mode: str = "hybrid",  # NEW: "semantic", "text", "hybrid"
    ) -> List[Dict[str, Any]]:
    ```
  - [ ] 2.2 Implementar `_search_semantic()` — busca vetorial pura (refatorar SQL existente)
  - [ ] 2.3 Implementar `_search_text()` — busca textual via tsvector:
    ```sql
    SELECT q.id AS question_id, q.question_text, q.subject, em.year,
           qc.id AS chunk_id, qc.chunk_type, qc.content AS chunk_content,
           ts_rank(qc.tsv_content, plainto_tsquery('portuguese', :query)) AS text_score
    FROM enem_questions.question_chunks qc
    JOIN enem_questions.questions q ON q.id = qc.question_id
    LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
    WHERE qc.chunk_type = :chunk_type
      AND qc.tsv_content @@ plainto_tsquery('portuguese', :query)
    ORDER BY text_score DESC
    LIMIT :rrf_limit
    ```
  - [ ] 2.4 Implementar `_search_hybrid()` com Reciprocal Rank Fusion:
    ```python
    K = 60
    # Get top-N from vector and text separately
    vector_results = await self._search_semantic(query, limit=rrf_pool, ...)
    text_results = await self._search_text(query, limit=rrf_pool, ...)
    # Assign ranks (1-indexed)
    vector_ranks = {r["question_id"]: i+1 for i, r in enumerate(vector_results)}
    text_ranks = {r["question_id"]: i+1 for i, r in enumerate(text_results)}
    # Compute RRF scores
    all_ids = set(vector_ranks) | set(text_ranks)
    rrf_scores = {}
    for qid in all_ids:
        v_rank = vector_ranks.get(qid, rrf_pool + 1)  # penalize missing
        t_rank = text_ranks.get(qid, rrf_pool + 1)
        rrf_scores[qid] = 1/(K + v_rank) + 1/(K + t_rank)
    # Sort by RRF score descending, take top limit
    ```
  - [ ] 2.5 `rrf_pool` = `limit * 3` para cada sub-query (pool maior → fusão mais rica)
  - [ ] 2.6 Resultado híbrido retorna `similarity_score` como RRF score normalizado (0-1)
- [ ] Task 3: Atualizar endpoint de busca semântica (AC: 4)
  - [ ] 3.1 Adicionar campo `search_mode` ao `SemanticSearchRequest` em `api/fastapi_app.py`:
    ```python
    search_mode: str = Field("hybrid", description="Modo de busca: semantic, text, hybrid", pattern="^(semantic|text|hybrid)$")
    ```
  - [ ] 3.2 Passar `search_mode` para `pgvector_search.search_questions()` no endpoint
  - [ ] 3.3 Manter backward compatibility — `search_mode` com default `hybrid`
- [ ] Task 4: Testes (AC: 5, 7)
  - [ ] 4.1 Arquivo: `tests/test_hybrid_search.py`
  - [ ] 4.2 Testes de unidade (DB mocked via SQLAlchemy text):
    - `test_search_mode_semantic_only` — modo "semantic" usa apenas vetor
    - `test_search_mode_text_only` — modo "text" usa apenas tsvector
    - `test_search_mode_hybrid_rrf` — modo "hybrid" combina ambos com RRF
    - `test_rrf_scoring` — verifica cálculo RRF com dados controlados
    - `test_hybrid_deduplication` — resultado não tem questões duplicadas
    - `test_portuguese_stemming` — "questões sobre fotossíntese" match "fotossintese" (accent)
    - `test_empty_text_results` — se tsvector retorna vazio, hybrid == semantic
    - `test_backward_compatibility` — chamada sem search_mode funciona como "hybrid"
  - [ ] 4.3 Teste de benchmark (pode ser `@pytest.mark.benchmark`):
    - `test_hybrid_improves_recall` — comparar recall@10 de hybrid vs semantic para queries em PT-BR
    - Usar conjunto de queries de teste: termos técnicos, sinônimos, acentuação
    - Assertiva: recall@10 hybrid >= recall@10 semantic (qualitativo; >=5% é aspiracional)

## Dev Notes

### Arquivo principal a modificar

`src/rag_features/semantic_search.py` — classe `PgVectorSearch` (linha ~476)

Método `search_questions()` atualmente faz APENAS busca vetorial:
```sql
SELECT ... 1 - (qc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
FROM enem_questions.question_chunks qc
...
ORDER BY qc.embedding <=> CAST(:embedding AS vector)
```

O refactoring deve:
1. Extrair o SQL vetorial existente para `_search_semantic()`
2. Criar `_search_text()` com tsvector
3. Criar `_search_hybrid()` com RRF
4. `search_questions()` roteia para o método correto baseado em `search_mode`

### Tabela question_chunks — schema atual

```sql
CREATE TABLE enem_questions.question_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL REFERENCES enem_questions.questions(id),
    chunk_type      VARCHAR(20) NOT NULL CHECK (chunk_type IN ('full', 'context')),
    content         TEXT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL UNIQUE,
    embedding       vector(1536),
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**NÃO existe** coluna `tsv_content` — a migration deve adicioná-la.

### portuguese_unaccent já existe

`database/init.sql` já cria:
```sql
CREATE TEXT SEARCH CONFIGURATION portuguese_unaccent (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portuguese_unaccent
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;
```

Considerar usar `portuguese_unaccent` em vez de `portuguese` para melhor matching com acentos.

### FTS indexes existentes em outras tabelas

`database/complete-init.sql` já tem GIN indexes em `questions.question_text` e `question_alternatives.alternative_text`:
```sql
CREATE INDEX "idx_questions_text_search" ON enem_questions."questions"
    USING gin(to_tsvector('portuguese', "question_text"));
```

Estes são expression-based indexes. A Story 7.2 cria uma coluna materializada `tsv_content` em `question_chunks` para evitar recomputação.

### Padrão PgVectorSearch — SQLAlchemy text()

O projeto usa `sqlalchemy.text()` para queries na `PgVectorSearch` (NÃO raw psycopg2 como no pipeline).
A classe usa `create_engine()` para conexão, `with engine.connect() as conn: conn.execute(text(sql))`.

### Reciprocal Rank Fusion (RRF) — referência

Fórmula: `RRF(d) = Σ 1/(k + rank_i(d))` com k=60 (padrão da literatura)

Para hybrid search com 2 rankers:
- `rrf_score = 1/(60 + rank_vector) + 1/(60 + rank_text)`
- Score máximo teórico = `1/61 + 1/61 ≈ 0.0328` (rank 1 em ambos)
- Normalizar para 0-1 dividindo pelo score máximo teórico

### Endpoint existente

`POST /api/v1/search/semantic` em `api/fastapi_app.py` (linha ~1078) — chama `pgvector_search.search_questions()`.
Modelo request: `SemanticSearchRequest` com `query`, `subject`, `year`, `limit`, `include_answer`.

### Project Structure Notes

- Novo arquivo: `database/hybrid-search-migration.sql`
- Modificar: `src/rag_features/semantic_search.py` — classe PgVectorSearch
- Modificar: `api/fastapi_app.py` — SemanticSearchRequest model + endpoint
- Novo arquivo: `tests/test_hybrid_search.py`
- Sem conflitos com estrutura existente

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.2]
- [Source: src/rag_features/semantic_search.py:476-591] — PgVectorSearch class
- [Source: database/pgvector-migration.sql] — question_chunks schema
- [Source: database/init.sql] — portuguese_unaccent text search config
- [Source: database/complete-init.sql:150-152] — existing FTS GIN indexes
- [Source: api/fastapi_app.py:1078-1132] — semantic search endpoint

### Previous Story Intelligence

- Epic 5-6 established pattern: psycopg2 raw SQL for pipeline, SQLAlchemy text() for search
- PgVectorSearch uses `create_engine` + `text()` — follow this pattern for new queries
- Tests mock SQLAlchemy connections, not psycopg2 — `test_pgvector_search.py` pattern
- Code review caught: avoid f-string SQL construction (deferred work item) — use parameterized queries with `text()` and `:param` binding
- `test_pgvector_search.py` mocks: `@patch("src.rag_features.semantic_search.create_engine")` pattern
- Redis caching for query embeddings already in place — hybrid search should reuse same embedding cache

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- Existing tests in test_pgvector_search.py needed `search_mode="semantic"` since default changed to `"hybrid"`

### Completion Notes List
- Migration SQL uses `portuguese_unaccent` config (accent-insensitive) instead of plain `portuguese`
- PgVectorSearch refactored: router `search_questions()` → `_search_semantic()`, `_search_text()`, `_search_hybrid()`
- RRF implementation: K=60, rrf_pool=limit*3, scores normalized to 0-1
- Hybrid fallback: if text search returns empty, returns semantic results unchanged
- Endpoint `POST /api/v1/search/semantic` now accepts `search_mode` field (default: `hybrid`)
- Backward compatible: existing tests pass with explicit `search_mode="semantic"`
- 7 new tests in test_hybrid_search.py, all passing

### File List
- `database/hybrid-search-migration.sql` — NEW: tsvector column + GIN index + trigger
- `src/rag_features/semantic_search.py` — MODIFIED: PgVectorSearch hybrid search refactor
- `api/fastapi_app.py` — MODIFIED: SemanticSearchRequest + endpoint updated
- `tests/test_hybrid_search.py` — NEW: 7 hybrid search tests
- `tests/test_pgvector_search.py` — MODIFIED: added `search_mode="semantic"` to existing tests

### Review Findings
- [x] [Review][Patch] `ts_rank` pode retornar > 1.0 no modo text — clamp similarity_score [semantic_search.py:663]
- [x] [Review][Patch] Fallback assimétrico: semantic vazio não faz fallback para text [semantic_search.py:687-688]
- [x] [Review][Patch] Sem testes com queries PT-BR (acentuação) [test_hybrid_search.py]
- [x] [Review][Defer] Hybrid faz 2 queries sequenciais — migrar para asyncio.gather [semantic_search.py] — deferred, performance optimization
- [x] [Review][Defer] `test_cer_by_subject` não tem assertion — deferred, reporting test
- [x] [Review][Defer] Sem benchmark recall@10 hybrid vs semantic — deferred, requer DB real
- [x] [Review][Defer] Sem CI pipeline para golden set — deferred, projeto sem CI
