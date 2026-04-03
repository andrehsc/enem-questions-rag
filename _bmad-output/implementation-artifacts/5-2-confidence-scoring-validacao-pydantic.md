# Story 5.2: Confidence Scoring & Validação Pydantic

Status: review

## Story

Como desenvolvedor,
Quero um sistema de confidence scoring e validação Pydantic para cada questão extraída,
Para classificar automaticamente a qualidade da extração e direcionar questões para fallback ou dead letter.

## Acceptance Criteria (AC)

1. Model Pydantic `ENEMQuestion` valida: 5 alternativas (A-E), número sequencial, enunciado mínimo (50 chars)
2. Confidence score (0.0-1.0) baseado em: presença de 5 alternativas, texto válido, sequência numérica, comprimento
3. Score ≥ 0.80 → aceita no pipeline
4. Score < 0.80 e ≥ 0.50 → envia para fallback Azure DI (Epic 6)
5. Score < 0.50 → dead letter queue (Epic 6)
6. Campos `confidence_score` e `extraction_method` persistidos no schema
7. Testes com questões de diferentes qualidades (perfeita, parcial, corrompida)

## Tasks / Subtasks

- [ ] Task 1: Migration SQL — novos campos no schema (AC: 6)
  - [ ] 1.1 Criar `database/extraction-v2-migration.sql` com ALTER TABLE para `enem_questions.questions`:
    - `confidence_score FLOAT DEFAULT NULL`
    - `extraction_method VARCHAR(30) DEFAULT 'pdfplumber'` (CHECK: pdfplumber, pymupdf4llm, azure_di, manual)
    - `extraction_errors JSONB DEFAULT NULL`
  - [ ] 1.2 Migration idempotente (`IF NOT EXISTS` / `DO $$ ... $$`)
  - [ ] 1.3 Index: `idx_questions_confidence` em `confidence_score` para queries de fallback
  - [ ] 1.4 Index: `idx_questions_extraction_method` em `extraction_method`
- [ ] Task 2: Model Pydantic `ENEMQuestion` (AC: 1)
  - [ ] 2.1 Criar `src/enem_ingestion/models.py` com models Pydantic v2
  - [ ] 2.2 `ENEMQuestion`: question_number (int, ge=1, le=180), question_text (str, min_length=50), alternatives (list, len=5), subject, metadata
  - [ ] 2.3 `ENEMAlternative`: letter (Literal['A','B','C','D','E']), text (str, min_length=1)
  - [ ] 2.4 Validator: alternativas são exatamente A-E em ordem
  - [ ] 2.5 Validator: question_number dentro do range válido do dia (1-90 Dia 1, 91-180 Dia 2)
  - [ ] 2.6 `from_dataclass(question: Question) -> ENEMQuestion` classmethod para converter das dataclasses existentes
- [ ] Task 3: Confidence Scorer (AC: 2, 3, 4, 5)
  - [ ] 3.1 Criar `src/enem_ingestion/confidence_scorer.py`
  - [ ] 3.2 Classe `ExtractionConfidenceScorer` com método `score(question: Question) -> ConfidenceResult`
  - [ ] 3.3 `ConfidenceResult` dataclass: score (float), passed (bool), issues (List[str]), routing (Literal['accept', 'fallback', 'dead_letter'])
  - [ ] 3.4 Critérios de scoring (peso total = 1.0):
    - Alternativas: +0.30 se exatamente 5 alternativas A-E
    - Texto enunciado: +0.25 se len >= 50 chars e contém texto legível
    - Sequência numérica: +0.20 se question_number segue sequência esperada
    - Comprimento: +0.15 se cada alternativa tem >= 5 chars
    - Pydantic válido: +0.10 se ENEMQuestion.from_dataclass() não levanta ValidationError
  - [ ] 3.5 Routing: score >= 0.80 → 'accept', 0.50 <= score < 0.80 → 'fallback', score < 0.50 → 'dead_letter'
  - [ ] 3.6 Log detalhado: quais critérios passaram/falharam e seus scores individuais
- [ ] Task 4: Integração com pipeline (AC: 6)
  - [ ] 4.1 Função `persist_confidence_metadata(db_url, question_id, score, method, errors)` usando raw SQL
  - [ ] 4.2 UPDATE `enem_questions.questions SET confidence_score = ?, extraction_method = ?, extraction_errors = ? WHERE id = ?`
  - [ ] 4.3 NÃO modificar `pgvector_writer.py` — a persistência dos novos campos é independente
- [ ] Task 5: Testes (AC: 7)
  - [ ] 5.1 Criar `tests/test_confidence_scorer.py`
  - [ ] 5.2 Teste questão perfeita: 5 alternativas, texto longo, número correto → score >= 0.90
  - [ ] 5.3 Teste questão parcial: 3 alternativas, texto curto → score ~0.50-0.70 → routing 'fallback'
  - [ ] 5.4 Teste questão corrompida: sem alternativas, texto < 20 chars → score < 0.50 → routing 'dead_letter'
  - [ ] 5.5 Teste Pydantic validation: alternativas fora de ordem, letra repetida, número inválido
  - [ ] 5.6 Teste ENEMQuestion.from_dataclass() com Question dataclass existente

## Dev Notes

### Arquitetura e Posicionamento

O confidence scorer é chamado APÓS a extração do pymupdf4llm (Story 5.1) e ANTES da persistência no pgvector. O fluxo:

