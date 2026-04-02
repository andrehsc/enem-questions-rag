---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments:
  - docs/prd.md
  - docs/architecture.md
workflowType: 'architecture'
project_name: 'enem-questions-rag'
user_name: 'Deh'
date: '2026-04-02'
status: complete
---

# Architecture Decision Document — ENEM Questions RAG

> **Projeto:** enem-questions-rag  
> **Autor:** Deh  
> **Data:** 2026-04-02  
> **Escopo:** Pipeline de ingestão + RAG sobre questões ENEM, base para integração TeachersHub

---

## 1. Contexto do Projeto

### Visão Geral

O sistema tem dois estágios claramente separados:

**Estágio 1 — Core RAG (foco desta arquitetura):**
Download e extração precisa de questões de PDFs do INEP → chunking semântico → embeddings → busca vetorial no PostgreSQL (pgvector).

**Estágio 2 — Integração TeachersHub (objetivo final):**
- Busca semântica de questões por assunto/referência da prova → questão completa + gabarito
- Geração de avaliações de treino a partir das questões recuperadas
- Geração de novas questões por nível de dificuldade e assunto (RAG + LLM)

### Requisitos Arquiteturais Chave

| Requisito | Decisão |
|---|---|
| Fonte dos PDFs | Download automático do INEP (pipeline existente em `src/enem_ingestion/`) |
| Imagens nas questões | Extraídas para disco; referenciadas como metadado no chunk (path + descrição) |
| Modelo de embeddings | `text-embedding-3-small` (OpenAI) |
| Vector store | **pgvector** no PostgreSQL existente |
| LLM para geração | OpenAI GPT-4 / GPT-4o |
| Estratégia de chunking | **Híbrido 2 chunks por questão** (descrito abaixo) |
| Gabarito | Chunk separado linkado por `question_id` |
| Idempotência | Re-ingestão não duplica embeddings (hash do conteúdo como chave) |

### Complexidade do Projeto

- **Domínio:** Backend/ML/RAG
- **Complexidade:** Média-Alta (pipeline multi-etapa, integração OpenAI, pgvector)
- **Dados:** ~2.532 questões × 2 chunks = ~5.064 vetores base + chunks de gabarito e contexto
- **Custo OpenAI (embeddings):** ~$0.02 para todo o corpus (text-embedding-3-small a $0.02/1M tokens)

---

## 2. Stack Tecnológico

### Tecnologias Principais

| Componente | Tecnologia | Versão | Justificativa |
|---|---|---|---|
| Linguagem pipeline | Python | 3.11 | Ecossistema ML, compatível com ambiente existente |
| API | FastAPI | latest | Já em uso no projeto |
| Banco de dados | PostgreSQL | 15+ | Já em uso; suporta pgvector |
| Extensão vetorial | pgvector | 0.7+ | Nativo no PostgreSQL, sem infraestrutura extra |
| Embeddings | OpenAI `text-embedding-3-small` | API | Multilingual, alta qualidade, custo baixo |
| LLM geração | OpenAI `gpt-4o` | API | Geração de questões e avaliações |
| Extração PDF | pdfplumber | já instalado | Extração de texto de PDFs ENEM |
| OCR (imagens) | Tesseract + pytesseract | 5.x | Fallback para texto em imagens |
| Cache embeddings | Redis | já em uso | Evitar re-chamadas à API OpenAI |
| ORM | SQLAlchemy | 2.x | Compatível com pgvector-python |

### Dependências a Adicionar

```
pgvector                  # driver pgvector para Python/SQLAlchemy
openai>=1.0.0             # API embeddings + geração
pgvector-python           # integração pgvector + SQLAlchemy
tiktoken                  # contar tokens antes de chamar API
```

---

## 3. Estratégia de Chunking

### Decisão: Híbrido 2 Chunks por Questão

Cada questão gera **até 2 chunks** no banco vetorial:

#### Chunk 1 — `type: "full"` (sempre presente)
```
text = "[ENUNCIADO] {enunciado_texto}
        A) {alt_a}
        B) {alt_b}
        C) {alt_c}
        D) {alt_d}
        E) {alt_e}"
```
- Contém a questão completa para recuperação direta
- Usado para busca semântica (Feature 1) e geração de avaliações (Feature 2)

