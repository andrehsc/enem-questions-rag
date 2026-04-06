# Epic 9: Qualidade de Extração v2 — Pós-Ingestão 2020-2021

> Gerado em 2026-04-06 a partir de análise do relatório `relatorio-extracao-completo-2026-04-06.md` (223 questões aceitas, 534 detectadas, 10 cadernos).

---

## 1. Diagnóstico: Problemas Residuais Pós-Epic 8

O Epic 8 implementou sanitizer, extrator robusto, scorer v2, dedup e pipeline de validação. Porém a ingestão real de 10 cadernos (2020 D1/D2, 2021 D1) revelou problemas que escaparam do pipeline:

### 1.1 Números Gerais

| Métrica | Valor |
|---------|-------|
| Questões aceitas (banco) | 223 (41.8%) |
| Dead letter | 311 (58.2%) |
| Questões com alternativas duplicadas (raw + formatadas) | ~70+ (31%+) |
| Questões com alternativas coladas (D+E mesma linha) | ~25 (11%) |
| Questões com conteúdo misturado entre questões | ~25 (11%) |
| Questões com alternativas incompletas/cortadas | ~18 (8%) |
| Lixo no enunciado (identificadores caderno) | 4 instâncias (2021) |

### 1.2 Catálogo de Erros Residuais

#### ALTO — Alternativas Brutas Duplicadas no Enunciado (~70+ questões)

O extrator `pymupdf4llm` gera markdown onde as alternativas aparecem **duas vezes**: primeiro em texto bruto (como veio do PDF) e depois no formato markdown com bullet points. O `_extract_enunciado()` para ao ver `- **A)**` ou `^[A-E])`, mas **não reconhece** o formato bruto `A texto.` / `B texto.` sem dash/bold, permitindo que as alternativas brutas entrem no enunciado.

**Exemplo (Q172 matematica)**:
```
> Para que ele atinja seu objetivo, o raio...

A 4,00.           ← alternativa bruta no enunciado (ERRO)
B 4,87.           ← alternativa bruta no enunciado (ERRO)

- **A)** 4,00.    ← alternativa formatada (correta)
- **B)** 4,87.
- **C)** 5,00. D 5,83.   ← alternativa colada (ERRO)
- **D)** 5,83.
- **E)** 6,26.
```

#### ALTO — Alternativas Coladas na Mesma Linha (~25 questões)

Quando o PDF tem colunas estreitas, duas ou mais alternativas ficam na mesma linha. O parser captura tudo como uma alternativa só.

**Subtipos encontrados**:
- `D W. E T.` → D captura "W. E T.", E separada como "T."
- `C 1 e 2. D 1 e 3. E 2 e 3.` → 3 alternativas numa linha só
- `D 52. E 60.` → D e E compactadas
- `C 5,00. D 5,83.` → decimais colados

#### MEDIO — Identificadores de Caderno no Enunciado (2021)

Padrões de OCR artifact que passam pelo sanitizer atual:
- `enem2o02/`, `enem2o2/` — OCR lê logotipos como texto
- `6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação` — header fora do formato esperado
- `20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação`

#### MEDIO — Scorer Aceita Questões com Contaminação Leve

O peso de `contamination` no scorer é apenas `0.10`. Uma questão com **todas as alternativas corretas mas enunciado poluído** pode ter score `0.90` e ser aceita. A contaminação deveria ter peso maior para barrar questões com lixo no texto.

#### MEDIO — Guardrails São Advisory-Only

O `EnemStructuralGuardrailsController` computa riscos e valida questões, mas quando retorna `VALIDATION_FAILED`, o código faz `pass` e segue com o resultado do enhanced extractor. Questões que falharam na validação estrutural deveriam ser penalizadas no scorer ou roteadas para fallback.

---

## 2. Análise de Causas Raiz

### 2.1 `_extract_enunciado()` — Stop condition insuficiente

```python
# pymupdf4llm_extractor.py:429-435 — SÓ para nestes formatos:
if re.match(r'^\*{0,2}\(?[A-E]\)\*{0,2}\s', stripped):  # (A), **(A)**
    break
if re.match(r'^-\s+[A-E]\s', stripped):  # - A texto
    break
# NÃO para em: "A texto.", "B texto." (formato bruto do PDF)
```

