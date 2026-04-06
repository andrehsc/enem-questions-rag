# Story 8.2: Extração de Alternativas Robusta

Status: pending

## Story

Como desenvolvedor,
Quero corrigir a lógica de splitting de alternativas para eliminar cascata, merge de estratégias e placeholders,
Para que todas as questões tenham 5 alternativas corretas ou sejam roteadas para fallback.

## Acceptance Criteria (AC)

1. Detecção e correção de alternativas em cascata (differencing: se text_A ⊃ text_B ⊃ text_C, extrair por diferença)
2. Merge de estratégias: união de resultados de múltiplas estratégias (se S1 tem A,B,C e S2 tem C,D,E, resultado = A,B,C,D,E)
3. Placeholder [Alternative not found] nunca salvo no banco de dados
4. False-positive filter substituído por heurística baseada em comprimento/estrutura (remover filtro de palavras PT-BR)
5. Suporte a formato 2022-2023 de dupla-letra (AA, BB, CC, DD, EE)
6. Testes cobrindo: cascata, merge, alternativas matemáticas curtas, formato dupla-letra, alternativas inline

## Tasks / Subtasks

- [ ] Task 1: Detecção e correção de cascata (AC: 1)
  - [ ] 1.1 Método `_detect_cascade(alternatives: Dict[str, str]) -> bool` em `EnhancedAlternativeExtractor`
    - Heurística: se `text_A` contém `text_B` que contém `text_C`, é cascata
    - Verificar com `text_B in text_A and text_C in text_B`
  - [ ] 1.2 Método `_fix_cascade(alternatives: Dict[str, str]) -> Dict[str, str]`
    - Differencing reverso: começar pelo E (geralmente correto), extrair D = text_D[:-len(text_E)].strip(), etc.
    - Edge case: quando limites não são exatos, usar SequenceMatcher para alinhar
  - [ ] 1.3 Integrar detecção no fluxo: se cascata detectada após extração, aplicar fix antes de retornar
- [ ] Task 2: Merge de estratégias (AC: 2)
  - [ ] 2.1 Modificar `EnhancedAlternativeExtractor.extract_alternatives()` (linhas 380-404):
    - Atualmente: roda todas as estratégias, pega a de maior confiança
    - Novo: roda todas, coleta resultados por letra (A-E), se nenhuma individual tem 5, tentar merge
  - [ ] 2.2 Merge logic:
    ```python
    def _merge_strategies(results: List[ExtractionResult]) -> Dict[str, str]:
        merged = {}
        for letter in 'ABCDE':
            candidates = [(r.alternatives[letter], r.confidence)
                         for r in results if letter in r.alternatives]
            if candidates:
                merged[letter] = max(candidates, key=lambda x: x[1])[0]
        return merged
    ```
  - [ ] 2.3 Se merge produz 5 alternativas onde nenhuma estratégia individual conseguiu, usar merge com confiança = min(confiança dos componentes)
- [ ] Task 3: Remover false-positive filter (AC: 4)
  - [ ] 3.1 Em `alternative_extractor.py:StandardPatternStrategy._is_likely_false_positive()` (linhas 156-172):
    - REMOVER checagem de palavras PT-BR: "este", "esta", "não há", "pode ser", "sobre o tema"
    - MANTER limite de comprimento mas aumentar de 200 para 500 chars
    - MANTER checagem de >2 sentenças mas aumentar para >5
  - [ ] 3.2 Substituir por heurística estrutural:
    - Rejeitar se alternativa é substring exata do enunciado com >100 chars
    - Rejeitar se alternativa contém "QUESTÃO" ou "QUESTAO" (provável bleed de questão adjacente)
- [ ] Task 4: Eliminar placeholders (AC: 3)
  - [ ] 4.1 Em `parser.py` (linhas 316-318): REMOVER geração de `[Alternative not found]`
  - [ ] 4.2 Em `parser.py` (linhas 524-528 e 560-565): REMOVER padding com placeholder
  - [ ] 4.3 Em `pymupdf4llm_extractor.py:_extract_alternatives_simple()`: NÃO paddar
  - [ ] 4.4 Se <5 alternativas, retornar o que foi encontrado — o confidence scorer roteará para fallback
  - [ ] 4.5 Script de limpeza para DB existente: `UPDATE enem_questions.alternatives SET text = NULL WHERE text LIKE '%[Alternative not found]%'`
- [ ] Task 5: Alternativas matemáticas curtas (AC: 1, 6)
  - [ ] 5.1 Em `MathematicalStrategy` e `_extract_alternatives_simple()`: aceitar alternativas de 1-2 chars se forem números, fórmulas ou símbolos
  - [ ] 5.2 Regex para validar alt curta: `r'^[\d\.\,\+\-\*\/\=\s\π√\{\}\(\)a-zA-Z]+$'`
  - [ ] 5.3 Mínimo de comprimento: 1 char para alternatives com conteúdo matemático
