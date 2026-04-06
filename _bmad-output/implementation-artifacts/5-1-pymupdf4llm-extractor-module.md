# Story 5.1: pymupdf4llm Extractor Module

Status: done

## Story

Como desenvolvedor,
Quero um módulo `pymupdf4llm_extractor.py` que substitua o pdfplumber como extrator primário,
Para extrair questões ENEM com multi-coluna automático, OCR em português e associação de imagens.

## Acceptance Criteria (AC)

1. Usa `pymupdf4llm.to_markdown()` com `page_chunks=True` para extração
2. Multi-coluna detectado automaticamente via Layout AI module (ONNX)
3. OCR ativado via `force_ocr=True, ocr_language="por"` para páginas escaneadas
4. Header/footer removidos via `header=False, footer=False`
5. Associação imagem-questão via bounding box overlap
6. Compatível com dataclasses `Question`, `QuestionMetadata`, `AnswerKey` do `parser.py` existente
7. Testes unitários com PDFs de referência (pelo menos 3 tipos: texto puro, multi-coluna, com imagens)

## Tasks / Subtasks

- [ ] Task 1: Instalar pymupdf4llm com extras (AC: 1, 2, 3)
  - [ ] 1.1 Adicionar `pymupdf4llm[ocr,layout]>=1.27.0` ao `requirements.txt`
  - [ ] 1.2 Verificar compatibilidade com `PyMuPDF>=1.26.5` já instalado (pymupdf4llm instala sua própria versão — pode conflitar)
  - [ ] 1.3 Adicionar `pymupdf4llm` ao `pyproject.toml` em `[project.optional-dependencies]` se necessário
- [ ] Task 2: Criar `src/enem_ingestion/pymupdf4llm_extractor.py` (AC: 1, 2, 3, 4, 6)
  - [ ] 2.1 Classe `Pymupdf4llmExtractor` com método `extract_questions(pdf_path) -> List[Question]`
  - [ ] 2.2 Importar `pymupdf.layout` ANTES de `pymupdf4llm` para ativar Layout AI
  - [ ] 2.3 Chamada `to_markdown()` com params: `page_chunks=True, header=False, footer=False, write_images=True, image_path=<output_dir>, image_format="png", dpi=150, ocr_language="por"`
  - [ ] 2.4 Detecção automática de OCR: checar se página tem texto extraível, ativar `force_ocr=True` apenas se página for scanned
  - [ ] 2.5 Parser de markdown→Question: regex para separar questões (pattern `QUESTÃO \d+` ou `\d+\s+[A-E]`), extrair enunciado + alternativas
  - [ ] 2.6 Reutilizar `EnhancedAlternativeExtractor` de `alternative_extractor.py` para extração de alternativas quando o regex simples falhar
  - [ ] 2.7 Reutilizar `EnemTextNormalizer.normalize_full()` de `text_normalizer.py` para limpeza de texto
  - [ ] 2.8 Reutilizar `_determine_subject(question_number, day)` e `parse_filename()` de `parser.py`
  - [ ] 2.9 Retornar `List[Question]` usando as mesmas dataclasses do `parser.py`
- [ ] Task 3: Associação imagem-questão via bounding box (AC: 5)
  - [ ] 3.1 Usar `pymupdf4llm.to_json()` para obter bounding boxes de cada elemento da página
  - [ ] 3.2 Para cada imagem, calcular overlap com região da questão (Y range: início questão N → início questão N+1)
  - [ ] 3.3 Associar imagem à questão com maior overlap
  - [ ] 3.4 Salvar imagens extraídas em `data/extracted_images/{year}/{question_number}/`
- [ ] Task 4: Testes unitários (AC: 7)
  - [ ] 4.1 Criar `tests/test_pymupdf4llm_extractor.py`
  - [ ] 4.2 Teste com PDF de texto puro (mock pymupdf4llm.to_markdown retornando markdown simples)
  - [ ] 4.3 Teste com PDF multi-coluna (mock retornando 2-column markdown)
  - [ ] 4.4 Teste com PDF com imagens (mock retornando markdown com image refs + to_json com bounding boxes)
  - [ ] 4.5 Teste de fallback: quando pymupdf4llm falha, verifica que raise/log adequado (NÃO cair de volta para pdfplumber — fallback será via confidence score na Story 5.2)
  - [ ] 4.6 Teste de compatibilidade: output é `List[Question]` com campos corretos

## Dev Notes

### Arquitetura do Módulo

O novo extrator NÃO substitui `parser.py` — ele coexiste. O `pipeline_v2.py` (Story 5.3) escolherá qual usar. O `parser.py` atual continua disponível como referência e para backward compatibility.

```
pymupdf4llm_extractor.py
├── import pymupdf.layout  (ANTES de pymupdf4llm!)
├── import pymupdf4llm
├── from parser import Question, QuestionMetadata, Subject, parse_filename, _determine_subject
├── from alternative_extractor import create_enhanced_extractor
└── from text_normalizer import normalize_enem_text
```

### API pymupdf4llm (v1.27.x) — Referência Rápida

