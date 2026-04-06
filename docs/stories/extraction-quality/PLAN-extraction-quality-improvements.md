# Plano de Melhoria da Qualidade de Extração — ENEM Questions RAG

> Gerado em 2026-04-05 a partir de analise profunda do relatório `questoes_completas_novo.txt` (4.709 entradas, ~61.223 linhas) e do código-fonte do pipeline de extração.

---

## 1. Diagnostico: Panorama dos Erros

### 1.1 Numeros Gerais

| Metrica                          | Valor                        |
|----------------------------------|------------------------------|
| Total de entradas extraidas      | 4.709                        |
| Questoes unicas estimadas        | ~900 (180/ano x 5 anos)      |
| Entradas duplicadas (cadernos)   | ~3.800+                       |
| pdfplumber                       | 4.154 (88,2%)                |
| pymupdf4llm                      | 555 (11,8%)                  |
| Entradas com pelo menos 1 erro   | **~90%+ (pdfplumber), 100% (pymupdf4llm)** |

### 1.2 Catalogo de Erros por Categoria

#### CRITICO — (cid:XX) Texto Ilegivel (~2.829 linhas)
- **Causa**: PDFs de 2021 usam encoding de fonte nao-padrao que pdfplumber nao decodifica.
- **Impacto**: Enunciados e alternativas com tokens `(cid:3)(cid:10)(cid:5)...` inutilizaveis.
- **Escopo**: Quase exclusivamente 2021 pdfplumber (todos os cadernos).
- **Exemplo**: `"Intenso e original, Son of Saul retrata horror do holocausto (cid:3)(cid:10)(cid:5)(cid:13)..."`

#### ALTO — Alternativas em Cascata (~1.782 alternativas >300 chars)
- **Causa**: pdfplumber nao consegue separar alternativas quando A/B/C/D/E aparecem inline sem quebra de linha.
- **Impacto**: Alt A contem todo o texto de B-E, Alt B contem C-E, etc.
- **Escopo**: pdfplumber em todos os anos.
- **Exemplo**:
  ```
  A) [texto do enunciado inteiro + alt A + B + C + D + E]
  B) [texto B + C + D + E]
  C) [texto C + D + E]
  D) [texto D + E]
  E) [texto E — unico correto]
  ```

#### ALTO — [Alternative not found] (918 ocorrencias)
- **Causa**: Regex de extração falha em alternativas matematicas/curtas, e padding com placeholder.
- **Distribuição**: E=61%, D=16%, B=15%, C=4%, A=4%.
- **Escopo**: Maioria em Dia 2 (Ciencias/Matematica) — formulas, graficos, alternativas curtas.

#### MEDIO — Headers/Footers de Pagina no Conteudo (~2.500+ ocorrencias)
- **Causa**: pymupdf4llm `header=False` e heuristics insuficientes; cleanup so limpa formatos especificos.
- **Subtipos**:
  - `"CADERNO X"` / `"DERNO X"`: 1.261 ocorrencias
  - `"Aplicacao"`: 594
  - `"NEM2024"` / `"ENEM20E"`: 685
  - `"Pagina"`: 167
  - Headers de area (`CIENCIAS DA NATUREZA`, `E4 TEMATICA`): 186

#### MEDIO — Caracteres Duplicados / Nomes InDesign (~1.200+ ocorrencias)
- **Causa**: Metadados internos do PDF (nomes de arquivo InDesign) vazam no texto extraido.
- **Exemplo**: `"PP22__22__DDiiaa__MMTTTT__RREEGG__88__VVeerrddee..iinndddd 2255"`
- **Escopo**: Predominante em 2024 pdfplumber.
- **Inclui timestamps duplicados**: `"2233//0088//22002244 1188::1111::2211"`

#### MEDIO — Artefatos Markdown ## ** (~1.050 ocorrencias)
- **Causa**: pymupdf4llm produz markdown com headers/bold nao tratados.
- **Exemplo**: `"E) usar um apelido jocoso... ## **LINGUAGENS, CODIGOS E SUAS TECNOLOGIAS"`

#### MEDIO — Alternativas no Enunciado (pymupdf4llm) (~555 questoes)
- **Causa**: pymupdf4llm inclui alternativas (`- A ...`, `- B ...`) dentro do bloco de enunciado.
- **Escopo**: 100% das questoes pymupdf4llm.