### 2.2 `StandardPatternStrategy` — Usa `\n` como delimitador exclusivo

```python
# alternative_extractor.py — Todos os 5 padrões usam \n como boundary:
r'\n\s*([A-E])\s+([^\n]{3,500}?)(?=\n\s*[A-E]\s|...)'
# Quando D e E estão na mesma linha, captura tudo como uma alternativa
```

### 2.3 `confidence_scorer.py` — Peso contamination = 0.10

```python
# contamination pesa só 0.10 do total:
# alt_count=0.20 + text_quality=0.20 + alt_quality=0.25 + sequence=0.15 + contamination=0.10 + pydantic=0.10
# Questão poluída mas com 5 alts limpas: 0.20+0.20+0.25+0.15+0.00+0.10 = 0.90 → ACCEPT
```

### 2.4 `parser.py:547` — Guardrails VALIDATION_FAILED ignorado

```python
elif guardrails_result['status'] == 'VALIDATION_FAILED':
    # ... logging ...
    pass  # ← ignora o resultado, segue com enhanced extractor
```

### 2.5 `text_sanitizer.py` — Padrões 2021 ausentes

O sanitizer remove `LC - Ndia | Caderno N ... Página N` (com "Página" obrigatório) e `enem\W*\d+/` (sem o "o" do OCR). Não captura:
- `\d+ LC - Nº dia | Caderno N - COR - Nª Aplicação` (sem "Página")
- `enem2o\d+/` (com "o" substituindo "0" por OCR)

---

## 3. Plano de Ação — Stories

### Epic 9: Qualidade de Extração v2

| Story | Título | Impacto | Esforço | Dependências |
|-------|--------|---------|---------|--------------|
| 9.1 | Strip de alternativas brutas do enunciado | ALTO | BAIXO | — |
| 9.2 | Split de alternativas coladas na mesma linha | ALTO | MÉDIO | — |
| 9.3 | Recalibrar peso de contaminação no scorer | ALTO | BAIXO | — |
| 9.4 | Ativar guardrails como bloqueantes | MÉDIO | BAIXO | — |
| 9.5 | Limpar identificadores de caderno (2021) | MÉDIO | BAIXO | — |

---

#### Story 9.1 — Strip de Alternativas Brutas do Enunciado

**Resumo**:
**Como** engenheiro de dados,
**Eu quero** que o enunciado extraído não contenha alternativas brutas duplicadas,
**Para que** o texto armazenado seja limpo e utilizável no RAG sem ruído.

**Contexto técnico**:
O `pymupdf4llm` produz markdown onde alternativas aparecem primeiro em formato bruto (`A texto.\nB texto.`) e depois em formato markdown (`- **A)** texto.`). O `_extract_enunciado()` só para ao encontrar formato markdown/parenthesado, permitindo que as brutas entrem no enunciado.

**Implementação**:
1. Em `_extract_enunciado()` (`pymupdf4llm_extractor.py:424`), adicionar um stop condition para linhas que começam com `^[A-E]\s+.{3,}` (letra maiúscula A-E seguida de espaço e pelo menos 3 chars):
   ```python
   # Novo stop condition — alternativa bruta sem formatação
   if re.match(r'^[A-E]\s+\S.{2,}', stripped):
       break
   ```
2. Adicionar heurística de contexto: só parar se a linha anterior **não** começa com artigo/preposição (evitar falso-positivo com "A família..." ou "E então..."):
   ```python
   # Guardrails contra falso-positivo com conjunção "E" e artigo "A"
   if re.match(r'^[A-E]\s+\S.{2,}', stripped):
       # Validar: se é letra isolada seguida de texto curto (< 200 chars)
       # e existem pelo menos 2 linhas similares abaixo, é alternativa
       if _looks_like_alternative_block(lines[i:i+5]):
           break
   ```
3. Implementar `_looks_like_alternative_block()`:
   - Conta quantas das próximas 5 linhas começam com `^[A-E]\s+`
   - Se >= 3, confirma bloco de alternativas
   - Letras devem estar em sequência (A, B, C, D, E)