#### Chunk 2 — `type: "context"` (somente quando existe texto-base)
```
text = "{texto_base_da_questao}"
```
- Contém o contexto/texto-base separado
- Usado como inspiração para geração de novas questões (Feature 3)
- Presente apenas quando a questão tem texto-base identificável

#### Chunk 3 — `type: "answer"` (sempre presente, NÃO vetorizado)
```
text = "Gabarito: {letra_correta}"
stored_as = metadado relacionado (não entra no índice vetorial)
```
- Armazenado na tabela relacional como referência ao `question_id`
- Recuperado após a busca vetorial, nunca indexado como vetor

### Justificativa

| Benefício | Impacto |
|---|---|
| Questão completa em 1 hit vetorial | Feature 1 e 2 funcionam sem joins complexos |
| Contexto separado quando disponível | Feature 3 tem material rico para geração |
| Gabarito fora do vetor | Não contamina resultados de busca semântica |
| ~5k vetores total | Gerenciável sem infraestrutura pesada |

---

## 4. Schema do Banco de Dados

### Extensão pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Tabela de Chunks (vetores)

```sql
CREATE TABLE question_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    chunk_type      VARCHAR(20) NOT NULL CHECK (chunk_type IN ('full', 'context')),
    content         TEXT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 para idempotência
    embedding       vector(1536),                 -- text-embedding-3-small = 1536 dims
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice vetorial HNSW para busca rápida
CREATE INDEX ON question_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Índice por question_id para reconstituição
CREATE INDEX idx_chunks_question_id ON question_chunks (question_id);
CREATE INDEX idx_chunks_type ON question_chunks (chunk_type);
```

### Tabela de Imagens (referência)

```sql
CREATE TABLE question_images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    file_path       VARCHAR(500) NOT NULL,
    ocr_text        TEXT,                         -- texto extraído por OCR se disponível
    image_order     INTEGER DEFAULT 0,            -- ordem na questão
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Extensão da Tabela questions Existente

```sql
-- Adicionar campos para suporte ao pipeline RAG
ALTER TABLE questions ADD COLUMN IF NOT EXISTS
    ingestion_hash VARCHAR(64);                   -- evitar re-processamento
ALTER TABLE questions ADD COLUMN IF NOT EXISTS
    has_images BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS
    embedding_status VARCHAR(20) DEFAULT 'pending'
        CHECK (embedding_status IN ('pending', 'processing', 'done', 'error'));
```

---

## 5. Pipeline de Ingestão

### Fluxo Completo

```
PDFs INEP (download automático)
    │
    ▼
[1] PDF Parser (pdfplumber)
    - Extrai texto bruto por página
    - Detecta questões por regex (padrões ENEM)
    - Extrai alternativas (strategy pattern já implementado)
    - Identifica texto-base/contexto
    │
    ▼
[2] Image Extractor
    - Extrai imagens embarcadas nos PDFs
    - Salva em data/extracted_images/{ano}/{questao_id}/
    - Tenta OCR com Tesseract (pytesseract)
    - Registra path + ocr_text na tabela question_images
    │
    ▼
[3] Normalizer + Deduplicator
    - Normaliza encoding (mojibake correction — já implementado)
    - Calcula hash SHA-256 do conteúdo
    - Verifica se já foi ingerido (idempotência)
    │
    ▼
[4] Chunk Builder
    - Constrói chunk "full" (enunciado + alternativas)
    - Constrói chunk "context" se texto-base presente
    - Verifica content_hash antes de chamar API
    │
    ▼
[5] Embedding Generator
    - Chama OpenAI text-embedding-3-small em batches de 100
    - Usa tiktoken para validar token count (<8192)
    - Armazena resultado com content_hash (cache Redis TTL 7d)
    │
    ▼
[6] pgvector Writer
    - Insere/atualiza question_chunks via SQLAlchemy
    - Atualiza embedding_status na tabela questions
    - Log de ingestão estruturado
    │
    ▼
[7] Validation Report
    - Questões sem embedding
    - Chunks com hash duplicado
    - Erros de OCR
    - Custo total da sessão (tokens usados)
