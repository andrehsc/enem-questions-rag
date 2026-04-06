# Story 8.5: Re-extração Seletiva

Status: pending

## Story

Como desenvolvedor,
Quero usar pymupdf4llm como extrator para anos onde pdfplumber falha (2021 cid:XX, 2024 InDesign),
Para recuperar texto legível em questões atualmente inutilizáveis.

## Acceptance Criteria (AC)

1. 2021: re-extração completa com pymupdf4llm elimina tokens (cid:XX)
2. 2024 Dia 2: teste de pymupdf4llm para reduzir InDesign artifacts
3. Comparador dual-extrator: rodar ambos e manter o de maior confidence média por PDF
4. Matriz de decisão extrator × ano/dia documentada
5. Questões 2021 com >= 80% de texto legível (vs ~10% atual)

## Tasks / Subtasks

- [ ] Task 1: Re-extração 2021 com pymupdf4llm (AC: 1, 5)
  - [ ] 1.1 Identificar todos os PDFs 2021 em `data/downloads/` (padrão: `2021_PV_*.pdf`)
  - [ ] 1.2 Rodar `Pymupdf4llmExtractor.extract_questions()` em cada PDF
  - [ ] 1.3 Contar tokens (cid:XX) no output — comparar com pdfplumber
  - [ ] 1.4 Se pymupdf4llm produz texto limpo (zero cid): marcar como extrator preferido para 2021
  - [ ] 1.5 Se pymupdf4llm também falha: testar com `force_ocr=True` como fallback
- [ ] Task 2: Teste 2024 Dia 2 (AC: 2)
  - [ ] 2.1 Rodar pymupdf4llm nos PDFs 2024 Dia 2 (CD5-CD8)
  - [ ] 2.2 Contar artefatos InDesign (chars duplicados) vs pdfplumber
  - [ ] 2.3 Documentar resultados comparativos
- [ ] Task 3: Script comparador dual-extrator (AC: 3)
  - [ ] 3.1 Criar `scripts/compare_extractors.py`:
    ```python
    def compare_pdf(pdf_path: str) -> dict:
        """Roda pdfplumber e pymupdf4llm, retorna métricas comparativas."""
        # pymupdf4llm extraction
        ext_pymupdf = Pymupdf4llmExtractor(output_dir="data/tmp")
        questions_pymupdf = ext_pymupdf.extract_questions(str(pdf_path))

        # pdfplumber extraction (via parser)
        parser = EnemPDFParser()
        questions_pdfplumber = parser.parse_questions(str(pdf_path))

        # Score each set
        scorer = ExtractionConfidenceScorer()
        scores_pymupdf = [scorer.score(q).score for q in questions_pymupdf]
        scores_pdfplumber = [scorer.score(q).score for q in questions_pdfplumber]

        return {
            'pdf': pdf_path,
            'pymupdf4llm': {'count': len(questions_pymupdf), 'avg_score': mean(scores_pymupdf)},
            'pdfplumber': {'count': len(questions_pdfplumber), 'avg_score': mean(scores_pdfplumber)},
            'recommended': 'pymupdf4llm' if mean(scores_pymupdf) > mean(scores_pdfplumber) else 'pdfplumber',
        }
    ```
  - [ ] 3.2 Output: tabela markdown com resultados por PDF
  - [ ] 3.3 CLI: `python scripts/compare_extractors.py --input data/downloads/`
- [ ] Task 4: Matriz de decisão e integração (AC: 4)
  - [ ] 4.1 Criar `docs/extractor-decision-matrix.md`:
    ```markdown
    | Ano  | Dia | Cadernos | Melhor Extrator | Razão                    |
    |------|-----|----------|-----------------|--------------------------|
    | 2020 | 1   | CD1-CD4  | (resultado)     | (métricas)               |
    | 2020 | 2   | CD5-CD8  | (resultado)     | (métricas)               |
    | 2021 | 1   | CD1-CD4  | (resultado)     | (métricas — cid:XX?)     |
    | ...  |     |          |                 |                          |
    ```
  - [ ] 4.2 Em `pipeline_v2.py`: adicionar lógica de auto-seleção de extrator baseada na matriz
    ```python
    def _select_extractor(self, year: int, day: int) -> str:
        """Selecionar extrator baseado na matriz de decisão."""
        MATRIX = {
            (2021, 1): 'pymupdf4llm',
            (2021, 2): 'pymupdf4llm',
            # ... populado por Task 3
        }
        return MATRIX.get((year, day), 'pymupdf4llm')  # default
    ```
- [ ] Task 5: Testes (AC: 1, 5)
  - [ ] 5.1 Teste: re-extração 2021 com pymupdf4llm reduz (cid:XX) para < 5%
  - [ ] 5.2 Teste: comparador retorna recomendação válida
  - [ ] 5.3 Teste: auto-seleção de extrator funciona conforme matriz

## Dev Notes

### Estado atual: 2021 é catastrófico com pdfplumber

- ~2.829 linhas afetadas por (cid:XX) — quase exclusivamente 2021 pdfplumber
- Tokens (cid:XX) são Character IDs de fontes não-padrão que pdfplumber não decodifica
- pymupdf4llm usa método de extração diferente que pode não ter o problema
- Se pymupdf4llm também falha: OCR mode (`force_ocr=True, ocr_language="por"`) como última alternativa

### pymupdf4llm já tem extração funcional para 2020/2021

Na tabela do diagnóstico:
- 2020: 387 questões via pymupdf4llm (já extraídas)
- 2021: 168 questões via pymupdf4llm (já extraídas)

Porém, as extrações pymupdf4llm existentes também têm problemas (markdown artifacts `## **`, alternativas no enunciado). Com Story 8.1 (sanitizer) + 8.2 (alt extractor), esses problemas serão resolvidos.

### Dependências

- Depende de Story 8.1 (sanitizer) e 8.2 (alt extractor) para extrações limpas
- Independente de 8.3 (scorer) e 8.4 (dedup)

### Anti-Patterns a Evitar

- NÃO rodar re-extração sem as melhorias de 8.1/8.2 — a extração bruta terá os mesmos problemas
- NÃO assumir que pymupdf4llm é sempre melhor — testar empiricamente por ano/dia
- NÃO deletar extrações pdfplumber existentes — manter para comparação

### References

- [Source: pymupdf4llm_extractor.py:_extract_markdown] — pymupdf4llm call, line ~107
- [Source: pymupdf4llm_extractor.py:_detect_scanned_pages] — OCR detection
- [Source: pipeline_v2.py:run] — pipeline entry point
- [Source: PLAN-extraction-quality-improvements.md] — 2.829 cid lines, extraction table

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