**Critérios de aceite**:
- [ ] Nenhuma questão aceita contém alternativas brutas no enunciado
- [ ] Enunciados que começam com "A família..." ou "E então..." não são cortados (falso-positivo)
- [ ] Testes com >= 10 exemplos reais do relatório (Q172, Q171, Q173, Q170, Q167, Q166, Q155, Q142, Q139, Q136)
- [ ] Regressão: nenhuma questão limpa existente quebra

**Arquivos afetados**:
- `src/enem_ingestion/pymupdf4llm_extractor.py` (modificar `_extract_enunciado`)
- `tests/test_pymupdf4llm_extractor.py` (novos testes)

---

#### Story 9.2 — Split de Alternativas Coladas na Mesma Linha

**Resumo**:
**Como** engenheiro de dados,
**Eu quero** que alternativas compactadas na mesma linha sejam corretamente separadas,
**Para que** cada alternativa A-E tenha seu conteúdo isolado sem contaminar a próxima.

**Contexto técnico**:
Em PDFs com colunas estreitas, as alternativas D e E (ou mais) aparecem na mesma linha: `D texto1. E texto2.` ou `C 1 e 2. D 1 e 3. E 2 e 3.`. O regex atual usa `\n` como boundary e não detecta múltiplas alternativas inline.

**Implementação**:
1. Criar `_split_merged_alternatives()` no `alternative_extractor.py`:
   ```python
   def _split_merged_alternatives(self, alternatives: Dict[str, str]) -> Dict[str, str]:
       """Detect and split alternatives merged on the same line.

       Detects patterns like "texto1. E texto2" inside alternative D text,
       where E's content leaked into D.
       """
       result = dict(alternatives)
       letters = 'ABCDE'
       for i, letter in enumerate(letters[:-1]):  # A through D
           next_letter = letters[i + 1]
           if letter not in result:
               continue
           text = result[letter]
           # Pattern: "texto. X texto" where X is the next expected letter
           split_pattern = re.compile(
               rf'(.+?)\s+{next_letter}\s+(\S.+)$'
           )
           match = split_pattern.match(text)
           if match and next_letter not in result:
               result[letter] = match.group(1).strip().rstrip('.')
               result[next_letter] = match.group(2).strip()
       return result
   ```
2. Chamar `_split_merged_alternatives()` no orchestrator após strategy merge (line ~370 em `alternative_extractor.py`)
3. Tratar caso de 3+ alternativas coladas (`C 1 e 2. D 1 e 3. E 2 e 3.`) aplicando o split recursivamente
4. Validar que o split não quebra alternativas legítimas que contêm letra maiúscula (ex: "Platão E Aristóteles" — verificar se a letra é seguida por texto que parece alternativa, não continuação de frase)

**Critérios de aceite**:
- [ ] `"D W. E T."` → D="W.", E="T."
- [ ] `"C 1 e 2. D 1 e 3. E 2 e 3."` → C="1 e 2.", D="1 e 3.", E="2 e 3."
- [ ] `"D 52. E 60."` → D="52.", E="60."
- [ ] `"C 5,00. D 5,83."` → C="5,00.", D="5,83."
- [ ] `"D 10[4] E 10[6]"` → D="10[4]", E="10[6]"
- [ ] Alternativa legítima `"D Platão E Aristóteles"` NÃO é splitada (heurística de contexto)
- [ ] Testes com >= 15 exemplos reais do relatório
- [ ] Regressão: nenhuma alternativa limpa existente quebra

**Arquivos afetados**:
- `src/enem_ingestion/alternative_extractor.py` (novo método + integração no orchestrator)
- `tests/test_alternative_extractor_v2.py` (novos testes)

---

#### Story 9.3 — Recalibrar Peso de Contaminação no Scorer

**Resumo**:
**Como** engenheiro de dados,
**Eu quero** que questões com contaminação textual detectada não sejam aceitas no banco,
**Para que** a qualidade mínima das questões aceitas seja garantida.

**Contexto técnico**:
O peso de `contamination` no scorer é `0.10`. Questão com todas as 5 alternativas mas enunciado contaminado pode ter score:
- alt_count=0.20 + text_quality=0.20 + alt_quality=0.25 + sequence=0.15 + **contamination=0.00** + pydantic=0.10 = **0.90** → ACCEPT

Com peso 0.90, a questão passa o threshold de 0.85. Se contamination subir para 0.20, o score máximo com contaminação seria 0.80 → FALLBACK (correto).