```

### Componentes do Pipeline

```
src/enem_ingestion/
├── parser.py                  # ✅ existente — extração de questões
├── alternative_extractor.py   # ✅ existente — strategy pattern
├── image_extractor.py         # ✅ existente — extração de imagens
├── text_normalizer.py         # ✅ existente — normalização encoding
├── chunk_builder.py           # 🆕 NOVO — estratégia híbrida 2 chunks
├── embedding_generator.py     # 🆕 NOVO — OpenAI text-embedding-3-small
├── pgvector_writer.py         # 🆕 NOVO — inserção no pgvector
├── ingestion_pipeline.py      # 🆕 NOVO — orquestrador do pipeline
└── config.py                  # ✅ existente — variáveis de ambiente
```

---

## 6. API de Busca RAG

### Endpoints Necessários

#### Busca Semântica (Feature 1)
```
POST /api/v1/search/semantic
Body: {
  "query": "questão sobre fotossíntese",
  "subject": "ciencias_natureza",   // opcional
  "year": 2023,                      // opcional
  "limit": 10,
  "include_answer": true             // inclui gabarito na resposta
}
Response: {
  "questions": [
    {
      "id": 42,
      "year": 2023,
      "subject": "ciencias_natureza",
      "full_text": "enunciado + alternativas",
      "correct_answer": "C",         // se include_answer=true
      "images": [...],
      "similarity_score": 0.91,
      "chunk_type": "full"
    }
  ]
}
```

#### Geração de Avaliação (Feature 2)
```
POST /api/v1/assessments/generate
Body: {
  "subject": "matematica",
  "difficulty": "medium",            // easy | medium | hard
  "question_count": 10,
  "years": [2020, 2021, 2022, 2023, 2024]  // opcional
}
Response: {
  "assessment_id": "uuid",
  "questions": [...],
  "answer_key": {...}
}
```

#### Geração de Novas Questões (Feature 3)
```
POST /api/v1/questions/generate
Body: {
  "subject": "historia",
  "topic": "Segunda Guerra Mundial",
  "difficulty": "hard",
  "count": 3,
  "style": "enem"                    // mantém formato ENEM
}
Response: {
  "generated_questions": [
    {
      "stem": "enunciado gerado",
      "alternatives": {"A": ..., "B": ..., "C": ..., "D": ..., "E": ...},
      "answer": "B",
      "explanation": "...",
      "source_context_ids": [...]    // chunks usados como contexto
    }
  ]
}
```

---

## 7. Padrões de Implementação

### Nomenclatura

| Contexto | Padrão | Exemplo |
|---|---|---|
| Tabelas SQL | snake_case plural | `question_chunks` |
| Colunas SQL | snake_case | `question_id`, `chunk_type` |
| Classes Python | PascalCase | `ChunkBuilder`, `EmbeddingGenerator` |
| Funções/métodos Python | snake_case | `build_chunks()`, `generate_embedding()` |
| Constantes Python | UPPER_SNAKE | `EMBEDDING_MODEL`, `MAX_TOKENS` |
| Endpoints API | kebab-case plural | `/api/v1/question-chunks` |
| Variáveis de ambiente | UPPER_SNAKE | `OPENAI_API_KEY`, `PGVECTOR_DIMENSION` |

### Formato de Resposta da API

```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 10
  },
  "error": null
}
```

### Formato de Erro

```json
{
  "data": null,
  "error": {
    "code": "EMBEDDING_FAILED",
    "message": "Falha ao gerar embedding para questão 42",
    "details": { "question_id": 42, "reason": "token_limit_exceeded" }
  }
}
```

### Padrão de Logging no Pipeline

```python
logger.info("chunk_built", extra={
    "question_id": question_id,
    "chunk_type": chunk_type,
    "token_count": tokens,
    "has_context": bool(context_text)
})
```

### Idempotência

- Todo chunk tem `content_hash` (SHA-256) como chave única
- Antes de chamar a API OpenAI, verificar se embedding já existe no Redis/PostgreSQL
- `ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW()` no insert

---

## 8. Estrutura do Projeto (RAG Core)

```
enem-questions-rag/
├── src/
│   ├── enem_ingestion/
│   │   ├── parser.py                   # ✅ extração de questões do PDF
│   │   ├── alternative_extractor.py    # ✅ strategy pattern alternativas
│   │   ├── image_extractor.py          # ✅ extração de imagens
│   │   ├── text_normalizer.py          # ✅ normalização encoding
│   │   ├── chunk_builder.py            # 🆕 chunking híbrido
│   │   ├── embedding_generator.py      # 🆕 OpenAI embeddings em batch
│   │   ├── pgvector_writer.py          # 🆕 escrita no pgvector
│   │   ├── ingestion_pipeline.py       # 🆕 orquestrador principal
│   │   └── config.py                   # ✅ configurações
│   └── rag_features/
│       ├── semantic_search.py          # ✅ atualizar para pgvector
│       ├── question_generator.py       # ✅ atualizar para Feature 3
│       ├── assessment_generator.py     # 🆕 Feature 2 — geração de avaliações
│       └── rag_pipeline.py             # 🆕 pipeline RAG completo
├── api/
│   ├── fastapi_app.py                  # ✅ adicionar novos endpoints
│   └── routes/
│       ├── search.py                   # 🆕 /api/v1/search/semantic
│       ├── assessments.py              # 🆕 /api/v1/assessments/generate
│       └── generation.py              # 🆕 /api/v1/questions/generate
├── database/
│   ├── init.sql                        # ✅ existente
│   ├── pgvector-migration.sql          # 🆕 ADD EXTENSION + tabelas vetoriais
│   └── indexes.sql                     # 🆕 índices HNSW
├── tests/
│   ├── test_chunk_builder.py           # 🆕
│   ├── test_embedding_generator.py     # 🆕
│   └── test_semantic_search.py         # 🆕
└── .env.example                        # 🆕 incluir OPENAI_API_KEY, PGVECTOR_*
```

---

## 9. Variáveis de Ambiente Necessárias

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_COMPLETION_MODEL=gpt-4o

# pgvector
PGVECTOR_DIMENSION=1536
PGVECTOR_INDEX_TYPE=hnsw          # hnsw ou ivfflat

# Pipeline
EMBEDDING_BATCH_SIZE=100          # chunks por chamada à API
EMBEDDING_CACHE_TTL=604800        # 7 dias em segundos (Redis)
MAX_TOKENS_PER_CHUNK=8000         # limite seguro para text-embedding-3-small

# Banco
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
```