```
pymupdf4llm_extractor.extract_questions()
    → confidence_scorer.score(question)
        → if 'accept': → chunk_builder → embedding → pgvector
        → if 'fallback': → enfileirar para Azure DI (Epic 6)
        → if 'dead_letter': → inserir em dead_letter_questions (Epic 6)
```

### Validação Existente no Projeto (NÃO duplicar)

O projeto já tem validação manual em vários lugares:

- `enem_structure_spec.py:EnemValidationEngine.validate_extraction_result()` — 5 regras com confidence scoring
- `ai_services/common/base_types.py:EnemQuestionData.validate()` — verifica text, 5 alternativas, número
- `alternative_extractor.py:ExtractedAlternatives.confidence` — score por estratégia

**A validação Pydantic SUBSTITUI estas implementações manuais** para novos dados (v2). As validações antigas continuam funcionando para backward compatibility do parser.py original.

### Pydantic v2 — Referência

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, List

class ENEMAlternative(BaseModel):
    letter: Literal['A', 'B', 'C', 'D', 'E']
    text: str = Field(min_length=1)

class ENEMQuestion(BaseModel):
    question_number: int = Field(ge=1, le=180)
    question_text: str = Field(min_length=50)
    alternatives: List[ENEMAlternative] = Field(min_length=5, max_length=5)
    subject: str
    context_text: Optional[str] = None
    confidence_score: Optional[float] = None
    extraction_method: str = 'pymupdf4llm'

    @field_validator('alternatives')
    @classmethod
    def validate_alternatives_order(cls, v):
        expected = ['A', 'B', 'C', 'D', 'E']
        actual = [alt.letter for alt in v]
        if actual != expected:
            raise ValueError(f'Alternativas devem ser A-E em ordem, recebido: {actual}')
        return v
```

### Schema SQL — Migration

```sql
-- database/extraction-v2-migration.sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'enem_questions'
        AND table_name = 'questions'
        AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE enem_questions.questions ADD COLUMN confidence_score FLOAT DEFAULT NULL;
        ALTER TABLE enem_questions.questions ADD COLUMN extraction_method VARCHAR(30) DEFAULT 'pdfplumber';
        ALTER TABLE enem_questions.questions ADD COLUMN extraction_errors JSONB DEFAULT NULL;
        ALTER TABLE enem_questions.questions ADD CONSTRAINT chk_extraction_method
            CHECK (extraction_method IN ('pdfplumber', 'pymupdf4llm', 'azure_di', 'manual'));
        CREATE INDEX idx_questions_confidence ON enem_questions.questions(confidence_score);
        CREATE INDEX idx_questions_extraction_method ON enem_questions.questions(extraction_method);
    END IF;
END $$;
```

### Anti-Patterns a Evitar

- **NÃO** usar `database.py` SQLAlchemy ORM models — o projeto usa raw SQL via psycopg2/SQLAlchemy text()
- **NÃO** duplicar validação existente — usar Pydantic v2 como source of truth para o pipeline v2
- **NÃO** bloquear o pipeline por ValidationError — capturar, logar, e atribuir score baixo
- **NÃO** modificar `parser.py`, `alternative_extractor.py`, ou `enem_structure_spec.py`
- **NÃO** importar models de `api/` — os Pydantic models devem viver em `src/enem_ingestion/`

### Dependências

- `pydantic>=2.0.0` já está em `api/requirements.txt` mas NÃO em `requirements.txt` principal
- Adicionar `pydantic>=2.0.0` ao `requirements.txt` principal

### Project Structure Notes

- Novo arquivo: `src/enem_ingestion/models.py` (Pydantic models)
- Novo arquivo: `src/enem_ingestion/confidence_scorer.py`
- Novo arquivo: `database/extraction-v2-migration.sql`
- Novo arquivo: `tests/test_confidence_scorer.py`
- Novo arquivo: `tests/test_models.py` (Pydantic validation tests)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2]
- [Source: src/enem_ingestion/enem_structure_spec.py — EnemValidationEngine (validação manual existente)]
- [Source: src/ai_services/common/base_types.py — EnemQuestionData.validate()]
- [Source: src/enem_ingestion/parser.py — Question dataclass, Subject enum]
- [Source: database/pgvector-migration.sql — schema enem_questions.questions]
- [Source: database/complete-init.sql — schema completo]

### Testing Standards

- Framework: `pytest` + `pytest-mock`
- Pattern: criar questões com diferentes graus de qualidade via fixtures
- Naming: `test_score_perfect_question`, `test_score_partial_question`, `test_score_corrupted_question`
- Coverage: `--cov=src` (pytest.ini)
- NÃO depender de banco real — testar scorer como pure function

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- models.py: ENEMQuestion + ENEMAlternative Pydantic v2, from_dataclass converter, order validator
- confidence_scorer.py: 5-criteria scoring (alts 0.30, text 0.25, seq 0.20, alt_len 0.15, pydantic 0.10), routing logic
- extraction-v2-migration.sql: idempotent ALTER TABLE for confidence_score, extraction_method, extraction_errors
- 17 tests pass: Pydantic validation (8), scorer (6), routing (3)

### File List

- src/enem_ingestion/models.py (new)
- src/enem_ingestion/confidence_scorer.py (new)
- database/extraction-v2-migration.sql (new)
- tests/test_confidence_scorer.py (new)
- requirements.txt (modified — added pydantic>=2.0.0)