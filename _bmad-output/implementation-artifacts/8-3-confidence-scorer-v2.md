# Story 8.3: Confidence Scorer v2

Status: pending

## Story

Como desenvolvedor,
Quero que o scorer detecte contaminação textual e não aprove questões com placeholders, cid tokens ou headers residuais,
Para que apenas questões limpas sejam aceitas no banco.

## Acceptance Criteria (AC)

1. Penalização por placeholders ([Alternative not found]) em alternativas → score 0.0 para alt_quality
2. Penalização por contaminação: (cid:XX), InDesign, headers ENEM, timestamps → score 0.0 para contamination
3. Penalização por cascata: alt_A.length > 3 * alt_E.length → partial score para alt_quality
4. Novos pesos: alt_count 0.20, text_quality 0.20, alt_quality 0.25, sequence 0.15, contamination 0.10, pydantic 0.10
5. Threshold mais rigoroso: ACCEPT >= 0.85, FALLBACK >= 0.55
6. Testes com questões contaminadas (devem falhar) e limpas (devem passar)

## Tasks / Subtasks

- [ ] Task 1: Adicionar check de contaminação (AC: 2)
  - [ ] 1.1 Novo método `_score_contamination(question, issues) -> float` (peso 0.10)
  - [ ] 1.2 Detectar tokens `(cid:\d+)` em text ou alternatives
  - [ ] 1.3 Detectar artefatos InDesign (reusar regex de TextSanitizer ou import direto)
  - [ ] 1.4 Detectar headers ENEM residuais (CADERNO, NEM2024, áreas temáticas)
  - [ ] 1.5 Detectar timestamps duplicados
  - [ ] 1.6 Qualquer contaminação detectada → 0.0 para este componente + issue registrada
- [ ] Task 2: Adicionar check de placeholder (AC: 1)
  - [ ] 2.1 Em `_score_alt_quality()` (novo método, substitui `_score_alt_length()`):
    - Verificar se qualquer alternativa contém `[Alternative not found]` ou `[Alternativa não encontrada]`
    - Se sim: score 0.0 + issue `"placeholder_detected"`
  - [ ] 2.2 Também verificar alternativas com texto vazio ou < 1 char
- [ ] Task 3: Adicionar check de cascata (AC: 3)
  - [ ] 3.1 Em `_score_alt_quality()`:
    - Se 5 alternativas presentes E `len(alt_A) > 3 * len(alt_E)`: cascade suspected
    - Adicionar issue `"cascade_suspected"`, partial score 0.05
  - [ ] 3.2 Check adicional: se `alt_B in alt_A and alt_C in alt_B`: cascade confirmed
    - Score 0.0 + issue `"cascade_confirmed"`
- [ ] Task 4: Recalibrar pesos (AC: 4)
  - [ ] 4.1 Novos pesos:
    ```python
    # Antes:
    # alternatives  0.30, text  0.25, sequence  0.20, alt_length  0.15, pydantic  0.10

    # Depois:
    WEIGHTS = {
        'alt_count': 0.20,       # Exatamente 5 alternativas A-E
        'text_quality': 0.20,    # Enunciado >= 50 chars, conteúdo legível
        'alt_quality': 0.25,     # Sem placeholder, sem cascata, cada alt >= 3 chars
        'sequence': 0.15,        # question_number 1-180
        'contamination': 0.10,   # Sem cid, sem InDesign, sem headers
        'pydantic': 0.10,        # Validação Pydantic completa
    }
    ```
  - [ ] 4.2 Renomear `_score_alternatives` → `_score_alt_count` (clareza)
  - [ ] 4.3 Substituir `_score_alt_length` por `_score_alt_quality` (inclui placeholder + cascade + length)
  - [ ] 4.4 Adicionar `_score_contamination` (novo)
- [ ] Task 5: Ajustar thresholds (AC: 5)
  - [ ] 5.1 `ACCEPT_THRESHOLD` de 0.80 para 0.85
  - [ ] 5.2 `FALLBACK_THRESHOLD` de 0.50 para 0.55
- [ ] Task 6: Testes (AC: 6)
  - [ ] 6.1 Teste: questão limpa com 5 alternativas corretas → score >= 0.85, routing = "accept"
  - [ ] 6.2 Teste: questão com `[Alternative not found]` em alt E → score < 0.85, routing != "accept"
  - [ ] 6.3 Teste: questão com tokens (cid:XX) no enunciado → contamination = 0.0
  - [ ] 6.4 Teste: questão com cascata (alt_A = 500 chars, alt_E = 50 chars) → alt_quality penalizado
  - [ ] 6.5 Teste: questão com header InDesign no enunciado → contamination = 0.0
  - [ ] 6.6 Teste de thresholds: score 0.84 → fallback, score 0.85 → accept, score 0.54 → dead_letter
  - [ ] 6.7 Atualizar `tests/test_confidence_scorer.py` existente

## Dev Notes

### Estado atual do confidence_scorer.py

```python
# Pesos atuais (linhas 33-39):
#   alternatives  0.30 — exactly 5 alternatives A-E
#   text          0.25 — enunciado >= 50 chars
#   sequence      0.20 — question_number 1-180
#   alt_length    0.15 — each alternative >= 5 chars
#   pydantic      0.10 — Pydantic validation passes

ACCEPT_THRESHOLD = 0.80   # linha 41
FALLBACK_THRESHOLD = 0.50  # linha 42
```

### Bug crítico: placeholders passam o scorer

`[Alternative not found]` tem 27 caracteres → passa o check `len(a) >= 5` na linha 112.

Uma questão com 3 alternativas reais + 2 placeholders pode atingir:
- alt_count: 0.30 (tem 5 items)
- text: 0.25 (se >= 50 chars)
- sequence: 0.20 (se 1-180)
- alt_length: 0.15 (todos >= 5 chars)
- pydantic: 0.10
- **Total: 1.00** → "accept" com dados falsos no banco!

### Dependências

- Depende de Story 8.1 (TextSanitizer) para regex de contaminação
- Pode reusar patterns de `TextSanitizer` via import

### Anti-Patterns a Evitar

- NÃO criar dependência circular entre scorer e sanitizer — preferir importar apenas as constantes/regex
- NÃO penalizar questões com texto curto que sejam matemáticas (alternativas de 1-2 chars são legítimas)

### References

- [Source: confidence_scorer.py:33-42] — current weights and thresholds
- [Source: confidence_scorer.py:87-91] — _score_alternatives (to rename)
- [Source: confidence_scorer.py:109-116] — _score_alt_length (to replace)
- [Source: text_sanitizer.py] — regex patterns for contamination detection (Story 8.1)

## Dev Agent Record

### Agent Model Used
(pending)

### Debug Log References
(pending)

### Completion Notes List
(pending)

### File List
(pending)

### Review Findings
(pending)
