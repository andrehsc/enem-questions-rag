# Story 8.1: Text Sanitizer Robusto

Status: review

## Story

Como desenvolvedor,
Quero uma camada de sanitização pós-extração que limpe headers, footers, artefatos InDesign, tokens (cid:XX) e markdown residual,
Para que o texto armazenado no banco esteja limpo e utilizável para RAG.

## Acceptance Criteria (AC)

1. Regex remove headers ENEM em todas variantes (CADERNO X, NEM2024, Página NN, áreas temáticas) em qualquer posição do texto
2. Regex remove artefatos InDesign (caracteres duplicados PP22__, ..iinnddbb, timestamps duplicados)
3. Tokens (cid:XX) substituídos por espaço e espaços múltiplos colapsados
4. Artefatos markdown (## **, **, #) removidos do texto final
5. TextSanitizer como singleton (não re-instanciar EnemTextNormalizer a cada chamada)
6. Testes com exemplos reais de cada categoria de poluição (mínimo 15 test cases)

## Tasks / Subtasks

- [x] Task 1: Criar `src/enem_ingestion/text_sanitizer.py` (AC: 1, 2, 3, 4, 5)
  - [x] 1.1 Classe `TextSanitizer` com instância singleton via `_instance` class var
  - [x] 1.2 Método `sanitize(text: str) -> str` — entry point principal, encadeia todos os regex
  - [x] 1.3 Regex para headers de página ENEM — todas variantes:
    ```python
    # Padrões de cabeçalho/rodapé ENEM
    HEADER_PATTERNS = [
        r'\d+[°º]?\s*DIA\s*[•·.]\s*CADERNO\s*\d+\s*[•·.]\s*\w+\s*[•·.]\s*\w+',  # "2º DIA • CADERNO 8 • VERDE • MAT"
        r'DERNO\s*\d+\s*[.\s]*\w+\s*-',  # "DERNO 1 . AZUL-"
        r'(?:NEM|ENEM)\d{4}\s*\d*',  # "NEM2024 17", "ENEM20E 4"
        r'ENEM20[A-Z]\s*\d*',  # "ENEM20E 26"
        r'4202\s*MENE',  # "4202 MENE" (reversed)
        r'MENE\s*\d{4}',  # "MENE 2024"
        r'(?:LC|MT|CN|CH)\s*-\s*\d+[°º]?\s*dia\s*\|\s*Caderno\s*\d+.*?(?:Página|Pagina)\s*\d+',
        r'Página\s*\d+',  # "Página 25" isolado
        r'Pagina\s*\d+',
        r'\d+\s*[.-]\s*(?:ROSA|AZUL|AMARELO|AMARELA|BRANCO|BRANCA|VERDE|CINZA)\s*-?\s*\d*[aª]?\s*(?:Aplicação|Aplicacao)?',
    ]
    ```
  - [x] 1.4 Regex para áreas temáticas em QUALQUER posição (não só final)
  - [x] 1.5 Regex para artefatos InDesign — heurística de caracteres duplicados
  - [x] 1.6 Regex para tokens (cid:XX)
  - [x] 1.7 Regex para artefatos markdown
  - [x] 1.8 Método `sanitize_alternative(text: str) -> str` — limpeza mais agressiva para alternativas individuais (strip trailing pollution)
  - [x] 1.9 Função de conveniência `sanitize_enem_text(text: str) -> str` usando singleton
- [x] Task 2: Integrar no pipeline de extração (AC: 1, 2, 3, 4)
  - [x] 2.1 `pymupdf4llm_extractor.py:_build_question()` (linha ~225) — chamar `sanitize_enem_text()` APÓS `normalize_enem_text()` e ANTES de `_extract_alternatives()`
  - [x] 2.2 `pymupdf4llm_extractor.py:_build_question()` — chamar `sanitize_alternative()` em cada alternativa após extração
  - [x] 2.3 `parser.py:_clean_question_text()` (linha ~929) — chamar `sanitize_enem_text()` como camada adicional
  - [x] 2.4 Se `azure_di_fallback.py` existir, integrar sanitizer lá também — N/A (arquivo não existe)
- [x] Task 3: Refatorar singleton do normalizer (AC: 5)
  - [x] 3.1 Em `text_normalizer.py:normalize_enem_text()` (linha 196), usar instância singleton em vez de criar novo `EnemTextNormalizer()` a cada chamada
- [x] Task 4: Testes (AC: 6)
  - [x] 4.1 Criar `tests/test_text_sanitizer.py`
  - [x] 4.2 Testes parametrizados com exemplos reais — 33 test cases cobrindo todas categorias
  - [x] 4.3 Teste de idempotência: `sanitize(sanitize(text)) == sanitize(text)`
  - [x] 4.4 Teste de singleton: `TextSanitizer() is TextSanitizer()`

## Dev Notes

### Arquitetura: Normalizer vs Sanitizer

```
PDF → pymupdf4llm.to_markdown()
    → normalize_enem_text()     ← encoding/mojibake (text_normalizer.py)
    → sanitize_enem_text()      ← content-level cleaning (text_sanitizer.py) [NOVO]
    → _extract_alternatives()
    → sanitize_alternative()    ← per-alternative cleaning [NOVO]
    → Question dataclass
```

O `text_normalizer.py` trata encoding (mojibake, Unicode NFC, control chars). O novo `text_sanitizer.py` trata conteúdo (headers, InDesign, cid, markdown). São camadas complementares, NÃO substitutas.

### Limitações atuais do text_normalizer.py

- Linha 56-74: Só limpa formato `LC - N° dia | Caderno...` e caracteres de controle
- NÃO remove: headers ENEM (1.261 ocorrências), artefatos InDesign (~1.200), tokens cid (2.829 linhas), markdown (1.050), timestamps duplicados, áreas temáticas (186)

### Limitações do parser._clean_question_text()

- Linha 964-967: Strip de headers só no FINAL do texto (`.*$` anchored)
- Headers no MEIO do texto (page breaks) não são removidos
- Não trata InDesign ou timestamps duplicados

### Contagens de erros (do diagnóstico)

| Padrão | Ocorrências |
|--------|-------------|
| `CADERNO X` / `DERNO X` | 1.261 |
| `Aplicação` | 594 |
| `NEM2024` / `ENEM20E` | 685 |
| `Página` | 167 |
| Áreas temáticas | 186 |
| InDesign (chars duplicados) | ~1.200 |
| (cid:XX) | 2.829 linhas |
| `## **` markdown | 1.050 |
| Timestamps duplicados | presentes |

### Anti-Patterns a Evitar

- NÃO modificar `text_normalizer.py` (manter como camada de encoding)
- NÃO usar regex gananciosos (`.+` em vez de `.+?`) que comam texto legítimo
- NÃO remover "CADERNO" quando aparece em contexto literário (apenas em padrões de header)
- NÃO remover números isolados que possam ser parte de alternativas matemáticas

### Dependências

- Nenhuma dependência de outra story (8.1 é a fundação)
- Stories 8.2, 8.3, 8.5 dependem desta

### Project Structure Notes

- Novo: `src/enem_ingestion/text_sanitizer.py`
- Novo: `tests/test_text_sanitizer.py`
- Modificado: `src/enem_ingestion/pymupdf4llm_extractor.py`
- Modificado: `src/enem_ingestion/parser.py`
- Modificado: `src/enem_ingestion/text_normalizer.py` (singleton)

### References

- [Source: text_normalizer.py] — encoding layer, cleanup_patterns lines 56-74
- [Source: pymupdf4llm_extractor.py:_build_question] — integration point, line ~225
- [Source: parser.py:_clean_question_text] — legacy cleanup, line 929
- [Source: docs/stories/extraction-quality/PLAN-extraction-quality-improvements.md] — diagnostic data

### Testing Standards

- Testes unitários puros (sem DB, sem PDF)
- Cada regex pattern deve ter pelo menos 2 test cases (match + no-match)
- Exemplos extraídos de `reports/questoes_completas_novo.txt` (linhas reais)
- `python -m pytest tests/test_text_sanitizer.py -v`

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- Manual regex trace identified 3 bugs before test execution:
  1. `[°º]` didn't match plain `o` in `1o DIA` — fixed to `[°ºo]`
  2. InDesign pattern 2 assumed uppercase/lowercase pair alternation — fixed to `(?:[A-Za-z]{2}){3,}`
  3. Markdown `## **` removal left trailing space — fixed with `[ \t]*` prefix

### Completion Notes List
- TextSanitizer singleton via `__new__` + `_init_patterns()`
- 5 header patterns (IGNORECASE) + 4 case-sensitive header patterns + standalone Página
- 6 area patterns + 1 partial boundary pattern
- 4 InDesign patterns (PP prefix, generic doubled-char, trailing iinndd, doubled timestamps)
- cid:XX → space replacement + whitespace collapse
- Markdown `## **` and isolated `**` removal with horizontal whitespace consumption
- `has_contamination()` method for confidence scorer integration (Story 8.3)
- Pipeline integrated: pymupdf4llm_extractor.py lines 23,228,239; parser.py lines 19,951
- Normalizer singleton refactored: text_normalizer.py lines 196-209

### File List
- **New**: `src/enem_ingestion/text_sanitizer.py` — TextSanitizer class (214 lines)
- **New**: `tests/test_text_sanitizer.py` — 33 test cases across 8 test classes (267 lines)
- **Modified**: `src/enem_ingestion/pymupdf4llm_extractor.py` — import + 2 integration points
- **Modified**: `src/enem_ingestion/parser.py` — import + 1 integration point
- **Modified**: `src/enem_ingestion/text_normalizer.py` — singleton refactor

### Review Findings
- Tests need manual execution (Python hangs in Claude Code shell on Windows)
- Run: `python -m pytest tests/test_text_sanitizer.py -v --tb=short`
- All regex patterns verified via manual trace against test expectations
- Standalone `Página\s*\d+` pattern may false-positive on literary page references — acceptable for ENEM extraction context
