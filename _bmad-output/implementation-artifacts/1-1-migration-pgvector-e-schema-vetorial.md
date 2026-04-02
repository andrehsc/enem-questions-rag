# Story 1.1: Migration pgvector e Schema Vetorial

**Epic:** 1 — Fundação Vetorial  
**Story:** 1.1  
**Status:** done  
**Criado:** 2026-04-02  

---

## Story

Como desenvolvedor,  
Quero criar as tabelas e extensões necessárias no PostgreSQL para armazenar embeddings de questões ENEM,  
Para que o sistema possa persistir e consultar vetores usando pgvector.

---

## Contexto Crítico para Implementação

### Ambiente Existente

- **PostgreSQL:** container Docker `pgvector/pgvector:pg16` (já tem pgvector nativo), porta `5433` externa
- **Database:** `teachershub_enem`
- **Schema existente:** `enem_questions` (schema separado — TODAS as tabelas ficam sob este schema)
- **Docker Compose:** `docker-compose.yml` na raiz do projeto
- **Init SQL:** `database/complete-init.sql` — executado pelo Docker na inicialização (via `docker-entrypoint-initdb.d/`)
- **`pgvector` já está no `complete-init.sql`:** linha `CREATE EXTENSION IF NOT EXISTS "vector";`

### Tabelas Existentes (schema `enem_questions`)

```
enem_questions.exam_metadata     — metadados dos PDFs (year, day, caderno, etc.)
enem_questions.questions         — questões extraídas (id UUID, question_text, context_text, subject, has_images, etc.)
enem_questions.question_alternatives — alternativas A-E por questão
enem_questions.answer_keys       — gabaritos
```

### Coluna `questions.id` é UUID (não INTEGER!)

O schema existente usa `UUID` como PK em todas as tabelas, não `INTEGER`. Atenção ao criar FKs.

### Configuração de Conexão (de `src/enem_ingestion/config.py`)

```python
DATABASE_URL = "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
DB_PORT = 5433  # porta externa do Docker
```

---

## Critérios de Aceite

- [x] Extensão `vector` já existe — confirmar com `\dx` que está ativa; não recriar se já existe
- [x] Tabela `enem_questions.question_chunks` criada com coluna `embedding vector(1536)` e índice HNSW
- [x] Tabela `enem_questions.question_images` criada com campos de referência e texto OCR
- [x] Colunas `ingestion_hash`, `embedding_status` adicionadas à tabela `enem_questions.questions` — a coluna `has_images` **já existe** no schema, não adicionar de novo
- [x] Migration é idempotente (`IF NOT EXISTS` / `IF NOT EXISTS` em toda instrução)
- [x] Migration documentada com down migration (seção `-- DOWN MIGRATION`)
- [x] Arquivo SQL salvo em `database/pgvector-migration.sql`
- [x] Testes de integração em `tests/test_pgvector_schema.py` passam

---

## Tarefas

### Task 1: Criar `database/pgvector-migration.sql`

✅ **Concluída** — arquivo criado em `database/pgvector-migration.sql`

#### 1.1 — Confirmar extensão vector (já existe no complete-init.sql)
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 1.2 — Tabela `question_chunks`
```sql
CREATE TABLE IF NOT EXISTS enem_questions.question_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL REFERENCES enem_questions.questions(id) ON DELETE CASCADE,
    chunk_type      VARCHAR(20) NOT NULL CHECK (chunk_type IN ('full', 'context')),
    content         TEXT NOT NULL,
    content_hash    VARCHAR(64) NOT NULL,   -- SHA-256 hex (64 chars)
    embedding       vector(1536),           -- text-embedding-3-small = 1536 dims; NULL até ser gerado
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uk_question_chunks_hash UNIQUE (content_hash)
);
```

