# Story 9.3: Recalibrar Peso de Contaminação no Scorer

Status: done

## Story

Como desenvolvedor,
Quero que questões com contaminação textual detectada não sejam aceitas no banco (score < 0.85),
Para que a qualidade mínima das questões aceitas seja garantida e questões poluídas vão para fallback.

## Acceptance Criteria (AC)

1. Questão com contaminação detectada tem score máximo < 0.85 (roteada para fallback, não accept)
2. Questão limpa com 5 alternativas corretas ainda alcança score 1.00
3. Novo check: alternativas brutas no enunciado → contaminação detectada
4. Redistribuição de pesos mantém total = 1.00
5. Testes atualizados refletem novos pesos
6. Nenhuma questão limpa existente é rejeitada indevidamente

## Tasks / Subtasks

- [ ] Task 1: Redistribuir pesos (AC: 1, 2, 4)
  - [ ] 1.1 Em `confidence_scorer.py`, alterar pesos:
    ```python
    # Antes (v2 — Epic 8):
    # alt_count=0.20, text_quality=0.20, alt_quality=0.25,
    # sequence=0.15, contamination=0.10, pydantic=0.10

    # Depois (v3 — Epic 9):
    # alt_count=0.20, text_quality=0.15, alt_quality=0.25,
    # sequence=0.10, contamination=0.20, pydantic=0.10
    ```
  - [ ] 1.2 Validar que questão limpa: 0.20+0.15+0.25+0.10+0.20+0.10 = 1.00 → accept
  - [ ] 1.3 Validar que questão contaminada: 0.20+0.15+0.25+0.10+**0.00**+0.10 = 0.80 → fallback (< 0.85)
  - [ ] 1.4 Atualizar docstring da classe e comentários inline

- [ ] Task 2: Atualizar `_score_text_quality()` (AC: 1)
  - [ ] 2.1 Reduzir retorno de 0.20 para 0.15 quando texto >= 50 chars

- [ ] Task 3: Atualizar `_score_sequence()` (AC: 1)
  - [ ] 3.1 Reduzir retorno de 0.15 para 0.10 quando número 1-180

- [ ] Task 4: Ampliar `_score_contamination()` (AC: 1, 3)
  - [ ] 4.1 Aumentar retorno de 0.10 para 0.20 quando sem contaminação
  - [ ] 4.2 Adicionar check de alternativas brutas no enunciado:
    ```python
    # Detectar linhas que parecem alternativas brutas no question.text
    raw_alt_pattern = re.compile(r'^[A-E]\s+\S.{2,}', re.MULTILINE)
    raw_matches = raw_alt_pattern.findall(question.text or "")
    if len(raw_matches) >= 3:
        issues.append("raw_alternatives_in_enunciado")
        return 0.0
    ```

- [ ] Task 5: Testes (AC: 5, 6)
  - [ ] 5.1 Atualizar testes existentes em `tests/test_confidence_scorer.py`:
    - Ajustar scores esperados para novos pesos
    - Verificar que test_clean_question ainda retorna 1.00
    - Verificar que test_contaminated_question retorna < 0.85
  - [ ] 5.2 Novo teste: questão com alternativas brutas no enunciado → contamination = 0.0
  - [ ] 5.3 Novo teste: questão com score exatamente 0.80 (contaminada) → routing = "fallback"
  - [ ] 5.4 Novo teste: questão com score 0.85 (limpa mas com alt curta) → routing = "accept"

## Dev Notes

### Problema

Com pesos atuais, questão contaminada mas com boas alternativas:
- alt_count=0.20 + text_quality=0.20 + alt_quality=0.25 + sequence=0.15 + **contamination=0.00** + pydantic=0.10
- **Total = 0.90 → ACCEPT** (deveria ser fallback)

Com novos pesos:
- alt_count=0.20 + text_quality=0.15 + alt_quality=0.25 + sequence=0.10 + **contamination=0.00** + pydantic=0.10
- **Total = 0.80 → FALLBACK** (correto)

### Estado atual do confidence_scorer.py

```python
# confidence_scorer.py:38-48
class ExtractionConfidenceScorer:
    """Weights (total = 1.0) — v2:
        alt_count       0.20
        text_quality    0.20   ← reduzir para 0.15
        alt_quality     0.25
        sequence        0.15   ← reduzir para 0.10
        contamination   0.10   ← aumentar para 0.20
        pydantic        0.10
    """
    ACCEPT_THRESHOLD = 0.85
    FALLBACK_THRESHOLD = 0.55
```

### Tabela de impacto nos cenários

| Cenário | Score v2 | Score v3 | Routing v2 | Routing v3 |
|---------|----------|----------|------------|------------|
| Questão perfeita | 1.00 | 1.00 | accept | accept |
| Contaminada, boas alts | 0.90 | 0.80 | **accept** | **fallback** |
| Sem 5 alts, limpa | 0.80 | 0.80 | fallback | fallback |
| Placeholder em alt | 0.75 | 0.65 | fallback | fallback |
| Dead letter (múltiplos) | 0.30 | 0.30 | dead_letter | dead_letter |

### References

- [Source: confidence_scorer.py:38-48] — docstring com pesos atuais
- [Source: confidence_scorer.py:95-101] — `_score_alt_count` (não muda)
- [Source: confidence_scorer.py:103-110] — `_score_text_quality` (0.20→0.15)
- [Source: confidence_scorer.py:145-151] — `_score_sequence` (0.15→0.10)
- [Source: confidence_scorer.py:153-159] — `_score_contamination` (0.10→0.20)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
Redistributed weights (text_quality 0.20->0.15, sequence 0.15->0.10, contamination 0.10->0.20). Added raw-alternatives-in-enunciado detection. Contaminated questions now score 0.80 (fallback). 4 new tests pass.

### File List
- `src/enem_ingestion/confidence_scorer.py`
- `tests/test_confidence_scorer.py`
