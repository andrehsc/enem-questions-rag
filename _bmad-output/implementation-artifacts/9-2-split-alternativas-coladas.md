# Story 9.2: Split de Alternativas Coladas na Mesma Linha

Status: ready-for-dev

## Story

Como desenvolvedor,
Quero que alternativas compactadas na mesma linha (ex: "D texto1. E texto2.") sejam corretamente separadas,
Para que cada alternativa A-E tenha seu conteúdo isolado sem contaminar a próxima.

## Acceptance Criteria (AC)

1. `"D W. E T."` → D="W.", E="T."
2. `"C 1 e 2. D 1 e 3. E 2 e 3."` → C="1 e 2.", D="1 e 3.", E="2 e 3."
3. `"D 52. E 60."` → D="52.", E="60."
4. `"C 5,00. D 5,83."` → C="5,00.", D="5,83."
5. `"D 10[4] E 10[6]"` → D="10[4]", E="10[6]"
6. Alternativa legítima com letra maiúscula no meio (ex: "Platão E Aristóteles") NÃO é splitada
7. Testes com >= 15 exemplos reais do relatório
8. Regressão: nenhuma alternativa limpa existente quebra

## Tasks / Subtasks

- [ ] Task 1: Criar `_split_merged_alternatives()` (AC: 1, 2, 3, 4, 5)
  - [ ] 1.1 Novo método em `alternative_extractor.py`:
    ```python
    def _split_merged_alternatives(
        self, alternatives: Dict[str, str]
    ) -> Dict[str, str]:
        """Detecta e separa alternativas coladas na mesma linha.

        Detecta padrões como "texto1. E texto2" dentro do texto da alternativa D,
        onde o conteúdo de E vazou para dentro de D.
        """
    ```
  - [ ] 1.2 Lógica de split: para cada alternativa (A-D), procurar a próxima letra esperada no texto:
    ```python
    # Para alternativa D, procurar "E" seguido de conteúdo
    # Pattern: "texto_D. E texto_E" ou "texto_D E texto_E"
    split_re = re.compile(
        rf'(.+?)\s+{next_letter}\s+(\S.{{2,}})$'
    )
    ```
  - [ ] 1.3 Tratar caso recursivo: 3+ alternativas coladas ("C x. D y. E z.")
    - Aplicar split iterativamente: primeiro separar a última letra, depois a penúltima
    - Abordagem: varrer de trás para frente (E primeiro, depois D, etc.)
  - [ ] 1.4 Só splittar se a letra seguinte NÃO já existe no dicionário (evitar sobrescrever)

- [ ] Task 2: Heurística para evitar falso-positivo (AC: 6)
  - [ ] 2.1 NÃO splittar se o texto após a "letra" parece continuação de frase:
    - Se segue com palavra minúscula longa > 8 chars: provavelmente é texto corrido
    - Se segue com número, fórmula, ou palavra curta (< 8 chars): provavelmente é alternativa
  - [ ] 2.2 Validar que o conteúdo resultante após split tem >= 1 char (não gerar alternativa vazia)
  - [ ] 2.3 Contexto: alternativas matemáticas são tipicamente curtas (1-10 chars), alternativas de texto longo (>50 chars) raramente ficam coladas

- [ ] Task 3: Integrar no orchestrator (AC: 7)
  - [ ] 3.1 Em `EnhancedAlternativeExtractor.extract_alternatives()` (linha ~370), chamar `_split_merged_alternatives()` APÓS o strategy merge e ANTES da validação final
  - [ ] 3.2 Também aplicar na saída de `_extract_alternatives_simple()` em `pymupdf4llm_extractor.py`

- [ ] Task 4: Testes (AC: 7, 8)
  - [ ] 4.1 Testes parametrizados com exemplos reais:
    ```python
    @pytest.mark.parametrize("input_text,expected_d,expected_e", [
        ("W. E T.", "W.", "T."),
        ("52. E 60.", "52.", "60."),
        ("5,00. D 5,83.", "5,00.", "5,83."),  # caso C→D
        ("10[4] E 10[6]", "10[4]", "10[6]"),
        ("18. E 20.", "18.", "20."),
        ("30. E 34.", "30.", "34."),
    ])
    ```
  - [ ] 4.2 Teste com 3 alternativas coladas: "C 1 e 2. D 1 e 3. E 2 e 3."
  - [ ] 4.3 Teste de falso-positivo: "Platão E Aristóteles estudaram" → NÃO splittar
  - [ ] 4.4 Teste de regressão: alternativas limpas não são afetadas

## Dev Notes

### Problema

Em PDFs com colunas estreitas, alternativas D e E (ou mais) ficam na mesma linha no texto extraído:

```
# Resultado atual (errado):
- D) W. E T.    ← Alt D contém "W. E T." inteiro, Alt E duplicada como "T."
- E) T.

# Resultado esperado:
- D) W.
- E) T.
```

### Padrões encontrados no relatório

| Padrão | Questões | Frequência |
|--------|----------|------------|
| `D texto. E texto.` (2 alts) | Q139, Q140, Q142, Q155, Q168, Q173 | ~15 |
| `C texto. D texto. E texto.` (3 alts) | Q154, Q167, Q171 | ~5 |
| `D N E N` (sem pontuação) | Q97, Q131, Q135 | ~5 |

### Posição no pipeline

```
extract_alternatives()
  → strategies (Standard, Multiline, Mathematical, DoubledLetter)
  → strategy merge (best per letter)
  → _split_merged_alternatives()   ← NOVO (aqui)
  → cascade detection and fix
  → validation
```

### Risco: "E" como conjunção dentro de alternativa

Texto legítimo pode conter "E" maiúsculo como conjunção: "Platão E Aristóteles". A heurística deve verificar:
1. A letra candidata está em sequência com a alternativa atual (D → E, C → D)
2. O texto após a letra é curto/numérico (típico de alternativa matemática)
3. A letra NÃO já existe no dicionário de alternativas

### References

- [Source: alternative_extractor.py:305-420] — orchestrator `extract_alternatives()`
- [Source: alternative_extractor.py:370-385] — strategy merge (ponto de integração)
- [Relatório: relatorio-extracao-completo-2026-04-06.md] — ~25 questões afetadas

## Dev Agent Record

### Agent Model Used
(pending)

### Completion Notes List
(pending)

### File List
(pending)