**Implementação**:
1. Em `confidence_scorer.py`, redistribuir pesos:
   ```python
   # Antes:
   # alt_count=0.20, text_quality=0.20, alt_quality=0.25,
   # sequence=0.15, contamination=0.10, pydantic=0.10

   # Depois:
   # alt_count=0.20, text_quality=0.15, alt_quality=0.25,
   # sequence=0.10, contamination=0.20, pydantic=0.10
   ```
2. Atualizar docstring e comentários internos
3. Adicionar check de **alternativas brutas no enunciado** como critério de contaminação:
   ```python
   # Em has_contamination() ou _score_contamination():
   # Detectar linhas ^[A-E]\s+.{3,} dentro do question.text antes das alternativas formatadas
   ```
4. Atualizar testes existentes com novos pesos

**Critérios de aceite**:
- [ ] Questão com contaminação detectada tem score máximo < 0.85 (não é aceita)
- [ ] Questão limpa com 5 alternativas ainda alcança score 1.00
- [ ] Testes atualizados refletem novos pesos
- [ ] Nenhuma questão limpa existente é rejeitada indevidamente

**Arquivos afetados**:
- `src/enem_ingestion/confidence_scorer.py` (pesos e check adicional)
- `tests/test_confidence_scorer.py` (atualização de testes)

---

#### Story 9.4 — Ativar Guardrails como Bloqueantes

**Resumo**:
**Como** engenheiro de dados,
**Eu quero** que questões que falharam na validação dos guardrails sejam penalizadas no scoring,
**Para que** questões estruturalmente inválidas não sejam aceitas no banco.

**Contexto técnico**:
O `EnemStructuralGuardrailsController` valida a estrutura da questão e retorna `VALIDATION_FAILED` quando há problemas. Porém em `parser.py:547`, o resultado é ignorado (`pass`) e a questão segue normalmente no pipeline.

**Implementação**:
1. Em `parser.py`, quando `guardrails_result['status'] == 'VALIDATION_FAILED'`:
   - Propagar o status de falha para o dataclass `Question` via novo campo `guardrails_failed: bool`
   ```python
   elif guardrails_result['status'] == 'VALIDATION_FAILED':
       recovery = guardrails_result['recovery_strategy']
       risk_level = guardrails_result['guardrails_applied']['risk_level']
       # Marcar questão como falhada nos guardrails
       guardrails_failed = True
       logger.warning(f"Q{question_number} Guardrails BLOCKED: risk={risk_level}")
   ```
2. Em `confidence_scorer.py`, adicionar penalização para `guardrails_failed`:
   ```python
   def _score_guardrails(self, question: Question, issues: List[str]) -> float:
       """Penalizar questões que falharam nos guardrails estruturais."""
       if getattr(question, 'guardrails_failed', False):
           issues.append("guardrails_validation_failed")
           return -0.15  # Penalidade que força fallback
       return 0.0
   ```
3. Alternativa mais simples: integrar no `_score_contamination` existente em vez de novo campo:
   - Se guardrails falha, marcar contaminação, zerando os 0.20 pontos
4. Atualizar dataclass `Question` em `parser.py` para incluir campo `guardrails_failed`

**Critérios de aceite**:
- [ ] Questão com `VALIDATION_FAILED` tem score reduzido (não aceita se score < 0.85)
- [ ] Questão com guardrails `SUCCESS` não é afetada
- [ ] Log clarifica quando questão é penalizada por guardrails
- [ ] Testes unitários para ambos os cenários

**Arquivos afetados**:
- `src/enem_ingestion/parser.py` (propagar status guardrails)
- `src/enem_ingestion/confidence_scorer.py` (penalização)
- `tests/test_confidence_scorer.py` (novos testes)

---

#### Story 9.5 — Limpar Identificadores de Caderno (2021)

**Resumo**:
**Como** engenheiro de dados,
**Eu quero** que artefatos de OCR dos cadernos 2021 sejam removidos do texto extraído,
**Para que** o enunciado não contenha identificadores de página/caderno irrelevantes.

**Contexto técnico**:
Os PDFs de 2021 produzem artefatos de OCR não cobertos pelo sanitizer atual:
- `enem2o02/`, `enem2o2/` — OCR do logotipo ENEM lido como texto (com "o" no lugar de "0")
- `6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação` — header de caderno sem "Página" no final
- `20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação` — idem

