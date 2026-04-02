# Story 3.1: Atualizar Semantic Search para pgvector

**Status:** draft
**Epic:** 3 — Busca Semântica: Feature 1
**Story ID:** 3.1
**Story Key:** `3-1-atualizar-semantic-search-pgvector`
**Criado:** 2026-04-02

---

## Story

Como desenvolvedor,
Quero atualizar `src/rag_features/semantic_search.py` para usar pgvector em vez de ChromaDB/SQLite,
Para que a busca semântica use o mesmo PostgreSQL já em uso no projeto, sem infraestrutura extra.

---

## Acceptance Criteria

1. Classe `PgVectorSearch` implementa a interface `SemanticSearchInterface` existente (`search_questions`, `add_questions_to_index`)
2. Busca por similaridade cosseno usa operador `<=>` do pgvector na tabela `enem_questions.question_chunks`
3. Suporta filtros por metadados via JOIN: `year` (via `exam_metadata`) e `subject` (via `questions`)
4. Reconstrói questão completa agregando chunks por `question_id`: usa chunk `type='full'` como `full_text`
5. Busca retorna no máximo `limit` questões únicas — sem chunks duplicados do mesmo `question_id`
6. ChromaDB e SQLite mantidos como fallback; variável de ambiente `VECTOR_STORE=pgvector` (default) seleciona a implementação
7. Testes unitários cobrem: busca simples, busca com filtro subject, busca com filtro year, resultado vazio, deduplicação de question_id

---

## Tasks / Subtasks

- [ ] **Task 1: Criar `PgVectorSearch` em `src/rag_features/semantic_search.py`** (AC: 1–6)
  - [ ] 1.1 Adicionar imports: `sqlalchemy`, `openai`, dependências pgvector no topo do arquivo
  - [ ] 1.2 Implementar `PgVectorSearch.__init__(database_url, openai_api_key, redis_url)` — instancia engine SQLAlchemy
  - [ ] 1.3 Implementar `_get_query_embedding(query: str) -> List[float]` — chama OpenAI `text-embedding-3-small`; usa Redis cache com TTL 1h
  - [ ] 1.4 Implementar `search_questions(query, limit, year?, subject?) -> List[Dict]` — query pgvector com filtros e deduplicação
  - [ ] 1.5 Implementar `add_questions_to_index(questions)` — stub que leva a notar que ingestão é feita pelo `ingestion_pipeline.py` (raise `NotImplementedError` com mensagem explicativa)
  - [ ] 1.6 Atualizar `create_semantic_search()` factory: verificar `VECTOR_STORE` env var; retornar `PgVectorSearch` por padrão quando `pgvector`

- [ ] **Task 2: Criar `tests/test_pgvector_search.py`** (AC: 1–7)
  - [ ] 2.1 Testar `search_questions` retorna lista com `similarity_score`, `question_id`, `full_text`, `subject`, `year`
  - [ ] 2.2 Testar filtro por `subject`: query SQL inclui `AND q.subject = :subject`
  - [ ] 2.3 Testar filtro por `year`: query SQL inclui `AND em.year = :year`
  - [ ] 2.4 Testar deduplicação: dois chunks do mesmo `question_id` resultam em 1 questão no retorno
  - [ ] 2.5 Testar cache Redis: segunda chamada com mesma query não chama OpenAI API
  - [ ] 2.6 Testar `VECTOR_STORE=pgvector` seleciona `PgVectorSearch` na factory
  - [ ] 2.7 Testar `VECTOR_STORE=chromadb` mantém comportamento original (sem quebrar testes existentes)

---

## Dev Notes

### Arquivo a modificar

```
src/rag_features/semantic_search.py   ← MODIFICAR (adicionar classe PgVectorSearch)
tests/test_pgvector_search.py         ← NOVO
```

**NÃO modificar:** `api/fastapi_app.py`, módulos de ingestão.

### Interface existente a implementar

```python
class SemanticSearchInterface(ABC):
    @abstractmethod
    async def search_questions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool: ...
```

> A interface original não aceita `year`/`subject` — estender a assinatura de `PgVectorSearch.search_questions` com parâmetros opcionais [`year: Optional[int] = None`, `subject: Optional[str] = None`] mantém compatibilidade.

### Schema disponível no banco

