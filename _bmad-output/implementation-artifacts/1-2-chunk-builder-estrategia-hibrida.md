# Story 1.2: Chunk Builder — Estratégia Híbrida

**Status:** done  
**Epic:** 1 — Fundação Vetorial: pgvector + Chunk Builder  
**Story ID:** 1.2  
**Story Key:** `1-2-chunk-builder-estrategia-hibrida`

---

## Story

Como desenvolvedor,  
Quero um módulo `chunk_builder.py` que produza chunks híbridos de questões ENEM,  
Para que cada questão seja representada por até 2 chunks (`full` + `context`) com metadados ricos e hash de idempotência.

---

## Acceptance Criteria

1. Questão **com** `context_text` gera exatamente 2 chunks: `full` (enunciado + alternativas) e `context` (texto-base)
2. Questão **sem** `context_text` (null ou vazio) gera exatamente 1 chunk: `full`
3. Cada chunk inclui `content_hash` SHA-256 (64 chars hex) para idempotência de inserção no pgvector
4. `token_count` calculado via `tiktoken` (encoding `cl100k_base`) antes de retornar o chunk
5. Chunks com mais de 8000 tokens são **truncados** ao limite com log `WARNING` indicando `question_id` e tipo do chunk
6. Testes unitários (sem DB) cobrem: questão simples, questão com texto-base, questão matemática curta, questão com imagem (`has_images=True`)

---

## Tasks / Subtasks

- [x] **Task 1: Criar `src/enem_ingestion/chunk_builder.py`** (AC: 1, 2, 3, 4, 5)
  - [x] 1.1 Definir dataclass `ChunkData` com campos: `question_id`, `chunk_type`, `content`, `content_hash`, `token_count`, `metadata`
  - [x] 1.2 Implementar função `build_chunks(question_text, alternatives, context_text, question_id, metadata)` → `List[ChunkData]`
  - [x] 1.3 Formatar chunk `full`: `"[ENUNCIADO] {question_text}\nA) {alt_a}\nB) {alt_b}\nC) {alt_c}\nD) {alt_d}\nE) {alt_e}"`
  - [x] 1.4 Formatar chunk `context`: apenas `context_text` (somente se não-null e não-vazio após strip)
  - [x] 1.5 Calcular `content_hash` via `hashlib.sha256(content.encode()).hexdigest()` (retorna 64 chars)
  - [x] 1.6 Calcular `token_count` via `tiktoken.get_encoding("cl100k_base").encode(content)`
  - [x] 1.7 Implementar truncamento: se `len(tokens) > 8000`, truncar conteúdo e logar `WARNING` com `question_id` + `chunk_type`
  - [x] 1.8 Expor função helper `build_chunks_from_db_row(row_dict) → List[ChunkData]` para uso com queries SQLAlchemy

- [x] **Task 2: Criar `tests/test_chunk_builder.py`** (AC: 6)
  - [x] 2.1 `test_simple_question_generates_one_full_chunk` — sem context_text → 1 chunk tipo `full`
  - [x] 2.2 `test_question_with_context_generates_two_chunks` — com context_text → 2 chunks, tipos `full` e `context`
  - [x] 2.3 `test_full_chunk_format_contains_alternatives` — verificar formato `[ENUNCIADO] ... A) ... B) ...`
  - [x] 2.4 `test_content_hash_is_64_char_hex` — hash tem 64 chars, é SHA-256 correto
  - [x] 2.5 `test_token_count_is_calculated` — `token_count > 0` para chunk com conteúdo
  - [x] 2.6 `test_truncation_at_8000_tokens_logs_warning` — chunk com >8000 tokens é truncado e logger.warning é chamado
  - [x] 2.7 `test_question_with_images_metadata` — questão com `has_images=True` preserva metadado no chunk
  - [x] 2.8 `test_short_math_question_no_context` — questão matemática curta gera apenas `full` sem crash

---

## Dev Notes

### Localização do arquivo

**Criar:** `src/enem_ingestion/chunk_builder.py`  
**Testes:** `tests/test_chunk_builder.py` (unit tests, sem banco de dados)

> **NUNCA** criar em outro pacote ou fora de `src/enem_ingestion/`. Não modificar outros módulos no pacote.

