# Story 6.1: Azure DI Layout Fallback

Status: done

## Story

Como desenvolvedor,
Quero um módulo de fallback que use Azure Document Intelligence Layout para reprocessar questões com baixa confiança,
Para recuperar questões que o pymupdf4llm não extraiu corretamente.

## Acceptance Criteria (AC)

1. Usa `DocumentIntelligenceClient` com `begin_analyze_document("prebuilt-layout")`
2. Ativado automaticamente para questões com confidence < 0.80 (routing "fallback")
3. Add-on `DocumentAnalysisFeature.FORMULAS` ativado para extrair LaTeX
4. Output em `ContentFormat.MARKDOWN` para compatibilidade com parser existente
5. Re-scoring após extração Azure DI para validar melhoria de qualidade
6. Controle de custo: tracking de páginas processadas vs budget R$50
7. Testes com mock do Azure DI SDK (sem chamadas reais no CI)

## Tasks / Subtasks

- [ ] Task 1: Criar `src/enem_ingestion/azure_di_fallback.py` — Módulo fallback (AC: 1, 2, 3, 4)
  - [ ] 1.1 Classe `AzureDIFallback` com construtor: `(endpoint, key, budget_limit=50.0)`
    - Config via env vars: `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY`
  - [ ] 1.2 Método `process_fallback_questions(questions: List[Question], pdf_path: str) -> List[FallbackResult]`
    - Recebe a lista de `report.fallback_questions` do pipeline_v2
    - Para cada questão, identifica a(s) página(s) relevante(s) no PDF
  - [ ] 1.3 Método interno `_analyze_pages(pdf_path, pages: str) -> AnalyzeResult`
    - Chama `client.begin_analyze_document("prebuilt-layout", ...)` com:
      - `content_type="application/octet-stream"`
      - `output_content_format=ContentFormat.MARKDOWN`
      - `features=[DocumentAnalysisFeature.FORMULAS, DocumentAnalysisFeature.OCR_HIGH_RESOLUTION]`
      - `pages=pages` (ex: "5-7")
    - Usa poller síncrono (`.result()`) — polling built-in do SDK
  - [ ] 1.4 Parse markdown output do Azure DI → `List[Question]` via regex igual ao `pymupdf4llm_extractor._split_questions()`
    - Reutilizar `QUESTION_SPLIT_RE` e `QUESTION_BOLD_RE` de `pymupdf4llm_extractor.py`
    - Reutilizar `_extract_alternatives_simple()` e `_extract_enunciado()` ou delegar para `EnhancedAlternativeExtractor`
  - [ ] 1.5 `FallbackResult` dataclass: `question`, `original_score`, `new_score`, `improved` (bool), `method='azure_di'`
- [ ] Task 2: Re-scoring e routing (AC: 5)
  - [ ] 2.1 Após extração Azure DI, re-score via `ExtractionConfidenceScorer.score()`
  - [ ] 2.2 Se `new_score >= ACCEPT_THRESHOLD (0.80)` → persist com `extraction_method='azure_di'`
  - [ ] 2.3 Se `new_score < ACCEPT_THRESHOLD` → encaminhar para dead_letter (Story 6.2)
  - [ ] 2.4 Log detalhado: `[FALLBACK_IMPROVED] Q{n} {old_score:.2f} → {new_score:.2f}` ou `[FALLBACK_FAILED]`
- [ ] Task 3: Controle de custo (AC: 6)
  - [ ] 3.1 `CostTracker` dataclass: `pages_processed`, `estimated_cost_brl`, `budget_limit_brl`
  - [ ] 3.2 Preço Layout: R$50/1000 páginas ≈ R$0.05/página (com créditos Azure acadêmicos)
  - [ ] 3.3 Antes de cada chamada, verificar `estimated_cost + page_cost <= budget_limit`
  - [ ] 3.4 Se budget excedido: log WARNING, pular questão, contar como `budget_exceeded`
  - [ ] 3.5 Report inclui: `pages_processed`, `estimated_cost_brl`, `budget_remaining`
- [ ] Task 4: Integrar no pipeline_v2 (AC: 2)
  - [ ] 4.1 Adicionar `azure_config: Optional[dict] = None` ao construtor de `ExtractionPipelineV2`
    - `azure_config = {"endpoint": ..., "key": ..., "budget_limit": 50.0}` ou None para desabilitar
  - [ ] 4.2 Após processar todos PDFs, se `azure_config` e `report.fallback_questions` não vazio:
    - Instanciar `AzureDIFallback(azure_config)`
    - Chamar `process_fallback_questions(report.fallback_questions, pdf_path)` para cada PDF
    - Atualizar report counters
  - [ ] 4.3 CLI: adicionar `--azure-endpoint`, `--azure-key`, `--azure-budget` ao argparse
    - Defaults via env vars: `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY`, `AZURE_DI_BUDGET`
  - [ ] 4.4 Se nenhuma config Azure fornecida, fallback questions permanecem como placeholders (sem erro)
- [ ] Task 5: Testes (AC: 7)
  - [ ] 5.1 Criar `tests/test_azure_di_fallback.py`
  - [ ] 5.2 Mock completo de `DocumentIntelligenceClient` — NÃO chamar Azure real
  - [ ] 5.3 Teste: questão fallback processada → score melhora → accepted
  - [ ] 5.4 Teste: questão fallback processada → score NÃO melhora → dead_letter
  - [ ] 5.5 Teste: budget excedido → questão pulada com warning
  - [ ] 5.6 Teste: re-scoring usa `ExtractionConfidenceScorer` real
  - [ ] 5.7 Teste: LaTeX formula em markdown é preservada
  - [ ] 5.8 Teste: pipeline_v2 com azure_config=None não chama Azure (backward compat)

