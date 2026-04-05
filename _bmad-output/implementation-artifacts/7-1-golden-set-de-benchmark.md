# Story 7.1: Golden Set de Benchmark

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero um golden set de 50 questões ENEM verificadas manualmente,
Para servir como benchmark de acurácia do pipeline de extração.

## Acceptance Criteria (AC)

1. 50 questões selecionadas: 10 por área (Linguagens, Humanas, Natureza, Matemática, Redação-suporte)
2. Cada questão inclui: texto-base (se presente), enunciado, 5 alternativas, gabarito, metadados
3. Formato JSON como fixture pytest (`tests/fixtures/golden_set.json`)
4. Script de validação compara output do pipeline vs golden set
5. Métricas: acurácia, CER (Character Error Rate), completude de alternativas
6. CI executa validação contra golden set em cada PR

## Tasks / Subtasks

- [ ] Task 1: Criar diretório e fixture `tests/fixtures/golden_set.json` (AC: 1, 2, 3)
  - [ ] 1.1 Criar `tests/fixtures/` directory
  - [ ] 1.2 Selecionar 50 questões dos PDFs ENEM já baixados em `data/downloads/`:
    - 10 Linguagens (Subject.linguagens)
    - 10 Ciências Humanas (Subject.ciencias_humanas)
    - 10 Ciências da Natureza (Subject.ciencias_natureza)
    - 10 Matemática (Subject.matematica)
    - 10 mistas — incluindo questões com texto-base, imagens, fórmulas
  - [ ] 1.3 Formato JSON — cada questão como objeto:
    ```json
    {
      "questions": [
        {
          "id": "gs-001",
          "year": 2023,
          "day": 1,
          "caderno": "CD1",
          "application_type": "regular",
          "question_number": 1,
          "subject": "linguagens",
          "context_text": "Texto-base da questão (ou null)",
          "question_text": "Enunciado completo da questão",
          "alternatives": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
          "correct_answer": "A",
          "has_images": false,
          "has_formulas": false,
          "notes": "observações sobre esta questão"
        }
      ]
    }
    ```
  - [ ] 1.4 Validar manualmente que o texto extraído corresponde exatamente ao PDF original
- [ ] Task 2: Criar script de validação `tests/test_golden_set.py` (AC: 4, 5)
  - [ ] 2.1 Fixture `golden_questions` carrega `tests/fixtures/golden_set.json`
  - [ ] 2.2 Função `compare_extraction(extracted: Question, golden: dict) -> dict` retorna métricas:
    - `text_match`: bool — enunciado extraído contém o texto esperado
    - `cer`: float — Character Error Rate calculado via `difflib.SequenceMatcher`
    - `alternatives_complete`: bool — 5 alternativas extraídas
    - `alt_match_count`: int — quantas alternativas correspondem (0-5)
    - `number_correct`: bool — `question_number` correto
    - `subject_correct`: bool — `subject` correto
  - [ ] 2.3 Teste `test_pipeline_vs_golden_set` que:
    - Executa `Pymupdf4llmExtractor.extract_questions()` nos PDFs do golden set
    - Compara cada questão extraída com a referência golden
    - Calcula métricas agregadas: acurácia total, CER médio, taxa de alternativas completas
    - Assertiva: acurácia >= 0.98 (49/50 corretas)
    - Assertiva: CER médio < 0.02
    - Assertiva: taxa de alternativas completas >= 0.99
  - [ ] 2.4 Teste `test_confidence_scores_golden_set` que:
    - Roda `ExtractionConfidenceScorer.score()` em cada questão extraída
    - Assertiva: todas as 50 questões devem ter score >= 0.80 (routing = "accept")
  - [ ] 2.5 Helper `_find_golden_pdf(year, day, caderno)` localiza PDF em `data/downloads/`
- [ ] Task 3: Pytest marker e CI integration (AC: 6)
  - [ ] 3.1 Registrar marker `@pytest.mark.golden` em `pyproject.toml` ou `conftest.py`
  - [ ] 3.2 Testes golden set marcados com `@pytest.mark.golden`
  - [ ] 3.3 Testes que dependem de PDFs marcados com `@pytest.mark.skipif` caso `data/downloads/` esteja vazio
  - [ ] 3.4 Documentar no README ou docstring: como executar golden set benchmark

## Dev Notes

### Padrão do projeto

- **Raw SQL / psycopg2** para queries de banco (NÃO usar SQLAlchemy ORM)
- **Testes mocked** para DB; golden set testa extraction (PDF → Question), não persistência
- **Parser dataclasses**: `Question`, `QuestionMetadata`, `Subject` em `src/enem_ingestion/parser.py`
- **Pydantic model**: `ENEMQuestion` em `src/enem_ingestion/models.py`
- **Extractor**: `Pymupdf4llmExtractor` em `src/enem_ingestion/pymupdf4llm_extractor.py`
- **Scorer**: `ExtractionConfidenceScorer` em `src/enem_ingestion/confidence_scorer.py`

### Confidence Scorer — pesos e thresholds

| Componente | Peso | Critério |
|---|---|---|
| alternatives | 0.30 | Exatamente 5 alternativas A-E |
| text | 0.25 | enunciado >= 50 chars |
| sequence | 0.20 | question_number 1-180 |
| alt_length | 0.15 | cada alternativa >= 5 chars |
| pydantic | 0.10 | ENEMQuestion valida |

Thresholds: ACCEPT >= 0.80, FALLBACK >= 0.50, DEAD_LETTER < 0.50

### Character Error Rate (CER)

Usar `difflib.SequenceMatcher` do stdlib para calcular CER:
```python
def calculate_cer(extracted: str, reference: str) -> float:
    sm = difflib.SequenceMatcher(None, extracted, reference)
    return 1.0 - sm.ratio()
```

### Subject enum values

`Subject` enum em parser.py: `linguagens`, `ciencias_humanas`, `ciencias_natureza`, `matematica`

### Padrão de parse do filename

`Pymupdf4llmExtractor._parser.parse_filename(pdf_path.name)` → `QuestionMetadata`

Formato: `{year}_PV_{application_type}_D{day}_{caderno}.pdf`

### Localização dos PDFs

PDFs ENEM estão em `data/downloads/` com formato `2023_PV_regular_D1_CD1.pdf`.
Se não houver PDFs baixados, os testes devem ser skippados graciosamente.

### Project Structure Notes

- Novo diretório: `tests/fixtures/` (não existe ainda)
- Novo arquivo: `tests/fixtures/golden_set.json`
- Novo arquivo: `tests/test_golden_set.py`
- Modificar: `pyproject.toml` ou `conftest.py` para registrar marker `golden`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1]
- [Source: src/enem_ingestion/confidence_scorer.py] — scoring weights and thresholds
- [Source: src/enem_ingestion/pymupdf4llm_extractor.py] — extractor API
- [Source: src/enem_ingestion/parser.py] — Question, QuestionMetadata, Subject
- [Source: src/enem_ingestion/models.py] — ENEMQuestion Pydantic model

### Previous Story Intelligence

- Epic 5 code review fixed context manager leaks in `_detect_scanned_pages` and `_get_image_bboxes` — use `with pymupdf.open() as doc:` pattern
- Epic 6 code review fixed score propagation bugs — `fallback_scores` dict now tracks both fallback and dead_letter questions
- All tests use mocks heavily for psycopg2 connections — golden set is the first test that exercises real extraction without DB mocks
- Tests run via `python -m pytest tests/ --ignore=tests/ai_services` to avoid aiohttp import error

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