#### BAIXO — Texto Truncado/Interleaved por Colunas (~100+ questoes)
- **Causa**: pdfplumber mistura texto de colunas adjacentes em PDFs multi-coluna (2024).

---

## 2. Analise de Causas Raiz no Codigo

### 2.1 `text_normalizer.py` — Insuficiente
- Nao remove headers de pagina ENEM (so formato `LC - N dia | Caderno...`).
- Nao trata caracteres duplicados de InDesign.
- Nao remove tokens `(cid:XX)`.
- Nao remove timestamps duplicados (`2233//0088//22002244`).
- Instancia novo `EnemTextNormalizer` a cada chamada (ineficiente).

### 2.2 `alternative_extractor.py` — Falso-positivos e sem merge
- `_is_likely_false_positive()` rejeita alternativas com palavras PT-BR comuns ("este", "esta", "pode ser").
- Estrategias rodam independentes sem merge (se S1 acha A,B,C e S2 acha C,D,E, pega so uma).
- Nao trata formatos de dupla-letra 2022-2023 (`AA`, `BB`).

### 2.3 `confidence_scorer.py` — Nao detecta placeholders
- `[Alternative not found]` passa o check de comprimento (27 chars > 5).
- Questao com 3 alternativas reais + 2 placeholders pode score 0.90+ e ser "aceita".
- Nao verifica poluicao textual (headers, InDesign, cid tokens).

### 2.4 `pymupdf4llm_extractor.py` — Sem limpeza pos-split
- Apos `_split_questions()`, nao limpa headers/footers entre questoes.
- `_extract_alternatives_simple()` aceita >= 3 alternativas (perde 2 silenciosamente).
- Nao faz strip de headers de area temática.

### 2.5 `parser.py` — Cleanup parcial e mal posicionado
- `_clean_question_text()` so strip headers no **final** do texto (nao no meio).
- Palavra "E" (conjuncao PT-BR) gera falso-match como alternativa E.

---

## 3. Plano de Acao — Epicos e Stories

### EPIC 8: Melhoria da Qualidade de Extracao

#### Story 8.1 — Text Sanitizer Robusto (Post-Processing Layer)

**Objetivo**: Criar camada unica de sanitizacao "final" que limpa todo texto apos extracao, antes de salvar.

**Tarefas**:
1. **Regex de headers/footers ENEM** — arquivo `text_sanitizer.py` com padroes para:
   - `N° DIA • CADERNO N • COR • AREA` (todas as variantes)
   - `DERNO N . COR-` / `N. COR - Na Aplicacao`
   - `NEM2024 NN` / `ENEM20E NN` / `MENE` reversos
   - `Pagina NN`, `CH - N dia | Caderno...`
   - Timestamps: `NN/NN/NNNN NN:NN:NN` e versoes duplicadas `NNNN//NNNN//NNNN`
2. **Regex de artefatos InDesign** — detectar e remover:
   - Padroes com caracteres duplicados: `PP22__`, `..iinnddbb`, `..iinndddd`, `RREEGG`, etc.
   - Heuristica: sequencia onde cada char esta duplicado (`AABBcc` → provavel InDesign artifact)
3. **Regex de headers de area tematica** — remover em qualquer posicao (nao so final):
   - `LINGUAGENS, CODIGOS E SUAS TECNOLOGIAS`
   - `CIENCIAS HUMANAS E SUAS TECNOLOGIAS`
   - `CIENCIAS DA NATUREZA E SUAS TECNOLOGIAS`
   - `MATEMATICA E SUAS TECNOLOGIAS`
   - `E4 TEMATICA` / `Questoes de N a M`
4. **Remocao de tokens (cid:XX)** — regex `\(cid:\d+\)` substituido por espaco, depois colapsar multiplos espacos.
5. **Remocao de artefatos markdown** — strip `## **`, `**`, `#` residuais.
6. **Singleton do normalizer** — evitar re-instanciar a cada chamada.

**Criterio de aceite**: Texto sanitizado nao contem nenhum dos padroes acima. Testes com exemplos reais de cada categoria.

---

#### Story 8.2 — Extracao de Alternativas Robusta

**Objetivo**: Reescrever logica de splitting de alternativas para lidar com os padros ENEM.

