# Deferred Work

## Deferred from: code review das stories 3.1, 3.2, 4.1, 4.2 (2026-04-02)

- **f-string SQL construction** [semantic_search.py:search_questions] — `subject_filter`/`year_filter` são strings fixas hoje e não há risco de injection imediato, mas o padrão é perigoso. Migrar para `text()` com `and_()` condicional ao refatorar a query.
- **Credenciais hardcoded como fallback** [fastapi_app.py, semantic_search.py, assessment_generator.py] — `postgresql://postgres:postgres123@localhost:5433/...` como default de `os.getenv("DATABASE_URL", ...)` é padrão pré-existente em toda a codebase. Resolver ao configurar gestão de secrets (vault, .env com validação obrigatória).
- **OPENAI_API_KEY default string vazia** [fastapi_app.py] — `os.getenv("OPENAI_API_KEY", "")` constrói `AsyncOpenAI(api_key="")` com sucesso mas falha na primeira chamada com AuthenticationError. Padrão pré-existente; resolver com validação de env vars no startup.
- **`@app.on_event("startup")` deprecated** [fastapi_app.py] — FastAPI ≥ 0.93 depreca `on_event` em favor do `lifespan` context manager. Refatorar ao atualizar a versão do FastAPI ou ao fazer refactoring geral do app.

## Deferred from: code review of Epic 5 (2026-04-03)

- **Image bbox via to_json()**: Story 5.1 spec recommended `pymupdf4llm.to_json()` for bounding boxes, but implementation uses `pymupdf.open()` + `get_image_rects()` directly. Both work; current approach is simpler.
- **Content-level dual-hash**: Story 5.3 spec mentions file-level + content-level hash. Content-level hash already exists in `chunk_builder.py`. Pipeline v2 only implements layer 1 (file-level) — by design.
- **Day-range validation (1-90 / 91-180)**: Pydantic model validates 1-180 but doesn't enforce day-specific ranges. Enhancement candidate.
- **extraction_errors JSONB never populated**: Column exists in migration but pipeline_v2 doesn't write to it. Placeholder for Epic 6.
- **azure_config constructor param**: Story 5.3 spec mentions `azure_config=None` but implementation omits it. Epic 6 scope.
- **test_models.py not created as separate file**: Pydantic model tests live in `tests/test_confidence_scorer.py`.
- **Single DB connection per pipeline run**: Acceptable for batch. Consider connection pooling for production scale.
- **Stale alternatives after UPSERT**: If question re-extracted with fewer alternatives, old ones remain. Low risk since ENEM always has 5.

## Deferred from: code review of Epic 6 (2026-04-03)

- **No auth on admin endpoints** [fastapi_app.py] — GET/PATCH `/api/v1/admin/dead-letter` have no authentication. Project has zero auth on any endpoint; admin auth is future scope.
- **UUID validation on dl_id path parameter** [fastapi_app.py] — `dl_id` is passed as a raw string without UUID format validation. Invalid UUIDs will fail at the DB layer with a 503 instead of 400. Nice-to-have improvement.
- **Missing Pydantic response models for admin endpoints** [fastapi_app.py] — Admin endpoints return raw dicts instead of typed response models. Endpoints work correctly; typed responses would improve Swagger docs.

## Deferred from: code review of Epic 7 (2026-04-05)

- **Hybrid queries sequenciais** [semantic_search.py:_search_hybrid] — `_search_semantic` e `_search_text` executam sequencialmente; migrar para `asyncio.gather()` para reduzir latência.
- **`test_cer_by_subject` sem assertion** [test_golden_set.py] — Teste apenas imprime CER por área sem assertiva de threshold. Adicionar assertion quando thresholds realistas forem definidos.
- **Benchmark recall@10 hybrid vs semantic** [Story 7.2 AC5] — Requer dados reais no banco para comparar recall híbrido vs semântico. Implementar quando DB de staging estiver disponível.
- **Golden set sem CI pipeline** [Story 7.1 AC6] — Registrar marcador `golden` no CI quando pipelines forem configuradas.
- **Golden set: falta área Redação-suporte** [golden_set.json] — AC1 pede 10 questões Redação-suporte; não há questões desse tipo no dataset extraído. Preencher quando houver curadoria manual.
- **Golden set: alternatives e gabarito vazios** [golden_set.json] — Todas 50 questões têm alternatives=[] e correct_answer=null. Extrator embute alternativas no texto. Curadoria manual necessária para golden set definitivo.
- **Golden set: has_images inconsistente** [golden_set.json] — Questionários com imagens referenciadas no context_text têm has_images=false. Ajustar na curadoria manual.