---

## 10. Validação da Arquitetura

### Cobertura de Features

| Feature | Componentes Arquiteturais | Status |
|---|---|---|
| F1 — Busca por assunto | pgvector + semantic_search + `/search/semantic` | ✅ coberto |
| F2 — Geração de avaliações | question retriever + assessment_generator + `/assessments/generate` | ✅ coberto |
| F3 — Geração de novas questões | context chunks + GPT-4o RAG + `/questions/generate` | ✅ coberto |
| Pipeline idempotente | content_hash + Redis cache | ✅ coberto |
| Imagens referenciadas | question_images + metadado no chunk | ✅ coberto |
| Gabarito não contamina busca | answer chunk fora do índice vetorial | ✅ coberto |

### Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Rate limit OpenAI | Baixa | Batch de 100 + retry exponencial |
| Token limit em questões longas | Média | tiktoken valida antes de chamar API; truncagem com log |
| Custo inesperado de API | Baixa | Cache Redis; dashboard de tokens usados por sessão |
| Drift de schema pgvector | Baixa | Migrations versionadas em `database/` |
| Re-ingestão duplicando dados | Nenhuma | content_hash UNIQUE constraint |

### Decisões Irreversíveis

1. **pgvector em vez de ChromaDB** — requer extensão PostgreSQL instalada; migração futura custosa
2. **text-embedding-3-small (dim=1536)** — dimensão fixada no schema; mudança de modelo exige re-vetorização completa
3. **Chunking híbrido** — estratégia pode ser estendida mas não reduzida sem re-ingestão

---

## 11. Ordem de Implementação Recomendada

```
Sprint 1 — Fundação vetorial
  ├── pgvector-migration.sql (schema + extensão)
  ├── chunk_builder.py
  └── testes unitários do chunk_builder

Sprint 2 — Pipeline de embeddings
  ├── embedding_generator.py (com cache Redis)
  ├── pgvector_writer.py
  └── ingestion_pipeline.py (orquestrador)

Sprint 3 — Busca semântica (Feature 1)
  ├── Atualizar semantic_search.py para pgvector
  ├── Endpoint /api/v1/search/semantic
  └── Testes de integração

Sprint 4 — Geração (Features 2 e 3)
  ├── assessment_generator.py
  ├── Atualizar question_generator.py
  └── Endpoints /assessments/generate e /questions/generate
```
