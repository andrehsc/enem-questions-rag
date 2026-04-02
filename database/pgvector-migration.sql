-- =============================================================
-- MIGRATION: pgvector + Chunking Schema
-- Story: 1.1 — Migration pgvector e Schema Vetorial
-- Date: 2026-04-02
-- Description: Adiciona suporte a embeddings vetoriais para o
--              pipeline RAG de questões ENEM usando pgvector.
-- =============================================================
-- IDEMPOTENTE: pode ser executado múltiplas vezes sem erro.
-- =============================================================

-- Garantir extensão vector (já definida em complete-init.sql, mas seguro repetir)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- TABELA: question_chunks
-- Armazena chunks de texto gerados a partir de questões ENEM,
-- com embeddings vetoriais para busca semântica.
-- Estratégia híbrida: 'full' (enunciado+alternativas) + 'context'
-- (texto-base separado, quando existir).
-- =============================================================
CREATE TABLE IF NOT EXISTS enem_questions.question_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL
                        REFERENCES enem_questions.questions(id)
                        ON DELETE CASCADE,
    chunk_type      VARCHAR(20) NOT NULL
                        CHECK (chunk_type IN ('full', 'context')),
    content         TEXT NOT NULL,
    -- SHA-256 hex do content (64 chars) — chave de idempotência do pipeline
    content_hash    VARCHAR(64) NOT NULL,
    -- Dimensão 1536 = text-embedding-3-small da OpenAI
    -- NULL até o embedding_generator.py preencher (pipeline em 2 fases)
    embedding       vector(1536),
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uk_question_chunks_hash UNIQUE (content_hash)
);

-- Índice vetorial HNSW para busca por similaridade cosseno
-- HNSW preferível a IVFFlat para corpus <100k vetores (sem VACUUM periódico)
-- m=16 e ef_construction=64 são valores padrão equilibrados
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'enem_questions'
          AND tablename  = 'question_chunks'
          AND indexname  = 'idx_question_chunks_embedding'
    ) THEN
        CREATE INDEX idx_question_chunks_embedding
            ON enem_questions.question_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_question_chunks_question_id
    ON enem_questions.question_chunks (question_id);

CREATE INDEX IF NOT EXISTS idx_question_chunks_type
    ON enem_questions.question_chunks (chunk_type);

-- =============================================================
-- TABELA: question_images
-- Registra imagens extraídas dos PDFs ENEM, com caminho para
-- o arquivo em disco e texto OCR opcional (Tesseract).
-- =============================================================
CREATE TABLE IF NOT EXISTS enem_questions.question_images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL
                        REFERENCES enem_questions.questions(id)
                        ON DELETE CASCADE,
    -- Caminho relativo à raiz do projeto: data/extracted_images/...
    file_path       VARCHAR(500) NOT NULL,
    -- Texto extraído por OCR; NULL se imagem não tem texto ou OCR não foi executado
    ocr_text        TEXT,
    -- Ordem da imagem dentro da questão (0-indexed)
    image_order     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uk_question_images_path UNIQUE (question_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_question_images_question_id
    ON enem_questions.question_images (question_id);

-- =============================================================
-- ALTER TABLE: enem_questions.questions
-- Adiciona colunas para suporte ao pipeline de ingestão RAG.
-- ATENÇÃO: has_images JÁ EXISTE na tabela — não recriar.
-- =============================================================

-- ingestion_hash: SHA-256 do conteúdo bruto da questão extraída do PDF.
-- Permite que o pipeline detecte questões já processadas e pule re-ingestão.
ALTER TABLE enem_questions.questions
    ADD COLUMN IF NOT EXISTS ingestion_hash VARCHAR(64);

-- embedding_status: rastreia progresso do pipeline de embeddings por questão.
--   pending    → questão ingerida, embedding não gerado ainda
--   processing → embedding sendo gerado (uso futuro para pipeline paralelo)
--   done       → embedding gerado e gravado em question_chunks
--   error      → falha na geração do embedding (ver logs para detalhes)
ALTER TABLE enem_questions.questions
    ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(20) DEFAULT 'pending';

-- Adicionar constraint de check separadamente (compatível com ADD COLUMN IF NOT EXISTS)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_questions_embedding_status'
    ) THEN
        ALTER TABLE enem_questions.questions
            ADD CONSTRAINT chk_questions_embedding_status
            CHECK (embedding_status IN ('pending', 'processing', 'done', 'error'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_questions_embedding_status
    ON enem_questions.questions (embedding_status);

CREATE INDEX IF NOT EXISTS idx_questions_ingestion_hash
    ON enem_questions.questions (ingestion_hash)
    WHERE ingestion_hash IS NOT NULL;

-- =============================================================
-- VERIFICAÇÃO FINAL
-- =============================================================
DO $$
DECLARE
    chunks_exists  BOOLEAN;
    images_exists  BOOLEAN;
    hash_col       BOOLEAN;
    status_col     BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'enem_questions' AND table_name = 'question_chunks'
    ) INTO chunks_exists;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'enem_questions' AND table_name = 'question_images'
    ) INTO images_exists;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'enem_questions'
          AND table_name   = 'questions'
          AND column_name  = 'ingestion_hash'
    ) INTO hash_col;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'enem_questions'
          AND table_name   = 'questions'
          AND column_name  = 'embedding_status'
    ) INTO status_col;

    RAISE NOTICE 'Migration 1.1 pgvector — Resultado:';
    RAISE NOTICE '  question_chunks:  %', CASE WHEN chunks_exists THEN 'OK' ELSE 'FALHOU' END;
    RAISE NOTICE '  question_images:  %', CASE WHEN images_exists THEN 'OK' ELSE 'FALHOU' END;
    RAISE NOTICE '  ingestion_hash:   %', CASE WHEN hash_col      THEN 'OK' ELSE 'FALHOU' END;
    RAISE NOTICE '  embedding_status: %', CASE WHEN status_col    THEN 'OK' ELSE 'FALHOU' END;

    IF NOT (chunks_exists AND images_exists AND hash_col AND status_col) THEN
        RAISE EXCEPTION 'Migration 1.1 incompleta — verifique erros acima.';
    END IF;

    RAISE NOTICE 'Migration 1.1 concluida com sucesso.';
END
$$;

-- =============================================================
-- DOWN MIGRATION (executar apenas para reverter)
-- =============================================================
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_embedding;
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_question_id;
-- DROP INDEX IF EXISTS enem_questions.idx_question_chunks_type;
-- DROP INDEX IF EXISTS enem_questions.idx_question_images_question_id;
-- DROP INDEX IF EXISTS enem_questions.idx_questions_embedding_status;
-- DROP INDEX IF EXISTS enem_questions.idx_questions_ingestion_hash;
-- DROP TABLE IF EXISTS enem_questions.question_chunks CASCADE;
-- DROP TABLE IF EXISTS enem_questions.question_images CASCADE;
-- ALTER TABLE enem_questions.questions DROP CONSTRAINT IF EXISTS chk_questions_embedding_status;
-- ALTER TABLE enem_questions.questions DROP COLUMN IF EXISTS ingestion_hash;
-- ALTER TABLE enem_questions.questions DROP COLUMN IF EXISTS embedding_status;