**Tarefas**:
1. **Pre-limpeza do bloco antes do split** — remover headers/footers/InDesign antes de tentar identificar alternativas.
2. **Merge de estrategias** — combinar resultados de multiplas estrategias (uniao em vez de "melhor unico"):
   - Se S1 achou {A,B,C} e S2 achou {C,D,E}, resultado final = {A,B,C,D,E} (C do de maior confianca).
3. **Fix cascading alternatives** — detectar padrao cascata:
   - Se `texto_A ⊃ texto_B ⊃ texto_C ⊃ texto_D ⊃ texto_E`, extrair por differencing (remover texto_B do inicio de texto_A para obter alt A real).
4. **Remover false-positive filter agressivo** — as palavras "este", "esta", "pode ser", "nao ha", "sobre o tema" sao **completamente normais** em alternativas ENEM. Substituir por heuristica baseada em comprimento/estrutura.
5. **Alternativas matematicas curtas** — aceitar alternativas de 1-2 chars se forem numeros, formulas, ou simbolos matematicos (`π`, `√`, etc.).
6. **Suporte a formato 2022-2023 (dupla-letra)** — trazer logica de `parser.py` para o `EnhancedAlternativeExtractor`:
   - `AA)`, `BB)`, `CC)`, `DD)`, `EE)` → A, B, C, D, E.
   - `A A)`, `B B)` (spaced double letters).
7. **Eliminar placeholder `[Alternative not found]`** — nunca salvar placeholders no banco. Se < 5 alternativas, registrar issue no scorer e rotear para fallback.
8. **Validacao: alternativa != substring do enunciado** — rejeitar alternativa se for copia exata de trecho longo do enunciado (> 100 chars).

**Criterio de aceite**: Taxa de `[Alternative not found]` < 2%. Zero alternativas cascata. Zero placeholders no banco.

---

#### Story 8.3 — Confidence Scorer v2

**Objetivo**: Tornar o scorer capaz de detectar contaminacao textual e nao aprovar questoes poluidas.

**Tarefas**:
1. **Check de placeholders** — penalizar se qualquer alternativa contem `[Alternative not found]` ou `[Alternativa nao encontrada]`.
2. **Check de contaminacao textual** — penalizar se enunciado ou alternativas contem:
   - Tokens `(cid:XX)`
   - Padroes InDesign (chars duplicados)
   - Headers de pagina ENEM
   - Timestamps
3. **Check de cascata** — penalizar se alt_A.length > 3 * alt_E.length (heuristica de cascata).
4. **Check de alternativa = enunciado** — penalizar se texto da alternativa > 200 chars e contem substring do enunciado.
5. **Novos pesos sugeridos**:
   ```
   alternatives_count   0.20  (5 alternativas presentes)
   text_quality         0.20  (>= 50 chars, sem contaminacao)
   alt_quality          0.25  (sem placeholder, sem cascata, cada alt >= 3 chars)
   sequence             0.15  (numero 1-180)
   contamination_free   0.10  (sem cid, sem InDesign, sem headers)
   pydantic             0.10  (validacao do modelo)
   ```
6. **Ajustar thresholds**: ACCEPT >= 0.85 (mais rigoroso), FALLBACK >= 0.55.

**Criterio de aceite**: Nenhuma questao com placeholder ou poluicao visivel deve ser "aceita". Questoes com (cid:) devem ir para dead_letter.

---

#### Story 8.4 — Deduplicacao Inteligente de Cadernos

**Objetivo**: Evitar 4-12 copias da mesma questao no banco.

**Tarefas**:
1. **Hash de conteudo** — gerar hash do enunciado normalizado (sem headers/numeros).
2. **Dedup na ingestao** — se hash igual a questao existente, manter a de maior confidence score.
3. **Pick best extraction** — entre pdfplumber e pymupdf4llm para mesma questao, escolher a com menos issues.
4. **Coluna `canonical_question_id`** — linkar questoes duplicadas a um registro canonico.

**Criterio de aceite**: Banco com ~900 questoes unicas (em vez de ~4.700). Cada questao aponta para a melhor extracao disponivel.

---

#### Story 8.5 — Re-extracao Seletiva com pymupdf4llm para Anos Problematicos

**Objetivo**: Usar pymupdf4llm como extrator primario para anos onde pdfplumber falha mais.