O sanitizer atual tem regex que exige "Página \d+" no final do padrão LC.

**Implementação**:
1. Em `text_sanitizer.py`, adicionar padrões em `_header_patterns`:
   ```python
   # Header LC sem "Página" no final (2021)
   r'\d+\s+(?:LC|MT|CN|CH)\s*-\s*\d+[°ºo]?\s*dia\s*\|\s*Caderno\s*\d+\s*-\s*(?:AZUL|AMARELO|AMARELA|BRANCO|BRANCA|VERDE|ROSA|CINZA)\s*-\s*\d*[aª]?\s*(?:Aplicação|Aplicacao)',
   ```
2. Atualizar padrão `_header_patterns_nocase` para OCR do logotipo:
   ```python
   # OCR do logotipo com "o" substituindo "0": "enem2o02/", "enem2o2/"
   r'enem\d*o+\d*/?',
   ```
3. Adicionar em `has_contamination()` os mesmos padrões para que o scorer detecte a poluição

**Critérios de aceite**:
- [ ] `sanitize_enem_text("texto enem2o02/ continuação")` → `"texto continuação"`
- [ ] `sanitize_enem_text("texto enem2o2/ continuação")` → `"texto continuação"`
- [ ] `sanitize_enem_text("6 LC - 1º dia | Caderno 1 - AZUL - 1º Aplicação")` → `""`
- [ ] `sanitize_enem_text("20 LC - 1º dia | Caderno 2 - AMARELO - 1º Aplicação")` → `""`
- [ ] `has_contamination("texto enem2o02/ test")` → `True`
- [ ] Padrões existentes do sanitizer não são afetados (regressão)
- [ ] Testes unitários para cada padrão

**Arquivos afetados**:
- `src/enem_ingestion/text_sanitizer.py` (novos padrões)
- `tests/test_text_sanitizer.py` (novos testes)

---

## 4. Prioridade Sugerida

| Ordem | Story | Impacto | Esforço | Justificativa |
|-------|-------|---------|---------|---------------|
| 1 | 9.5 | MÉDIO | BAIXO | Quick win: 2 regex no sanitizer, resolve lixo 2021 |
| 2 | 9.1 | ALTO | BAIXO | Resolve ~70 questões com alternativas duplicadas no enunciado |
| 3 | 9.2 | ALTO | MÉDIO | Resolve ~25 questões com alternativas coladas |
| 4 | 9.3 | ALTO | BAIXO | Evita aceitar questões poluídas (ajuste de pesos) |
| 5 | 9.4 | MÉDIO | BAIXO | Ativa guardrails existentes como proteção real |

---

## 5. Impacto Esperado

| Métrica | Antes (Epic 8) | Target Pós-Epic 9 |
|---------|----------------|---------------------|
| Alternativas brutas no enunciado | ~70 questões | 0 |
| Alternativas coladas (D+E mesma linha) | ~25 questões | 0 |
| Lixo de caderno no enunciado (2021) | 4 questões | 0 |
| Questões poluídas aceitas (score >= 0.85) | ~10% | 0% |
| Guardrails bloqueando questões ruins | 0 (advisory) | Ativo |

---

## 6. Dependências e Riscos

| Risco | Mitigação |
|-------|-----------|
| Stop condition de alternativas brutas gera falso-positivo (ex: "A família...") | Heurística `_looks_like_alternative_block()` com validação de sequência A-E |
| Split de alternativas coladas quebra texto legítimo | Verificar que próxima letra está em sequência e contexto é curto/numérico |
| Novo peso contamination rejeita questões boas | Validar impacto com relatório de auditoria antes de mergear |
| Guardrails bloqueiam demais | Implementar como penalidade gradual, não rejeição absoluta |

---

## 7. Dev Agent Record — Implementation Status

> Updated: 2026-04-06

### Story 9.1 — Strip de Alternativas Brutas do Enunciado — **TODO**
### Story 9.2 — Split de Alternativas Coladas — **TODO**
### Story 9.3 — Recalibrar Peso de Contaminação — **TODO**
### Story 9.4 — Ativar Guardrails como Bloqueantes — **TODO**
### Story 9.5 — Limpar Identificadores de Caderno (2021) — **TODO**
