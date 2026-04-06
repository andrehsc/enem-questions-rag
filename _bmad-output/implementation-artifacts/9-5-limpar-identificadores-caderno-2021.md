# Story 9.5: Limpar Identificadores de Caderno (2021)

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero que artefatos de OCR dos cadernos 2021 (logotipos ENEM e headers de caderno) sejam removidos do texto extraído,
Para que o enunciado não contenha identificadores de página/caderno irrelevantes.

## Acceptance Criteria (AC)

1. `sanitize_enem_text("texto enem2o02/ continuação")` → `"texto continuação"`
2. `sanitize_enem_text("texto enem2o2/ continuação")` → `"texto continuação"`
3. `sanitize_enem_text("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação")` → `""`
4. `sanitize_enem_text("20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação")` → `""`
5. `has_contamination("texto enem2o02/ test")` → `True`
6. `has_contamination("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação")` → `True`
7. Padrões existentes do sanitizer não são afetados (regressão)
8. Testes unitários para cada novo padrão

## Tasks / Subtasks

- [ ] Task 1: Adicionar padrão para header LC sem "Página" (AC: 3, 4)
  - [ ] 1.1 Em `text_sanitizer.py:_init_patterns()`, adicionar a `_header_patterns`:
    ```python
    # Header LC sem "Página" no final (formato 2021)
    # "6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação"
    # "20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação"
    r'\d+\s+(?:LC|MT|CN|CH)\s*-\s*\d+[°ºo]?\s*dia\s*\|\s*Caderno\s*\d+\s*-\s*(?:AZUL|AMARELO|AMARELA|BRANCO|BRANCA|VERDE|ROSA|CINZA)\s*-\s*\d*[aª]?\s*(?:Aplicação|Aplicacao)',
    ```
  - [ ] 1.2 Verificar que o padrão existente (com "Página" obrigatório) não conflita:
    ```python
    # Existente (linha 37): exige "Página N" no final
    r'(?:LC|MT|CN|CH)\s*-\s*\d+[°ºo]?\s*dia\s*\|\s*Caderno\s*\d+.*?(?:Página|Pagina)\s*\d+',
    # Novo: não exige "Página", mas precisa de COR e "Aplicação"
    ```

- [ ] Task 2: Adicionar padrão para OCR do logotipo ENEM com "o" (AC: 1, 2)
  - [ ] 2.1 Em `text_sanitizer.py:_init_patterns()`, adicionar a `_header_patterns_nocase`:
    ```python
    # OCR do logotipo ENEM com "o" substituindo "0" (2021)
    # "enem2o02/", "enem2o2/"
    r'enem\d*o+\d*/?',
    ```
  - [ ] 2.2 Verificar que o padrão existente para OCR artifacts (linha 55) não já cobre:
    ```python
    # Existente: r'enenn?m[\W\d]*\d+/?'
    # NÃO cobre "enem2o02/" porque [\W\d] não inclui "o" (é letra, não \W nem \d)
    ```
  - [ ] 2.3 Alternativa: ampliar o padrão existente para incluir caracteres OCR comuns:
    ```python
    # Opção A: padrão separado (mais legível)
    r'enem\d*o+\d*/?',
    # Opção B: ampliar existente (mais abrangente)
    r'enenn?m[\W\do]*\d+/?',  # adicionar "o" à classe de caracteres
    ```
    **Decisão**: Opção B (ampliar existente) — menos padrões, mais robusto para futuros OCR artifacts.

- [ ] Task 3: Garantir detecção em `has_contamination()` (AC: 5, 6)
  - [ ] 3.1 Verificar que `has_contamination()` já itera `_header_patterns` e `_header_patterns_nocase` — **sim, linhas 173-178**
  - [ ] 3.2 Os novos padrões adicionados nas tasks 1 e 2 serão automaticamente verificados por `has_contamination()` sem mudança adicional

- [ ] Task 4: Testes (AC: 7, 8)
  - [ ] 4.1 Em `tests/test_text_sanitizer.py`, adicionar testes parametrizados:
    ```python
    @pytest.mark.parametrize("input_text,expected", [
        ("texto enem2o02/ continuação", "texto continuação"),
        ("texto enem2o2/ continuação", "texto continuação"),
        ("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação", ""),
        ("20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação", ""),
        ("15 CN - 2º dia | Caderno 5 - AMARELO - 1ª Aplicação", ""),
    ])
    def test_sanitize_caderno_2021_artifacts(input_text, expected):
        assert sanitize_enem_text(input_text).strip() == expected
    ```
  - [ ] 4.2 Testes de `has_contamination()`:
    ```python
    def test_has_contamination_enem_ocr_logo():
        assert TextSanitizer().has_contamination("texto enem2o02/ test")
    def test_has_contamination_lc_header_2021():
        assert TextSanitizer().has_contamination("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação")
    ```
  - [ ] 4.3 Testes de regressão: padrões existentes ainda funcionam:
    ```python
    def test_existing_headers_still_removed():
        assert sanitize_enem_text("NEM2024 17 texto").strip() == "texto"
        assert sanitize_enem_text("LC - 1º dia | Caderno 1 - AZUL - Página 5").strip() == ""
    ```

## Dev Notes

### Problema

PDFs de 2021 produzem artefatos de OCR não cobertos pelo sanitizer atual:

1. **Logotipo ENEM lido como texto**: OCR interpreta o logo circular como "enem2o02/" ou "enem2o2/" (com "o" minúsculo no lugar de "0")
2. **Header de caderno sem "Página"**: O padrão LC existente exige `(?:Página|Pagina)\s*\d+` no final, mas o 2021 tem formato `N LC - Nº dia | Caderno N - COR - Nª Aplicação` sem "Página"

### Padrões existentes no sanitizer (linha 30-56)

```python
# _header_patterns (case-insensitive):
r'(?:LC|MT|CN|CH)\s*-\s*\d+[°ºo]?\s*dia\s*\|\s*Caderno\s*\d+.*?(?:Página|Pagina)\s*\d+'
#                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                                              EXIGE "Página N" — não match 2021

# _header_patterns_nocase:
r'enenn?m[\W\d]*\d+/?'
#        ^^^^^^ [\W\d] — não inclui "o" (letra), falha em "enem2o02/"
```

### Escopo

Do relatório `relatorio-extracao-completo-2026-04-06.md`:
- Q6 (2021 CD1): contém `enem2o02/` e `6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação`
- Q44 (2021 CD1): contém `enem2o2/` e `20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação`
- 4 instâncias no total (apenas 2021 Dia 1 foi processado até agora)
- Potencialmente mais quando 2021 Dia 2 for processado

### References

- [Source: text_sanitizer.py:30-56] — padrões atuais de headers
- [Source: text_sanitizer.py:156-182] — `has_contamination()`
- [Relatório: relatorio-extracao-completo-2026-04-06.md, linhas 4369-4420] — Q6 e Q44 com artefatos

## Dev Agent Record

### Agent Model Used
(pending)

### Completion Notes List
(pending)

### File List
(pending)
