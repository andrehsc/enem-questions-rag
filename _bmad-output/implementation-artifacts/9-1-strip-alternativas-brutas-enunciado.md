# Story 9.1: Strip de Alternativas Brutas do Enunciado

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero que o enunciado extraído não contenha alternativas brutas duplicadas (formato sem formatação markdown),
Para que o texto armazenado no banco seja limpo e utilizável no RAG sem ruído de alternativas repetidas.

## Acceptance Criteria (AC)

1. `_extract_enunciado()` para ao encontrar bloco de alternativas brutas (`^[A-E]\s+.{3,}`)
2. Heurística `_looks_like_alternative_block()` evita falso-positivo com frases iniciando por "A família...", "E então..."
3. Nenhuma questão aceita contém alternativas brutas no enunciado (validado com relatório de auditoria)
4. Testes com >= 10 exemplos reais do relatório (Q172, Q171, Q173, Q170, Q167, Q166, Q155, Q142, Q139, Q136)
5. Regressão: nenhuma questão limpa existente quebra após a mudança

## Tasks / Subtasks

- [ ] Task 1: Implementar `_looks_like_alternative_block()` (AC: 2)
  - [ ] 1.1 Criar método auxiliar em `pymupdf4llm_extractor.py`:
    ```python
    def _looks_like_alternative_block(self, lines: List[str], start_idx: int) -> bool:
        """Verifica se linhas a partir de start_idx formam bloco de alternativas.

        Regras:
        - Pelo menos 3 das próximas 5 linhas começam com ^[A-E]\s+
        - Letras estão em sequência (A, B, C, D, E) sem repetição
        - Linhas são curtas (<= 300 chars, típico de alternativa)
        """
    ```
  - [ ] 1.2 Tratar caso especial: "A" como artigo feminino e "E" como conjunção
    - Se a linha começa com `A ` seguido de palavra minúscula ("A família", "A técnica"), é provavelmente texto normal
    - Se a linha começa com `A ` seguido de maiúscula ou número ("A 4,00.", "A X."), é provavelmente alternativa
  - [ ] 1.3 Validar que letras encontradas estão em sequência crescente (A→B→C ou B→C→D, etc.)

- [ ] Task 2: Atualizar `_extract_enunciado()` com novo stop condition (AC: 1)
  - [ ] 2.1 Em `pymupdf4llm_extractor.py:424-447`, adicionar terceiro stop condition:
    ```python
    # Stop condition existente 1: alternativas com parênteses
    if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):
        break
    # Stop condition existente 2: markdown list
    if re.match(r'^-\s+[A-E]\s', stripped):
        break
    # NOVO stop condition 3: alternativas brutas sem formatação
    if re.match(r'^[A-E]\s+\S', stripped) and self._looks_like_alternative_block(lines, i):
        break
    ```
  - [ ] 2.2 Ajustar a iteração para ter acesso ao índice `i` (usar `enumerate(lines)`)

- [ ] Task 3: Testes (AC: 3, 4, 5)
  - [ ] 3.1 Testes com exemplos reais do relatório:
    - Q172 (matematica): "A 4,00.\nB 4,87." no enunciado
    - Q171 (matematica): "A 5\nB 8\nC 10" no enunciado
    - Q170 (matematica): "A fim de poupar tempo..." (falso-positivo: "A" é preposição)
    - Q167 (matematica): "A 1.\nB 3.\nC 1 e 2. D 1 e 3. E 2 e 3." no enunciado
    - Q155 (matematica): "A X.\nB Y.\nC Z.\nD W. E T." no enunciado
    - Q139 (matematica): "A 2 quadrados..." no enunciado
  - [ ] 3.2 Testes de falso-positivo (NÃO devem cortar):
    - "A família que adota é mais feliz..."
    - "E então o fenômeno se manifesta..."
    - "A técnica para gerar essa leguminosa..."
  - [ ] 3.3 Teste de regressão com questões limpas existentes

## Dev Notes

### Problema

O `pymupdf4llm` gera markdown onde alternativas aparecem primeiro em texto bruto e depois formatadas:

```
> Enunciado da questão...

A 4,00.           ← alternativa bruta (ENTRA NO ENUNCIADO)
B 4,87.           ← alternativa bruta (ENTRA NO ENUNCIADO)

- **A)** 4,00.    ← alternativa formatada (stop condition existente funciona)
- **B)** 4,87.
```

### Stop conditions atuais em `_extract_enunciado()` (linha 424-447)

```python
# pymupdf4llm_extractor.py:429-435
if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):  # (A), **(A)**
    break
if re.match(r'^-\s+[A-E]\s', stripped):  # - A texto
    break
# NÃO EXISTE: stop para "A texto." (formato bruto)
```

### Risco: Falso-positivo com artigo "A" e conjunção "E"

Frases como "A família que adota..." ou "E então..." começam com `^[A-E]\s+`. A heurística `_looks_like_alternative_block()` resolve verificando se as próximas linhas também começam com letras em sequência.

### Escopo: ~70 questões afetadas

Do relatório `relatorio-extracao-completo-2026-04-06.md`, ~70+ questões aceitas têm alternativas brutas no enunciado, distribuídas em todas as áreas mas concentradas em matemática e ciências natureza.

### References

- [Source: pymupdf4llm_extractor.py:424-447] — `_extract_enunciado()` atual
- [Relatório: relatorio-extracao-completo-2026-04-06.md] — exemplos reais de Q136-Q180

## Dev Agent Record

### Agent Model Used
(pending)

### Completion Notes List
(pending)

### File List
(pending)