**Índices:**
```sql
-- Índice vetorial HNSW para busca por similaridade cosseno
CREATE INDEX IF NOT EXISTS idx_question_chunks_embedding
    ON enem_questions.question_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Índice para reconstituição da questão por question_id
CREATE INDEX IF NOT EXISTS idx_question_chunks_question_id
    ON enem_questions.question_chunks (question_id);

-- Índice para filtrar por tipo de chunk
CREATE INDEX IF NOT EXISTS idx_question_chunks_type
    ON enem_questions.question_chunks (chunk_type);
```

#### 1.3 — Tabela `question_images`
```sql
CREATE TABLE IF NOT EXISTS enem_questions.question_images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL REFERENCES enem_questions.questions(id) ON DELETE CASCADE,
    file_path       VARCHAR(500) NOT NULL,  -- relativo à raiz do projeto: data/extracted_images/...
    ocr_text        TEXT,                   -- texto extraído por OCR (Tesseract), NULL se sem OCR
    image_order     INTEGER DEFAULT 0,      -- ordem da imagem dentro da questão
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uk_question_images_path UNIQUE (question_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_question_images_question_id
    ON enem_questions.question_images (question_id);
```

#### 1.4 — Adicionar colunas à tabela `questions` existente
```sql
-- ingestion_hash: SHA-256 do conteúdo da questão para idempotência do pipeline
ALTER TABLE enem_questions.questions
    ADD COLUMN IF NOT EXISTS ingestion_hash VARCHAR(64);

-- embedding_status: rastreia estado do pipeline de embeddings
ALTER TABLE enem_questions.questions
    ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(20) DEFAULT 'pending'
    CONSTRAINT chk_embedding_status CHECK (embedding_status IN ('pending', 'processing', 'done', 'error'));

CREATE INDEX IF NOT EXISTS idx_questions_embedding_status
    ON enem_questions.questions (embedding_status);
```

> ⚠️ NÃO adicionar `has_images` — já existe na tabela `questions`

#### 1.5 — DOWN MIGRATION (documentada em comentário)
```sql
-- DOWN MIGRATION (executar apenas para reverter):
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_embedding;
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_question_id;
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_type;
-- DROP INDEX IF EXISTS enem_questions.idx_question_images_question_id;
-- DROP INDEX IF EXISTS enem_questions.idx_questions_embedding_status;
-- DROP TABLE IF EXISTS enem_questions.question_chunks CASCADE;
-- DROP TABLE IF EXISTS enem_questions.question_images CASCADE;
-- ALTER TABLE enem_questions.questions DROP COLUMN IF EXISTS ingestion_hash;
-- ALTER TABLE enem_questions.questions DROP COLUMN IF EXISTS embedding_status;
```

---

### Task 2: Criar `tests/test_pgvector_schema.py`

✅ **Concluída** — 15 testes criados e passando (15/15)

**Setup:** usar conexão `DATABASE_URL` do ambiente (`.env` ou variável de sistema).

#### Testes obrigatórios:

1. **`test_extension_vector_exists`** — verifica que extensão `vector` está ativa
2. **`test_question_chunks_table_exists`** — verifica que a tabela foi criada
3. **`test_insert_chunk_with_mock_embedding`** — insere chunk com embedding `[0.1] * 1536` e recupera por `question_id`
4. **`test_content_hash_unique_constraint`** — tenta inserir dois chunks com mesmo hash, espera `IntegrityError`
5. **`test_embedding_status_check_constraint`** — tenta inserir status inválido, espera `IntegrityError`
6. **`test_hnsw_similarity_search`** — insere 3 chunks com embeddings diferentes, faz busca `<=>` e verifica ordenação por distância
7. **`test_cascade_delete`** — deleta questão pai, verifica que chunks filhos também são deletados
8. **`test_migration_idempotent`** — executa a migration duas vezes sem erro

**Estrutura de fixtures:**
```python
@pytest.fixture
def db_session():
    """Sessão SQLAlchemy com rollback após cada teste."""
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        yield session
        session.rollback()

@pytest.fixture
def sample_question_id(db_session):
    """Retorna UUID de questão existente no banco para usar como FK."""
    result = db_session.execute(
        text("SELECT id FROM enem_questions.questions LIMIT 1")
    ).fetchone()
    assert result is not None, "Banco deve ter pelo menos 1 questão para testes de integração"
    return result[0]
```