### Estrutura do ChunkData

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ChunkData:
    chunk_type: str          # 'full' | 'context'
    content: str             # texto do chunk
    content_hash: str        # SHA-256 hex, 64 chars
    token_count: int         # contagem tiktoken cl100k_base
    question_id: Optional[str] = None   # UUID string; None antes de persistir
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Ex metadata: {"year": 2023, "subject": "matematica", "question_number": 42, "has_images": False}
```

### Assinatura da função principal

```python
def build_chunks(
    question_text: str,
    alternatives: list[str],    # lista de strings — pode ser ["A) texto", "B) texto"] OU ["texto", "texto"]
    context_text: Optional[str] = None,
    question_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> list[ChunkData]:
```

### Formato exato do chunk `full`

```
[ENUNCIADO] {question_text}
A) {alt_a}
B) {alt_b}
C) {alt_c}
D) {alt_d}
E) {alt_e}
```

- As alternativas podem chegar como `["A) texto A", "B) texto B", ...]` (já com letra) **ou** como `["texto A", "texto B", ...]` (sem letra).
- O builder deve detectar e normalizar: se a string já começa com `"A)"`, `"B)"`, etc., use como está; caso contrário, prefixe com `"A) "`, `"B) "`, etc. usando a posição na lista (índice 0 = A).
- Se a lista de alternativas estiver vazia, o chunk `full` contém apenas o enunciado (sem seção de alternativas).

### Formato exato do chunk `context`

```
{context_text}  ← exatamente o texto-base, sem prefixo
```

- Produzir **somente se** `context_text is not None` **e** `context_text.strip() != ""`

### Cálculo do content_hash

```python
import hashlib

content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
# Retorna string hexadecimal de 64 caracteres
```

> O hash deve ser calculado **após** a montagem e formatação do conteúdo, mas **antes** do truncamento. Assim o hash é determinístico em relação ao conteúdo original integral. Se truncar, logar o hash original.

**ATENÇÃO:** O hash é calculado ANTES do truncamento para garantir idempotência — o hash representa a questão original completa.

### Token count com tiktoken

```python
import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")  # instanciar uma vez no nível do módulo

token_count = len(_ENC.encode(content))
```

> `cl100k_base` é o encoding correto para `text-embedding-3-small` (mesma família de tokens usada pela OpenAI para embeddings).

### Truncamento

```python
MAX_TOKENS = 8000

if token_count > MAX_TOKENS:
    logger.warning(
        "Chunk truncado: question_id=%s chunk_type=%s tokens_originais=%d tokens_limite=%d",
        question_id, chunk_type, token_count, MAX_TOKENS,
    )
    tokens = _ENC.encode(content)
    content = _ENC.decode(tokens[:MAX_TOKENS])
    token_count = MAX_TOKENS
```

### Função helper para queries DB

```python
def build_chunks_from_db_row(row: dict) -> list[ChunkData]:
    """
    Converte um dict com dados de uma questão (resultado de query SQLAlchemy) 
    em lista de ChunkData.

    row deve ter: 'question_text', 'alternatives' (list[str] | list[dict]),
    'context_text', 'id' (UUID str), 'subject', 'year', 'question_number', 'has_images'
    """
```

- `row["alternatives"]` pode ser:
  - `list[str]` — lista de textos em ordem (A, B, C, D, E)
  - `list[dict]` — como `[{"letter": "A", "text": "..."}]`
  - O helper deve normalizar para `list[str]` no formato `"A) texto"` antes de chamar `build_chunks`

### Schema do banco (referência Story 1.1)

Tabela destino dos chunks: `enem_questions.question_chunks`

| Coluna | Tipo | Mapeamento |
|--------|------|------------|
| `question_id` | `UUID` | `ChunkData.question_id` |
| `chunk_type` | `VARCHAR(20)` `CHECK ('full','context')` | `ChunkData.chunk_type` |
| `content` | `TEXT` | `ChunkData.content` |
| `content_hash` | `VARCHAR(64)` `UNIQUE` | `ChunkData.content_hash` |
| `token_count` | `INTEGER` | `ChunkData.token_count` |
| `embedding` | `vector(1536)` | preenchido depois na Story 2.1 |

> `question_id` na tabela `questions` é `UUID` (não INTEGER). O ORM legado em `database.py` usa INTEGER — **ignorar o ORM legado**; o chunk_builder não usa SQLAlchemy, apenas constrói os dados.

### Dependências a adicionar ao requirements.txt

```
tiktoken>=0.7.0
```

> `tiktoken` ainda não está no `requirements.txt`. **Adicionar** antes de implementar.

Comando para instalar no venv:
```bash
pip install tiktoken>=0.7.0
```

### Sobre a classe `Question` do parser.py

O módulo `parser.py` define:

```python
@dataclass
class Question:
    number: int
    text: str            # ← este é o question_text (enunciado)
    alternatives: List[str]  # ← lista de strings, formato pode variar
    metadata: QuestionMetadata
    subject: Optional[Subject] = None
    context: Optional[str] = None  # ← este é o context_text (texto-base)