- [ ] Task 6: Formato dupla-letra 2022-2023 (AC: 5)
  - [ ] 6.1 Nova estratégia `DoubledLetterStrategy` (ou adaptar de `parser.py:_extract_alternatives_2022_2023`, linha ~807):
    ```python
    DOUBLED_LETTER_RE = r'(?:^|\n)\s*(AA|BB|CC|DD|EE)\s*[).\-]?\s*(.+?)(?=\n\s*(?:AA|BB|CC|DD|EE)\s|\n\n|$)'
    SPACED_DOUBLE_RE = r'(?:^|\n)\s*([A-E])\s+\1\s*[).\-]?\s*(.+?)(?=\n\s*[A-E]\s+[A-E]\s|\n\n|$)'
    ```
  - [ ] 6.2 Mapeamento: AA→A, BB→B, CC→C, DD→D, EE→E
  - [ ] 6.3 Registrar como estratégia no `EnhancedAlternativeExtractor`
- [ ] Task 7: Pré-limpeza do bloco (AC: 1, 2)
  - [ ] 7.1 Antes de qualquer estratégia, chamar `sanitize_enem_text()` (de Story 8.1) no bloco de texto
  - [ ] 7.2 Isso remove headers/footers que quebram o regex de alternativas
- [ ] Task 8: Testes (AC: 6)
  - [ ] 8.1 `tests/test_alternative_extractor_v2.py` (ou estender existente)
  - [ ] 8.2 Teste cascata: input com A⊃B⊃C⊃D⊃E → 5 alternativas corretas por differencing
  - [ ] 8.3 Teste merge: S1 acha A,B,C + S2 acha C,D,E → merge = A,B,C,D,E
  - [ ] 8.4 Teste sem placeholder: <5 alternativas → retorna o que encontrou, sem padding
  - [ ] 8.5 Teste math curta: "A) π  B) 2π  C) 3π  D) 4π  E) 5π" → 5 alternativas
  - [ ] 8.6 Teste dupla-letra: "AA resposta1\nBB resposta2\n..." → A-E mapeados
  - [ ] 8.7 Teste inline: "A 7. B 8. C 9. D 10. E 11." → 5 alternativas

## Dev Notes

### Arquitetura atual do alternative_extractor.py

```
EnhancedAlternativeExtractor.extract_alternatives(text)
├── StandardPatternStrategy → 5 regex patterns, best-match
├── MultilinePatternStrategy → line-by-line walk
├── MathematicalStrategy → permissive for short/numeric
└── → Pick one with highest confidence (NO MERGE today)
```

### Problema: _is_likely_false_positive() é destrutivo

Localização: `alternative_extractor.py` linhas 156-172

Rejeita alternativas contendo: "este", "esta", "não há", "pode ser", "sobre o tema"

Essas palavras aparecem em alternativas ENEM legítimas constantemente. Exemplo:
- `"A) Esta análise demonstra a influência..."` → rejeitado por conter "esta"
- `"C) Não há contradição entre os textos..."` → rejeitado por conter "não há"

### Problema: >= 3 alternativas aceitas como válidas

Localização: `pymupdf4llm_extractor.py:_extract_alternatives_simple()` linhas 279-280

O markdown list pattern retorna com apenas 3 matches, perdendo 2 alternativas silenciosamente.

### Contagens de erros (do diagnóstico)

| Problema | Ocorrências |
|----------|-------------|
| Alternativas em cascata (>300 chars) | 1.782 |
| [Alternative not found] total | 918 |
| - Alt E | 562 (61%) |
| - Alt D | 144 (16%) |
| - Alt B | 135 (15%) |
| - Alt C | 41 (4%) |
| - Alt A | 36 (4%) |
| Alt A com >500 chars (enunciado inteiro) | 439 |

### Dependências

- Depende de Story 8.1 (TextSanitizer) para pré-limpeza antes da extração
- Story 8.3 (Confidence Scorer v2) depende desta

### Anti-Patterns a Evitar

- NÃO remover totalmente o false-positive filter — apenas substituir palavras PT-BR por heurística estrutural
- NÃO assumir que alternativa E é sempre correta na cascata (pode estar poluída com footer)
- NÃO usar merge se uma única estratégia já achou 5 — merge é fallback

### References

- [Source: alternative_extractor.py:156-172] — false positive filter to remove
- [Source: alternative_extractor.py:380-404] — current strategy selection (no merge)
- [Source: pymupdf4llm_extractor.py:260-287] — _extract_alternatives_simple()
- [Source: parser.py:316-318] — placeholder generation
- [Source: parser.py:524-528, 560-565] — more placeholder generation
- [Source: parser.py:807+] — 2022-2023 doubled letter logic to port

### Testing Standards

- Usar exemplos reais extraídos de `reports/questoes_completas_novo.txt`
- Cada tipo de erro deve ter test case com input/output exato
- `python -m pytest tests/test_alternative_extractor_v2.py -v`

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
