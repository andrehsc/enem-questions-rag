# Deferred Work

## Deferred from: code review das stories 3.1, 3.2, 4.1, 4.2 (2026-04-02)

- **f-string SQL construction** [semantic_search.py:search_questions] — `subject_filter`/`year_filter` são strings fixas hoje e não há risco de injection imediato, mas o padrão é perigoso. Migrar para `text()` com `and_()` condicional ao refatorar a query.
- **Credenciais hardcoded como fallback** [fastapi_app.py, semantic_search.py, assessment_generator.py] — `postgresql://postgres:postgres123@localhost:5433/...` como default de `os.getenv("DATABASE_URL", ...)` é padrão pré-existente em toda a codebase. Resolver ao configurar gestão de secrets (vault, .env com validação obrigatória).
- **OPENAI_API_KEY default string vazia** [fastapi_app.py] — `os.getenv("OPENAI_API_KEY", "")` constrói `AsyncOpenAI(api_key="")` com sucesso mas falha na primeira chamada com AuthenticationError. Padrão pré-existente; resolver com validação de env vars no startup.
- **`@app.on_event("startup")` deprecated** [fastapi_app.py] — FastAPI ≥ 0.93 depreca `on_event` em favor do `lifespan` context manager. Refatorar ao atualizar a versão do FastAPI ou ao fazer refactoring geral do app.