---

### Task 3: Executar e validar a migration

Após criar o arquivo SQL:

```bash
# Com Docker rodando:
docker exec -i teachershub-enem-postgres psql \
    -U postgres \
    -d teachershub_enem \
    < database/pgvector-migration.sql

# Verificar resultado:
docker exec teachershub-enem-postgres psql \
    -U postgres \
    -d teachershub_enem \
    -c "\dt enem_questions.*"

# Verificar índice HNSW:
docker exec teachershub-enem-postgres psql \
    -U postgres \
    -d teachershub_enem \
    -c "\di enem_questions.*embedding*"
```

---

## Notas de Implementação

### Por que HNSW e não IVFFlat?

HNSW é preferível para o tamanho do corpus (~5k vetores): não requer `VACUUM` periódico nem parâmetro `lists`, e tem melhor recall. IVFFlat seria mais eficiente apenas acima de ~100k vetores.

### Por que `content_hash VARCHAR(64)` e não UUID?

O hash SHA-256 do conteúdo textual do chunk é usado como chave de idempotência. Usar o próprio hash como identificador (em vez de gerar UUID e comparar separadamente) simplifica a query de deduplicação:
```sql
INSERT INTO question_chunks (...) VALUES (...)
ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW();
```

### `embedding` aceita NULL

O campo `embedding vector(1536)` é nullable intencionalmente. Chunks são inseridos primeiro (com hash) e o embedding é preenchido depois pelo `embedding_generator.py` (Sprint 2). Isso permite que o pipeline seja interrompido e retomado.

### Schema `enem_questions` — atenção

Todas as queries devem usar o schema explicitamente: `enem_questions.question_chunks`, não apenas `question_chunks`. O `search_path` do container Docker pode não incluir `enem_questions` por padrão.

---

## Arquivos a Criar/Modificar

| Ação | Arquivo | Descrição |
|------|---------|-----------|
| **CRIAR** | `database/pgvector-migration.sql` | Migration principal |
| **CRIAR** | `tests/test_pgvector_schema.py` | Testes de integração |
| **NÃO MODIFICAR** | `database/complete-init.sql` | Script de init Docker — não alterar |
| **NÃO MODIFICAR** | `database/init.sql` | Init legado — não alterar |
| **NÃO MODIFICAR** | `src/enem_ingestion/database.py` | Models SQLAlchemy — serão estendidos na Story 2.2 |

---

## Dependências

- Docker com PostgreSQL rodando (`docker-compose up -d postgres`)
- Python com `sqlalchemy`, `psycopg2` (já no `requirements.txt`)
- `pytest` para testes de integração

## Não faz parte desta story

- Modelos SQLAlchemy para `question_chunks` → Story 2.2
- Lógica de chunking → Story 1.2
- Geração de embeddings → Story 2.1
- Qualquer lógica Python de pipeline

---

## Dev Agent Record

**Implementado por:** GitHub Copilot  
**Data de conclusão:** 2025-07-16  
**Status final:** ✅ done

### Arquivos criados
- `database/pgvector-migration.sql` — Migration idempotente para pgvector
- `tests/test_pgvector_schema.py` — 15 testes de integração

### Resultado dos testes
```
15 passed in 3.18s
```
Todos os 15 testes passaram com sucesso.

### Decisões de implementação
- `CAST(:emb AS vector)` em vez de `:emb::vector` — SQLAlchemy interpreta `::` como parâmetro nomeado
- Credenciais de conexão: `postgres:postgres123@localhost:5433/teachershub_enem` (role `enem_rag_service` não existe)
- Índice HNSW com `m=16, ef_construction=64` para corpus de ~5k vetores
- Coluna `embedding` nullable — chunks inseridos antes, embeddings preenchidos depois (Sprint 2)