## Dev Notes

### Arquitetura do Fallback

```
pipeline_v2.py (orchestrator)
├── pymupdf4llm extractor → score → accept/fallback/dead_letter
│
├── azure_di_fallback.py (ESTE MÓDULO)
│   ├── DocumentIntelligenceClient (Azure SDK)
│   ├── EnhancedAlternativeExtractor (reuse)
│   ├── ExtractionConfidenceScorer (re-score)
│   └── CostTracker
│
└── Persist: accepted questions → DB (extraction_method='azure_di')
```

### Azure DI SDK — Referência (pesquisa confirmada)

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest, ContentFormat,
    DocumentAnalysisFeature, AnalyzeOutputOption
)
from azure.core.credentials import AzureKeyCredential

client = DocumentIntelligenceClient(
    endpoint=os.environ["AZURE_DI_ENDPOINT"],
    credential=AzureKeyCredential(os.environ["AZURE_DI_KEY"])
)

with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=f,
        content_type="application/octet-stream",
        output_content_format=ContentFormat.MARKDOWN,
        features=[
            DocumentAnalysisFeature.FORMULAS,
            DocumentAnalysisFeature.OCR_HIGH_RESOLUTION,
        ],
        pages="1-5",  # process specific pages
    )
result = poller.result()
markdown_content = result.content  # full markdown output
```

**Pacotes necessários:** `azure-ai-documentintelligence>=1.0.0b4` (não confundir com `azure-ai-formrecognizer` que é legacy).

### Padrão de DB Existente

Seguir raw SQL via psycopg2 (mesmo padrão do `pipeline_v2.py`):
- `extraction_method` já aceita `'azure_di'` (CHECK constraint na migration)
- `extraction_errors` JSONB pode ser preenchido com detalhes do fallback
- `confidence_score` atualizado com o re-score

### Deferred Items Resolvidos Nesta Story

- `azure_config constructor param` → implementado como Task 4.1
- `extraction_errors JSONB never populated` → preenchido com Azure DI errors/details

### Anti-Patterns a Evitar

- **NÃO** chamar Azure DI para questões com routing "accept" — já estão OK
- **NÃO** processar o PDF inteiro no Azure DI — processar apenas as páginas das questões fallback
- **NÃO** usar `azure-ai-formrecognizer` — é legacy; usar `azure-ai-documentintelligence`
- **NÃO** depender de Azure DI nos testes — mock completo do SDK
- **NÃO** modificar `pymupdf4llm_extractor.py` ou `confidence_scorer.py`
- **NÃO** usar SQLAlchemy ORM — manter raw SQL via psycopg2

### Dependências

- `azure-ai-documentintelligence>=1.0.0b4` — adicionar ao `requirements.txt`
- `azure-core>=1.30.0` — transitive dependency
- Env vars: `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY` (opcionais, fallback desativado se ausentes)

### Project Structure Notes

- Novo arquivo: `src/enem_ingestion/azure_di_fallback.py`
- Novo arquivo: `tests/test_azure_di_fallback.py`
- Modificar: `src/enem_ingestion/pipeline_v2.py` (azure_config, CLI args)
- Modificar: `requirements.txt` (adicionar azure-ai-documentintelligence)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1]
- [Source: _bmad-output/planning-artifacts/research/technical-pdf-extraction-enem-research-2026-04-02.md — Azure DI SDK sample]
- [Source: src/enem_ingestion/pipeline_v2.py — fallback_questions placeholder, ExtractionPipelineV2]
- [Source: src/enem_ingestion/confidence_scorer.py — ExtractionConfidenceScorer, ACCEPT_THRESHOLD]
- [Source: src/enem_ingestion/pymupdf4llm_extractor.py — QUESTION_SPLIT_RE, _extract_alternatives_simple]
- [Source: database/extraction-v2-migration.sql — extraction_method CHECK includes 'azure_di']
- [Source: _bmad-output/implementation-artifacts/deferred-work.md — azure_config, extraction_errors deferred]

### Testing Standards

- Framework: `pytest` + `pytest-mock`
- Pattern: mock `DocumentIntelligenceClient` completamente — NÃO chamar Azure
- Mock `poller.result()` retornando markdown com questões ENEM
- Naming: `test_fallback_improves_score`, `test_fallback_still_low`, `test_budget_exceeded`, `test_pipeline_integration`
- Coverage: `--cov=src` (pytest.ini)
- NÃO depender de Azure real — testar como pure functions com mocks

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- azure_di_fallback.py: AzureDIFallback class with lazy client init, cost tracking, page estimation, re-scoring
- CostTracker dataclass with budget enforcement (R$0.05/page)
- FallbackResult dataclass for per-question outcomes
- Markdown parsing reuses QUESTION_SPLIT_RE/QUESTION_BOLD_RE from pymupdf4llm_extractor
- pipeline_v2.py: added azure_config param, _run_azure_fallback method, CLI args for Azure
- 11 tests pass: cost tracker (3), fallback processing (7), pipeline backward compat (1)

### File List

- src/enem_ingestion/azure_di_fallback.py (new)
- tests/test_azure_di_fallback.py (new)
- src/enem_ingestion/pipeline_v2.py (modified — azure_config, fallback integration, CLI args)
- requirements.txt (modified — added azure-ai-documentintelligence>=1.0.0b4)