**Tarefas**:
1. **2021**: Priorizar pymupdf4llm (que nao tem problema de `cid:XX`). Re-extrair todos os PDFs 2021 com pymupdf4llm.
2. **2024 Dia 2**: Testar pymupdf4llm para reduzir interleaving de colunas e InDesign artifacts.
3. **Comparador qual-extrator** — para cada PDF, rodar ambos extractors e keepar o com maior media de confidence.
4. **Matriz de decisao extrator x ano/dia/caderno** — documentar qual extrator funciona melhor para cada combinacao.

**Criterio de aceite**: Questoes 2021 com >= 80% de texto legivel (vs ~10% atual). 2024 Dia 2 sem artefatos InDesign.

---

#### Story 8.6 — Pipeline de Validacao e Relatorio de Qualidade

**Objetivo**: Ferramenta para auditar qualidade apos extracao, com metricas claras.

**Tarefas**:
1. **Script de auditoria** — `scripts/audit_extraction_quality.py`:
   - Conta questoes por categoria (limpas, com_warnings, com_erros, inutilizaveis).
   - Lista top-10 padroes de poluicao encontrados.
   - Breakdown por ano/dia/caderno/extrator.
2. **Golden set manual** — 50 questoes manualmente validadas como ground truth.
3. **Metricas automaticas**:
   - % de alternativas com placeholder → target: 0%
   - % de enunciados com headers de pagina → target: 0%
   - % de alternativas em cascata → target: 0%
   - % de questoes com (cid:) → target: 0% (dead-lettered)
   - Taxa de deduplicacao → target: ~80% das entradas sao duplicatas identificadas
4. **Report generation** — gerar relatorio markdown automatico apos cada execucao.

**Criterio de aceite**: Dashboard com metricas claras. Regressao detectada automaticamente se qualidade cair.

---

## 4. Prioridade Sugerida

| Ordem | Story | Impacto | Esforco | Justificativa |
|-------|-------|---------|---------|---------------|
| 1     | 8.1   | ALTO    | MEDIO   | Fundacao: toda limpeza downstream depende disso |
| 2     | 8.2   | ALTO    | ALTO    | Resolve os 2 maiores problemas (cascata + not found) |
| 3     | 8.3   | ALTO    | BAIXO   | Evita questoes ruins no banco com pouco codigo |
| 4     | 8.5   | ALTO    | MEDIO   | Resolve 2021 (cid:XX) sem mudar logica — so trocar extrator |
| 5     | 8.4   | MEDIO   | MEDIO   | Limpa o banco de duplicatas, melhora RAG |
| 6     | 8.6   | MEDIO   | BAIXO   | Garante que melhorias sao mensuraveis |

---

## 5. Impacto Esperado

| Metrica                              | Antes    | Target Pos-Plano |
|--------------------------------------|----------|-------------------|
| Questoes com [Alternative not found] | 918      | < 20              |
| Alternativas em cascata              | 1.782    | 0                 |
| Headers/footers no conteudo          | ~2.500   | 0                 |
| Artefatos InDesign                   | ~1.200   | 0                 |
| Questoes com (cid:XX)               | ~2.829 linhas | 0 (dead-lettered ou re-extraidas) |
| Questoes unicas no banco             | ~4.700   | ~900              |
| Questoes limpas e utilizaveis        | ~10%     | **>90%**          |

---

## 6. Dependencias e Riscos

| Risco | Mitigacao |
|-------|-----------|
| pymupdf4llm tambem falha em 2021 (cid:XX) | Testar OCR mode como fallback adicional |
| Regex de limpeza remove conteudo legitimo | Golden set de validacao (8.6) + testes unitarios extensivos |
| Performance com 2 extractors por PDF | Cache hash — so re-extrai se score < threshold |
| Dedup incorreta (questoes parecidas mas diferentes) | Hash por enunciado completo normalizado, nao so inicio |

---

## 7. Dev Agent Record — Implementation Status

> Updated: 2026-04-06

### Story 8.1 — Text Sanitizer Robusto — **DONE**

| Artefato | Caminho |
|----------|---------|
| Text Sanitizer | `src/enem_ingestion/text_sanitizer.py` |
| Singleton normalizer | `src/enem_ingestion/text_normalizer.py` |
| Tests | `tests/test_text_sanitizer.py` (39 tests) |

