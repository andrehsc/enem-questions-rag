# Story 8.6: Pipeline de Validação e Relatório de Qualidade

Status: pending

## Story

Como desenvolvedor,
Quero um script de auditoria e relatório automático de qualidade pós-extração,
Para medir o impacto das melhorias e detectar regressões.

## Acceptance Criteria (AC)

1. Script `scripts/audit_extraction_quality.py` com breakdown por ano/dia/caderno/extrator
2. Métricas: % placeholders, % headers residuais, % cascata, % cid tokens, taxa deduplicação
3. Targets configuráveis: 0% placeholders, 0% headers, 0% cascata, 0% cid, ~80% dedup
4. Relatório markdown gerado automaticamente após cada execução
5. Golden set atualizado com alternativas e gabaritos validados manualmente (resolve deferred items Epic 7)

## Tasks / Subtasks

- [ ] Task 1: Criar script de auditoria (AC: 1, 2)
  - [ ] 1.1 Criar `scripts/audit_extraction_quality.py`:
    ```python
    def audit_questions(conn) -> AuditReport:
        """Auditar todas as questões no banco."""
        questions = fetch_all_questions(conn)
        report = AuditReport()

        for q in questions:
            issues = detect_issues(q)
            report.add(q, issues)

        return report
    ```
  - [ ] 1.2 Função `detect_issues(question) -> List[str]` que verifica:
    - `"placeholder"`: alternativa contém `[Alternative not found]`
    - `"header_pollution"`: texto contém padrão de header ENEM (regex de TextSanitizer)
    - `"indesign_artifact"`: texto contém chars duplicados InDesign
    - `"cid_token"`: texto contém `(cid:XX)`
    - `"cascade"`: alt_A.length > 3 * alt_E.length E alt_B in alt_A
    - `"markdown_artifact"`: texto contém `## **`
    - `"short_enunciado"`: enunciado < 50 chars
    - `"missing_alternatives"`: < 5 alternativas
  - [ ] 1.3 Breakdown por dimensões:
    - Por ano: 2020, 2021, 2022, 2023, 2024
    - Por dia: Dia 1, Dia 2
    - Por caderno: CD1-CD12
    - Por extrator: pdfplumber, pymupdf4llm
    - Por issue type: cada tipo acima
  - [ ] 1.4 Métricas agregadas:
    - Total questões, questões limpas, questões com warnings, questões com erros, inutilizáveis
    - % de cada tipo de issue
    - Top-10 padrões de poluição encontrados
- [ ] Task 2: Targets configuráveis (AC: 3)
  - [ ] 2.1 Dataclass `QualityTargets`:
    ```python
    @dataclass
    class QualityTargets:
        max_placeholder_rate: float = 0.0
        max_header_rate: float = 0.0
        max_cascade_rate: float = 0.0
        max_cid_rate: float = 0.0
        min_clean_rate: float = 0.90
        min_dedup_rate: float = 0.80
    ```
  - [ ] 2.2 Comparação: cada métrica vs target → PASS/FAIL com cores
- [ ] Task 3: Geração de relatório markdown (AC: 4)
  - [ ] 3.1 Output: `reports/quality-audit-{YYYY-MM-DD}.md`
  - [ ] 3.2 Seções do relatório:
    ```markdown
    # Relatório de Qualidade — Extração ENEM
    > Data: {timestamp}
    > Total questões: {N}

    ## Resumo
    | Métrica | Valor | Target | Status |
    |---------|-------|--------|--------|

    ## Breakdown por Ano
    ...

    ## Breakdown por Extrator
    ...

    ## Top-10 Padrões de Poluição
    ...

    ## Questões Mais Problemáticas
    ...
    ```
  - [ ] 3.3 CLI: `python scripts/audit_extraction_quality.py --db-url $DATABASE_URL --output reports/`
- [ ] Task 4: Atualizar golden set (AC: 5)
  - [ ] 4.1 Atualizar `tests/fixtures/golden_set.json`:
    - Preencher `alternatives` (atualmente `[]` em todas 50)
    - Preencher `correct_answer` (atualmente `null` em todas 50)
    - Corrigir `has_images` inconsistentes
  - [ ] 4.2 Adicionar questões de "Redação-suporte" se disponíveis (deferred Epic 7)
  - [ ] 4.3 Atualizar thresholds em `tests/test_golden_set.py`:
    - Após Stories 8.1-8.3: assertivas mais rigorosas (acurácia >= 0.95, alternativas completas >= 0.95)
  - [ ] 4.4 Resolver deferred items do Epic 7 no `deferred-work.md`:
    - `[x] Golden set sem CI pipeline` → permanecer deferred (sem CI)
    - `[x] Golden set: alternatives e gabarito vazios` → resolvido pelo Task 4.1
    - `[x] Golden set: has_images inconsistente` → resolvido pelo Task 4.1
    - `[x] Golden set: falta área Redação-suporte` → resolvido pelo Task 4.2 se possível
- [ ] Task 5: Testes (AC: 1)
  - [ ] 5.1 Teste: script de auditoria roda sem erros com mock de questões
  - [ ] 5.2 Teste: detect_issues identifica cada tipo de issue corretamente
  - [ ] 5.3 Teste: relatório markdown é gerado com formato válido
  - [ ] 5.4 Teste: comparação vs targets produz PASS/FAIL corretamente

## Dev Notes

### Deferred items do Epic 7 que esta story resolve

De `_bmad-output/implementation-artifacts/deferred-work.md`:

- **Golden set: alternatives e gabarito vazios** — Todas 50 questões têm alternatives=[] e correct_answer=null. Extrator embute alternativas no texto. Curadoria manual necessária.
- **Golden set: has_images inconsistente** — Questões com imagens referenciadas no context_text têm has_images=false.
- **Golden set: falta área Redação-suporte** — AC1 pede 10 questões Redação-suporte; não há no dataset.

### Formato do golden_set.json atual

```json
{
  "questions": [
    {
      "id": "gs-001",
      "year": 2023,
      "day": 1,
      "caderno": "CD1",
      "question_number": 1,
      "subject": "linguagens",
      "context_text": "...",
      "question_text": "...",
      "alternatives": [],  // ← VAZIO — preencher
      "correct_answer": null,  // ← NULL — preencher
      "has_images": false,
      "has_formulas": false,
      "notes": "..."
    }
  ]
}
```

### Dependências

- Última story do Epic 8 — mede o impacto de todas as anteriores
- Depende de 8.1 (regex patterns para detect_issues)
- Golden set update é independente (pode ser feito em paralelo)

### Anti-Patterns a Evitar

- NÃO hardcodar targets — usar dataclass configurável
- NÃO gerar relatório para stdout — sempre salvar em arquivo markdown
- NÃO alterar golden set sem verificação manual contra PDF original

### References

- [Source: tests/fixtures/golden_set.json] — golden set atual (50 questões, sem alternativas)
- [Source: tests/test_golden_set.py] — testes de benchmark atuais
- [Source: deferred-work.md] — deferred items Epic 7
- [Source: PLAN-extraction-quality-improvements.md] — métricas e targets

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
