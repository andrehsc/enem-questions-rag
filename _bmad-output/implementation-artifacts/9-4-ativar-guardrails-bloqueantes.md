# Story 9.4: Ativar Guardrails como Bloqueantes

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero que questões que falharam na validação dos guardrails estruturais sejam penalizadas no scoring,
Para que questões estruturalmente inválidas não sejam aceitas no banco.

## Acceptance Criteria (AC)

1. Questão com `VALIDATION_FAILED` dos guardrails tem field `guardrails_failed=True` no dataclass
2. Confidence scorer penaliza questões com `guardrails_failed` (score reduzido)
3. Questão com guardrails `SUCCESS` não é afetada (backward compatible)
4. Logger registra quando questão é penalizada por guardrails
5. Testes unitários para ambos os cenários (SUCCESS e VALIDATION_FAILED)

## Tasks / Subtasks

- [ ] Task 1: Propagar status de guardrails para o dataclass Question (AC: 1)
  - [ ] 1.1 Em `parser.py`, adicionar campo ao dataclass `Question`:
    ```python
    @dataclass
    class Question:
        number: int
        text: str
        alternatives: List[str]
        subject: str = ""
        metadata: Optional[dict] = None
        guardrails_failed: bool = False  # NOVO
    ```
  - [ ] 1.2 Em `_extract_alternatives_with_context()` (linha ~527-547), quando `VALIDATION_FAILED`:
    ```python
    elif guardrails_result['status'] == 'VALIDATION_FAILED':
        recovery = guardrails_result['recovery_strategy']
        risk_level = guardrails_result['guardrails_applied']['risk_level']
        self._last_guardrails_metrics['validation_failures'] += 1
        logger.warning(
            f"Q{question_number} Guardrails BLOCKED: risk={risk_level}, "
            f"strategy={recovery['action']}"
        )
        guardrails_failed = True  # Propagar para Question
    ```
  - [ ] 1.3 Retornar `guardrails_failed` junto com as alternatives (via tuple ou set no Question)
  - [ ] 1.4 Em `parse_questions()` (linha ~289-295), propagar o flag para o Question dataclass

- [ ] Task 2: Penalizar no scorer (AC: 2, 3)
  - [ ] 2.1 Em `confidence_scorer.py`, integrar check de guardrails no `_score_contamination()`:
    ```python
    def _score_contamination(self, question: Question, issues: List[str]) -> float:
        """0.20 — no contamination + guardrails passed."""
        # Check guardrails
        if getattr(question, 'guardrails_failed', False):
            issues.append("guardrails_validation_failed")
            return 0.0

        # Check text contamination (existente)
        full_text = (question.text or "") + " " + " ".join(question.alternatives)
        if self._sanitizer.has_contamination(full_text):
            issues.append("contamination_detected")
            return 0.0
        return 0.20
    ```
  - [ ] 2.2 Alternativa: criar método separado `_score_guardrails()` com peso próprio
    - Pro: separação de concerns
    - Con: redistribuir pesos novamente
    - **Decisão: integrar no `_score_contamination()` reutilizando os 0.20 pontos** (simples, sem mudar pesos)

- [ ] Task 3: Log e observabilidade (AC: 4)
  - [ ] 3.1 Adicionar log em `_score_contamination()` quando guardrails_failed:
    ```python
    logger.info("[GUARDRAILS_BLOCKED] Q%d — guardrails_failed, score penalty applied", question.number)
    ```

- [ ] Task 4: Testes (AC: 5)
  - [ ] 4.1 Teste: Question com `guardrails_failed=True` → contamination score = 0.0, total < 0.85
  - [ ] 4.2 Teste: Question com `guardrails_failed=False` (padrão) → sem impacto
  - [ ] 4.3 Teste: Question sem o attribute (backward compat) → `getattr` retorna False, sem impacto
  - [ ] 4.4 Teste de integração: parser.py com mock de guardrails retornando VALIDATION_FAILED

## Dev Notes

### Problema

Em `parser.py:527-547`, quando guardrails retorna `VALIDATION_FAILED`:

```python
elif guardrails_result['status'] == 'VALIDATION_FAILED':
    recovery = guardrails_result['recovery_strategy']
    risk_level = guardrails_result['guardrails_applied']['risk_level']
    # ... metrics logging ...
    pass  # ← IGNORA o resultado, segue com enhanced extractor
```

O `pass` faz com que a falha de validação seja **completamente ignorada**. A questão segue o pipeline normal e pode ser aceita com score alto.

### Abordagem escolhida: Flag no dataclass + penalização no scorer

Em vez de **bloquear** diretamente no parser (que quebraria o fluxo), propagar a informação via campo `guardrails_failed` e deixar o scorer decidir o roteamento. Isso é mais flexível e testável.

### Impacto no score

Questão com guardrails falho + contaminação e tudo mais OK:
- alt_count=0.20 + text_quality=0.15 + alt_quality=0.25 + sequence=0.10 + **contamination=0.00** + pydantic=0.10
- Total = **0.80 → FALLBACK** (correto)

### Backward compatibility

`getattr(question, 'guardrails_failed', False)` garante que Questions criadas sem o campo (pelo pymupdf4llm extractor direto, sem parser.py) não são afetadas.

### References

- [Source: parser.py:527-547] — `VALIDATION_FAILED` handler (atualmente `pass`)
- [Source: parser.py:463-470] — `_extract_alternatives_with_context()` entry point
- [Source: confidence_scorer.py:153-159] — `_score_contamination()` (ponto de integração)
- [Source: enem_structure_spec.py:1-80] — `EnemStructuralGuardrailsController`

## Dev Agent Record

### Agent Model Used
(pending)

### Completion Notes List
(pending)

### File List
(pending)