```sql
-- Tabela de chunks (pgvector)
enem_questions.question_chunks (
    id UUID, question_id INTEGER, chunk_type VARCHAR(20),
    content TEXT, content_hash VARCHAR(64),
    embedding vector(1536), token_count INTEGER
)

-- Tabelas de referência
enem_questions.questions (
    id INTEGER, question_text TEXT, context_text TEXT,
    subject VARCHAR(100), question_number INTEGER,
    has_images BOOLEAN, embedding_status VARCHAR(20)
)
enem_questions.exam_metadata (id INTEGER, year INTEGER, exam_type VARCHAR, day INTEGER)
enem_questions.question_alternatives (
    question_id INTEGER, alternative_letter CHAR(1),
    alternative_text TEXT, alternative_order INTEGER
)
enem_questions.answer_keys (exam_id INTEGER, question_number INTEGER, correct_answer CHAR(1))
```

### Query SQL central

```python
SEMANTIC_SEARCH_SQL = text("""
    SELECT
        q.id AS question_id,
        q.question_text,
        q.subject,
        em.year,
        qc.chunk_type,
        qc.content AS chunk_content,
        1 - (qc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
    FROM enem_questions.question_chunks qc
    JOIN enem_questions.questions q ON q.id = qc.question_id
    LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
    WHERE qc.chunk_type = 'full'
      AND qc.embedding IS NOT NULL
      {subject_filter}
      {year_filter}
    ORDER BY qc.embedding <=> CAST(:embedding AS vector)
    LIMIT :limit_val
""")
```

### API pública da classe

```python
class PgVectorSearch(SemanticSearchInterface):
    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6380/1",
    ) -> None: ...

    async def search_questions(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError(
            "Indexação feita pelo IngestionPipeline. "
            "Use: python -m src.enem_ingestion.ingestion_pipeline"
        )
```

### Formato de retorno

```python
{
    "question_id": 42,
    "full_text": "enunciado + alternativas",
    "subject": "ciencias_natureza",
    "year": 2023,
    "similarity_score": 0.91,
}
```

### Cache Redis para embeddings de query

```python
cache_key = f"query_emb:{hashlib.md5(query.encode()).hexdigest()}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)
# ... chamar OpenAI ...
redis_client.setex(cache_key, 3600, json.dumps(embedding))  # TTL 1h
```

### Factory atualizada

```python
def create_semantic_search() -> SemanticSearchInterface:
    vector_store = os.getenv("VECTOR_STORE", "pgvector")
    if vector_store == "pgvector":
        return PgVectorSearch(
            database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
        )
    # fallback: comportamento original ChromaDB/SQLite
    ...
```

### Dependências já disponíveis

- `sqlalchemy>=2.0.0` — já em requirements.txt ✅
- `openai>=1.0.0` — adicionado na Story 2.1 ✅
- `redis>=4.6.0` — adicionado na Story 2.1 ✅
- `pgvector-python` — adicionado na Story 1.1 ✅

### Aprendizados das stories anteriores

- `CAST(:param AS vector)` para parâmetros vetoriais no SQLAlchemy (Stories 1.x e 2.x)
- Schema qualificado: `enem_questions.question_chunks` (Story 1.1)
- `DATABASE_URL` padrão: `postgresql://postgres:postgres123@localhost:5433/teachershub_enem`
- 100% mocks nos unit tests — sem banco real, sem OpenAI real, sem Redis real

---

## Estrutura de Testes

```python
# tests/test_pgvector_search.py

class TestPgVectorSearchInit:
    def test_factory_returns_pgvector_when_env_set(self, monkeypatch): ...
    def test_factory_returns_chromadb_fallback(self, monkeypatch): ...

class TestSearchQuestions:
    def test_returns_results_with_required_fields(self, pgvector_search, mocker): ...
    def test_filter_by_subject_adds_where_clause(self, pgvector_search, mocker): ...
    def test_filter_by_year_adds_where_clause(self, pgvector_search, mocker): ...
    def test_deduplicates_by_question_id(self, pgvector_search, mocker): ...
    def test_empty_result_returns_empty_list(self, pgvector_search, mocker): ...

class TestQueryEmbeddingCache:
    def test_cache_hit_skips_openai_call(self, pgvector_search, mocker): ...
    def test_cache_miss_calls_openai_and_stores(self, pgvector_search, mocker): ...
```

---

## Não faz parte desta story

- Endpoint REST — Story 3.2
- Modificar tabelas ou migrations — Épic 1 (já concluído)
- Geração de avaliações ou novas questões — Épic 4
- Modificar `IngestionPipeline` ou módulos de ingestão

---

## Dev Agent Record

*This section will be populated by the development agent during implementation*

---

## Change Log

| Data | Alteração |
|------|-----------|
| 2026-04-02 | Story criada — atualizar semantic_search.py para pgvector (Epic 3, Story 1) |