- Regex patterns for ENEM headers, area headers, InDesign artifacts, (cid:XX), markdown residual
- `sanitize_enem_text()`, `sanitize_alternative()`, `has_contamination()` public API
- Singleton pattern for TextSanitizer and EnemTextNormalizer

### Story 8.2 — Extracao de Alternativas Robusta — **DONE**

| Artefato | Caminho |
|----------|---------|
| Alternative Extractor (rewrite) | `src/enem_ingestion/alternative_extractor.py` |
| Parser (placeholder removal) | `src/enem_ingestion/parser.py` |
| pymupdf4llm extractor (sanitizer integration) | `src/enem_ingestion/pymupdf4llm_extractor.py` |
| Tests | `tests/test_alternative_extractor_v2.py` (17 tests) |

- 4 strategies: Standard, Multiline, Mathematical, DoubledLetter
- Strategy merge (union of best per letter)
- Cascade detection and fix via reverse differencing
- False-positive filter: structural heuristics instead of PT-BR word list
- Placeholder `[Alternative not found]` removed from 3 locations in parser.py

### Story 8.3 — Confidence Scorer v2 — **DONE**

| Artefato | Caminho |
|----------|---------|
| Confidence Scorer (rewrite) | `src/enem_ingestion/confidence_scorer.py` |
| Tests | `tests/test_confidence_scorer.py` (26 tests) |

- New weights: alt_count 0.20, text_quality 0.20, alt_quality 0.25, sequence 0.15, contamination 0.10, pydantic 0.10
- Thresholds: ACCEPT >= 0.85, FALLBACK >= 0.55
- Placeholder detection, cascade detection, contamination check via TextSanitizer

### Story 8.4 — Deduplicacao Inteligente — **DONE**

| Artefato | Caminho |
|----------|---------|
| DB Migration | `database/dedup-migration.sql` |
| Pipeline dedup logic | `src/enem_ingestion/pipeline_v2.py` (`compute_content_hash`, `_persist_question`) |
| Standalone dedup script | `scripts/deduplicate_existing.py` |
| Tests | `tests/test_content_hash_dedup.py` (16 tests) |

- Content hash: SHA-256 of normalized enunciado + year + day, truncated to 16 hex chars
- Pipeline skips insert if existing question has higher confidence score
- Standalone script backfills hashes and marks duplicates with `canonical_question_id`
- DB adds `content_hash VARCHAR(16)` (unique index) and `canonical_question_id UUID`

### Story 8.5 — Re-extracao Seletiva — **DONE**

| Artefato | Caminho |
|----------|---------|
| Extractor decision matrix | `src/enem_ingestion/pipeline_v2.py` (`_EXTRACTOR_MATRIX`) |
| Comparison script | `scripts/compare_extractors.py` |
| Tests | `tests/test_extractor_comparison.py` (7 tests) |

- `_EXTRACTOR_MATRIX` maps (year, day) → preferred extractor
- Comparison script runs both extractors per PDF and generates markdown decision matrix
- 2021 hard-coded to pymupdf4llm (pdfplumber produces cid:XX tokens)

### Story 8.6 — Pipeline de Validacao e Relatorio — **DONE**

| Artefato | Caminho |
|----------|---------|
| Audit script | `scripts/audit_extraction_quality.py` |
| Tests | `tests/test_audit_quality.py` (24 tests) |

- `detect_issues()`: placeholder, header_pollution, cid_token, indesign_artifact, markdown_artifact, cascade, short_enunciado, missing_alternatives
- `audit_questions()`: fetches all from DB, aggregates by year/extractor
- `generate_markdown()`: pass/fail report against configurable QualityTargets
- Breakdown by year, extractor, top-20 most problematic questions

### Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| test_text_sanitizer.py | 39 | PASS |
| test_alternative_extractor_v2.py | 17 | PASS |
| test_confidence_scorer.py | 26 | PASS |
| test_content_hash_dedup.py | 16 | PASS |
| test_extractor_comparison.py | 7 | PASS |
| test_audit_quality.py | 24 | PASS |
| test_pipeline_v2.py | 10 | PASS |
| test_enhanced_alternatives.py | 14 | PASS |
| **Full regression** | **316 passed** | **0 new failures** |

Pre-existing failures (not Epic 8): GraphQL tests (12), semantic search filter test (1), tiktoken import (4 collection errors).