```

Quando o chunk builder for chamado a partir do parser (pipeline online), usar:
```python
build_chunks(
    question_text=q.text,
    alternatives=q.alternatives,
    context_text=q.context,
    question_id=None,   # ainda não salvo no DB
    metadata={"year": q.metadata.year, "subject": q.subject.value if q.subject else None, ...}
)
```

### O que NÃO fazer

- **Não** criar modelos SQLAlchemy neste módulo (isso vem na Story 2.2)
- **Não** fazer chamadas à API OpenAI (isso vem na Story 2.1: embedding_generator)
- **Não** conectar ao banco de dados (este módulo é puro Python)
- **Não** modificar `parser.py`, `text_normalizer.py`, `database.py` ou `config.py`
- **Não** usar ChromaDB em nenhum contexto

### Aprendizados da Story 1.1

- Banco de dados rodando em Docker, porta `5433`, user `postgres`, password `postgres123` (role `enem_rag_service` **não existe**)
- `questions.id` é `UUID` na tabela real (não INTEGER como no ORM legado em `database.py`)
- Testes de integração requerem `RUN_INTEGRATION_TESTS=true` como env var

### Project Structure Notes

Alinhamento com estrutura definida na arquitetura:

```
src/enem_ingestion/
├── parser.py                  # ✅ existente
├── alternative_extractor.py   # ✅ existente
├── image_extractor.py         # ✅ existente
├── text_normalizer.py         # ✅ existente
├── chunk_builder.py           # 🆕 CRIAR AQUI (esta story)
├── embedding_generator.py     # 🆕 Story 2.1
├── pgvector_writer.py         # 🆕 Story 2.2
├── ingestion_pipeline.py      # 🆕 Story 2.3
└── config.py                  # ✅ existente
```

### Referências

- Estratégia de chunking híbrida: [_bmad-output/planning-artifacts/architecture.md](../../_bmad-output/planning-artifacts/architecture.md) — Seção 3
- Schema pgvector: [database/pgvector-migration.sql](../../database/pgvector-migration.sql)
- Estrutura Question (parser): [src/enem_ingestion/parser.py](../../src/enem_ingestion/parser.py#L73)
- Story 1.1 concluída: [_bmad-output/implementation-artifacts/1-1-migration-pgvector-e-schema-vetorial.md](./1-1-migration-pgvector-e-schema-vetorial.md)
- tiktoken docs: [https://github.com/openai/tiktoken](https://github.com/openai/tiktoken) — encoding `cl100k_base` cobre modelos `text-embedding-3-*` e GPT-4

---

## Arquivos a Criar/Modificar

| Ação | Arquivo | Descrição |
|------|---------|-----------|
| **CRIAR** | `src/enem_ingestion/chunk_builder.py` | Módulo principal do chunk builder |
| **CRIAR** | `tests/test_chunk_builder.py` | Testes unitários (sem banco) |
| **MODIFICAR** | `requirements.txt` | Adicionar `tiktoken>=0.7.0` |

---

## Dependências (desta story)

- ✅ Story 1.1 concluída (schema pgvector já existe no banco)
- Python padrão: `hashlib` (built-in), `dataclasses` (built-in), `logging` (built-in)
- `tiktoken` — adicionar ao requirements.txt

## Não faz parte desta story

- Modelos SQLAlchemy para `question_chunks` → Story 2.2
- Chamadas à API OpenAI de embeddings → Story 2.1
- Inserção no banco de dados → Story 2.2
- Testes de integração com banco real → Story 1.3

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (GitHub Copilot)

### Debug Log References

- tiktoken 0.7.0 já estava presente no requirements.txt — nenhuma modificação necessária.
- 23 testes unitários criados, todos passando. Cobertura de 100% no chunk_builder.py.
- Hash calculado ANTES do truncamento conforme spec (idempotência garantida).

### Completion Notes List

- ✅ `ChunkData` dataclass criada com todos os campos requeridos.
- ✅ `build_chunks()` implementado: questão sem context → 1 chunk `full`; com context → 2 chunks.
- ✅ Formato `[ENUNCIADO] ... \nA) ... \nB) ...` implementado com normalização de alternativas (prefixadas ou não).
- ✅ `content_hash` SHA-256 de 64 chars calculado do conteúdo original antes do truncamento.
- ✅ `token_count` via tiktoken `cl100k_base` com encoding instanciado uma vez no nível do módulo.
- ✅ Truncamento ao limite de 8000 tokens com `logger.warning` contendo `question_id` + `chunk_type`.
- ✅ `build_chunks_from_db_row()` normaliza `list[str]` e `list[dict]` de alternativas.
- ✅ 23 testes criados cobrindo todos os ACs (incluindo testes extras de edge cases).
- ✅ Code review: corrigido uso do campo `letter` em alternativas dict fora de ordem (`_normalize_alternatives`).
- ✅ Code review: `content_hash` adicionado ao log de truncamento conforme spec.
- ✅ Novo teste `test_dict_alternatives_respect_letter_field` cobrindo alternativas fora de ordem.
- ✅ Teste de truncamento atualizado para verificar `content_hash` no log. 24 testes passando, cobertura 100%.

### File List

- `src/enem_ingestion/chunk_builder.py` — criado
- `tests/test_chunk_builder.py` — criado

### Change Log

- 2026-04-02: Implementação inicial da Story 1.2 — Chunk Builder com estratégia híbrida. Criados chunk_builder.py e test_chunk_builder.py. 23 testes passando, cobertura 100%.
- 2026-04-02: Correções pós code-review — (HIGH) `_normalize_alternatives` agora respeita campo `letter` em dicts fora de ordem; (MEDIUM) `content_hash` adicionado ao log de WARNING de truncamento. Novo teste + 1 teste atualizado. 24 testes, cobertura 100%. Status → done.