```python
# Layout AI DEVE ser importado PRIMEIRO
import pymupdf.layout
import pymupdf4llm

# Extração para RAG (retorna list[dict] por página)
chunks = pymupdf4llm.to_markdown(
    "enem.pdf",
    page_chunks=True,       # list[dict] per page
    header=False,           # remove headers ENEM
    footer=False,           # remove page numbers
    write_images=True,      # salvar imagens em disco
    image_path="./images",
    image_format="png",
    dpi=150,
    force_ocr=False,        # True apenas para scanned
    ocr_language="por",     # Tesseract Portuguese
)
# chunks[i] = { 'metadata': {'page': N}, 'text': '...', 'tables': [...], 'images': [...] }

# Bounding boxes (para associar imagem→questão)
json_text = pymupdf4llm.to_json("enem.pdf", embed_images=True, image_dpi=150)
# data['pages'][i]['boxes'][j] = { 'boxclass': 'image', 'x0': ..., 'y0': ..., 'x1': ..., 'y1': ... }
```

### Padrão Atual do Parser (para compatibilidade)

O `parser.py` usa:
- `EnemPDFParser.parse_questions(pdf_path) -> List[Question]`
- `_extract_text_by_columns(page)` — manual split at 50% page width (pymupdf4llm elimina isso com Layout AI)
- `_extract_text_robust(page)` — multi-fallback extraction (não necessário com pymupdf4llm)
- `_extract_alternatives_with_context()` → delega para `EnhancedAlternativeExtractor`

O novo extrator DEVE produzir o mesmo formato `List[Question]` para que o downstream (`chunk_builder.py`, `embedding_generator.py`, `pgvector_writer.py`) funcione sem mudanças.

### Dataclasses a Reutilizar (de `parser.py`)

```python
@dataclass
class QuestionMetadata:
    year: int; day: int; caderno: str; application_type: str
    accessibility: Optional[str]; language: Optional[str]; exam_type: str

@dataclass
class Question:
    number: int; text: str; alternatives: List[str]
    metadata: QuestionMetadata; subject: Subject; context: Optional[str]
```

### Regex para Separação de Questões no Markdown

O pymupdf4llm produz markdown onde questões ENEM aparecem como:
```
**QUESTÃO 1**
Texto do enunciado...
**(A)** Alternativa A
**(B)** Alternativa B
...
```

Usar regex: `r'(?:QUESTÃO|Questão|questão)\s*(\d+)'` para split.

### Imagens — Estratégia de Associação

1. `to_markdown()` com `write_images=True` salva as imagens em disco
2. `to_json()` retorna bounding boxes de cada imagem e texto
3. Para cada questão (detectada por regex no markdown), determinar o range Y na página
4. Para cada imagem, verificar se `image.y0` está dentro do range Y da questão
5. Se overlap > 50%, associar a imagem à questão

### Anti-Patterns a Evitar

- **NÃO** reimplementar column detection — o Layout AI do pymupdf4llm já faz isso via ONNX
- **NÃO** cair de volta para pdfplumber — se a extração falhar, retornar a questão com dados parciais e deixar o confidence scorer (Story 5.2) decidir
- **NÃO** modificar `parser.py` — manter intacto como referência
- **NÃO** criar novos models SQLAlchemy — o pipeline usa raw SQL contra schema `enem_questions.*`
- **NÃO** instalar GPU dependencies — Layout AI roda em CPU via ONNX

### Conflito Potencial: PyMuPDF Versions

`requirements.txt` já lista `PyMuPDF>=1.26.5`. O `pymupdf4llm` instala sua própria versão do PyMuPDF. Verificar que não há conflito de versão. Se houver, usar a versão do pymupdf4llm (mais recente) e validar que `image_extractor.py` (que usa `fitz`) continua funcionando.

### Project Structure Notes

- Novo arquivo: `src/enem_ingestion/pymupdf4llm_extractor.py`
- Novo diretório de testes: `tests/test_pymupdf4llm_extractor.py`
- Imagens extraídas: `data/extracted_images/{year}/` (já existe `data/extracted_images/`)
- **NÃO** criar novos arquivos de schema SQL nesta story (schema changes são da Story 5.2)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1]
- [Source: src/enem_ingestion/parser.py — EnemPDFParser, Question dataclass, Subject enum]
- [Source: src/enem_ingestion/alternative_extractor.py — EnhancedAlternativeExtractor, create_enhanced_extractor()]
- [Source: src/enem_ingestion/text_normalizer.py — normalize_enem_text()]
- [Source: src/enem_ingestion/image_extractor.py — ImageExtractor, ExtractedImage (usa fitz)]
- [Source: pymupdf4llm docs — to_markdown(), to_json(), page_chunks, Layout AI]
- [Source: requirements.txt — PyMuPDF>=1.26.5 existente]

### Testing Standards

- Framework: `pytest` + `pytest-mock` (mocker fixture)
- Pattern: mock `pymupdf4llm.to_markdown` e `pymupdf4llm.to_json` — NÃO depender de PDFs reais no CI
- Naming: `test_extract_questions_text_only`, `test_extract_questions_multicolumn`, `test_extract_questions_with_images`
- Coverage: `--cov=src` (pytest.ini)
- No real PDF fixtures needed — mock retorna strings de markdown

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- pymupdf4llm_extractor.py: Layout AI, to_markdown, OCR detection, image bbox, EnhancedAlternativeExtractor
- 13 tests pass: text-only, multi-column, images, edge cases, OCR, filename integration

### File List

- src/enem_ingestion/pymupdf4llm_extractor.py (new)
- tests/test_pymupdf4llm_extractor.py (new)
- requirements.txt (modified — added pymupdf4llm>=1.27.0)