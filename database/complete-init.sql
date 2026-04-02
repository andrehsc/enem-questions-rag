-- Script de inicialização do banco PostgreSQL para Docker

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Configurar busca textual em português
CREATE TEXT SEARCH CONFIGURATION portuguese_unaccent (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portuguese_unaccent
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;

-- Criar schema para o projeto ENEM RAG
CREATE SCHEMA IF NOT EXISTS enem_questions;

-- Garantir que as tabelas existam (serão criadas via migration se necessário)
-- Este arquivo serve principalmente para extensões e configurações iniciais
-- ========================================
-- ENEM QUESTIONS RAG DATABASE SCHEMA
-- Schema completo para armazenamento de questões do ENEM
-- Versão: 1.0 - Otimizada para RAG pipeline
-- ========================================

-- Configurações iniciais
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS enem_questions."question_alternatives" CASCADE;
DROP TABLE IF EXISTS enem_questions."answer_keys" CASCADE;
DROP TABLE IF EXISTS enem_questions."questions" CASCADE;
DROP TABLE IF EXISTS enem_questions."exam_metadata" CASCADE;
DROP TABLE IF EXISTS enem_questions."question_embeddings" CASCADE;

-- ========================================
-- CORE TABLES
-- ========================================

-- Create exam_metadata table (stores PDF file metadata)
CREATE TABLE enem_questions."exam_metadata" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "year" integer NOT NULL,
    "day" integer NOT NULL CHECK ("day" IN (1, 2)),
    "caderno" varchar(10) NOT NULL, -- CD1, CD2, etc.
    "application_type" varchar(50) NOT NULL DEFAULT 'regular', -- regular, reaplicacao_PPL
    "accessibility" varchar(50), -- libras, braille_ledor, PPL
    "exam_type" varchar(50), -- ENEM, PPL, ENEM_DIGITAL
    "language" varchar(20) DEFAULT 'portuguese', -- portuguese, spanish, english
    "file_type" varchar(20) NOT NULL, -- caderno_questoes, gabarito
    "pdf_filename" varchar(255) NOT NULL,
    "pdf_path" text,
    "file_size" bigint,
    "pages_count" integer,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    "updated_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_exam_metadata" PRIMARY KEY ("id"),
    CONSTRAINT "uk_exam_metadata_filename" UNIQUE ("pdf_filename")
);

-- Create questions table (stores parsed questions)
CREATE TABLE enem_questions."questions" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_number" integer NOT NULL,
    "question_text" text NOT NULL,
    "context_text" text, -- Supporting text/images description
    "subject" varchar(50) NOT NULL, -- linguagens, ciencias_humanas, ciencias_natureza, matematica
    "exam_metadata_id" uuid NOT NULL,
    "raw_text" text, -- Raw extracted text for debugging
    "parsing_confidence" decimal(4,3) DEFAULT 0.000,
    "has_images" boolean DEFAULT false,
    "images_description" text,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    "updated_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_questions" PRIMARY KEY ("id"),
    CONSTRAINT "fk_questions_exam_metadata" FOREIGN KEY ("exam_metadata_id") 
        REFERENCES enem_questions."exam_metadata" ("id") ON DELETE CASCADE
    -- Removed unique constraint to allow re-ingestion without conflicts
);

-- Create question_alternatives table (stores multiple choice alternatives)
CREATE TABLE enem_questions."question_alternatives" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_id" uuid NOT NULL,
    "alternative_letter" char(1) NOT NULL CHECK ("alternative_letter" IN ('A', 'B', 'C', 'D', 'E')),
    "alternative_text" text NOT NULL,
    "alternative_order" integer NOT NULL DEFAULT 0,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_question_alternatives" PRIMARY KEY ("id"),
    CONSTRAINT "fk_alternatives_questions" FOREIGN KEY ("question_id") 
        REFERENCES enem_questions."questions" ("id") ON DELETE CASCADE,
    CONSTRAINT "uk_alternatives_letter_question" UNIQUE ("alternative_letter", "question_id")
);

-- Create answer_keys table (stores correct answers from gabaritos)
CREATE TABLE enem_questions."answer_keys" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_number" integer NOT NULL,
    "correct_answer" char(1) NOT NULL CHECK ("correct_answer" IN ('A', 'B', 'C', 'D', 'E')),
    "subject" varchar(50), -- Made optional to prevent NULL constraint errors
    "language_option" varchar(20), -- ingles, espanhol (for language questions)
    "exam_year" integer NOT NULL, -- Year for easier querying
    "exam_type" varchar(50), -- ENEM, PPL, etc.
    "exam_metadata_id" uuid NOT NULL,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_answer_keys" PRIMARY KEY ("id"),
    CONSTRAINT "fk_answer_keys_exam_metadata" FOREIGN KEY ("exam_metadata_id") 
        REFERENCES enem_questions."exam_metadata" ("id") ON DELETE CASCADE
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Exam metadata indexes
CREATE INDEX "idx_exam_metadata_year" ON enem_questions."exam_metadata" ("year");
CREATE INDEX "idx_exam_metadata_year_day" ON enem_questions."exam_metadata" ("year", "day");
CREATE INDEX "idx_exam_metadata_caderno" ON enem_questions."exam_metadata" ("caderno");
CREATE INDEX "idx_exam_metadata_application_type" ON enem_questions."exam_metadata" ("application_type");
CREATE INDEX "idx_exam_metadata_accessibility" ON enem_questions."exam_metadata" ("accessibility");
CREATE INDEX "idx_exam_metadata_exam_type" ON enem_questions."exam_metadata" ("exam_type");
CREATE INDEX "idx_exam_metadata_language" ON enem_questions."exam_metadata" ("language");
CREATE INDEX "idx_exam_metadata_created_at" ON enem_questions."exam_metadata" ("created_at");

-- Questions indexes
CREATE INDEX "idx_questions_number" ON enem_questions."questions" ("question_number");
CREATE INDEX "idx_questions_subject" ON enem_questions."questions" ("subject");
CREATE INDEX "idx_questions_exam_metadata_id" ON enem_questions."questions" ("exam_metadata_id");
CREATE INDEX "idx_questions_number_subject" ON enem_questions."questions" ("question_number", "subject");
CREATE INDEX "idx_questions_confidence" ON enem_questions."questions" ("parsing_confidence");
CREATE INDEX "idx_questions_has_images" ON enem_questions."questions" ("has_images");

-- Question alternatives indexes
CREATE INDEX "idx_alternatives_question_id" ON enem_questions."question_alternatives" ("question_id");
CREATE INDEX "idx_alternatives_letter" ON enem_questions."question_alternatives" ("alternative_letter");
CREATE INDEX "idx_alternatives_question_order" ON enem_questions."question_alternatives" ("question_id", "alternative_order");

-- Answer keys indexes
CREATE INDEX "idx_answer_keys_question_number" ON enem_questions."answer_keys" ("question_number");
CREATE INDEX "idx_answer_keys_subject" ON enem_questions."answer_keys" ("subject");
CREATE INDEX "idx_answer_keys_exam_metadata_id" ON enem_questions."answer_keys" ("exam_metadata_id");
CREATE INDEX "idx_answer_keys_language_option" ON enem_questions."answer_keys" ("language_option");
CREATE INDEX "idx_answer_keys_exam_year" ON enem_questions."answer_keys" ("exam_year");
CREATE INDEX "idx_answer_keys_exam_type" ON enem_questions."answer_keys" ("exam_type");

-- Full-text search indexes (for RAG queries)
CREATE INDEX "idx_questions_text_search" ON enem_questions."questions" USING gin(to_tsvector('portuguese', "question_text"));
CREATE INDEX "idx_alternatives_text_search" ON enem_questions."question_alternatives" USING gin(to_tsvector('portuguese', "alternative_text"));
CREATE INDEX "idx_context_text_search" ON enem_questions."questions" USING gin(to_tsvector('portuguese', "context_text"));

-- ========================================
-- FUNCTIONS AND TRIGGERS
-- ========================================

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updated_at" = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating timestamps
CREATE TRIGGER update_exam_metadata_updated_at BEFORE UPDATE ON enem_questions."exam_metadata"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON enem_questions."questions"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate parsing statistics
CREATE OR REPLACE FUNCTION get_parsing_stats()
RETURNS TABLE(
    total_exams bigint,
    total_questions bigint,
    total_alternatives bigint,
    avg_confidence numeric,
    questions_with_images bigint,
    years_covered integer[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM enem_questions."exam_metadata"),
        (SELECT COUNT(*) FROM enem_questions."questions"),
        (SELECT COUNT(*) FROM enem_questions."question_alternatives"),
        (SELECT ROUND(AVG("parsing_confidence"), 3) FROM enem_questions."questions" WHERE "parsing_confidence" IS NOT NULL),
        (SELECT COUNT(*) FROM enem_questions."questions" WHERE "has_images" = TRUE),
        (SELECT ARRAY_AGG(DISTINCT "year" ORDER BY "year") FROM enem_questions."exam_metadata");
END;
$$ language 'plpgsql';

-- Function to find similar questions (for RAG)
CREATE OR REPLACE FUNCTION find_similar_questions(search_text text, limit_count integer DEFAULT 10)
RETURNS TABLE(
    question_id uuid,
    question_number integer,
    question_text text,
    subject varchar(50),
    year integer,
    similarity_score real
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q."id",
        q."question_number",
        q."question_text",
        q."subject",
        em."year",
        ts_rank(to_tsvector('portuguese', q."question_text"), plainto_tsquery('portuguese', search_text)) as similarity_score
    FROM enem_questions."questions" q
    JOIN enem_questions."exam_metadata" em ON q."exam_metadata_id" = em."id"
    WHERE to_tsvector('portuguese', q."question_text") @@ plainto_tsquery('portuguese', search_text)
    ORDER BY similarity_score DESC
    LIMIT limit_count;
END;
$$ language 'plpgsql';

-- ========================================
-- AI/VECTOR EXTENSION TABLES
-- ========================================

-- Create question_embeddings table for vector similarity search
CREATE TABLE IF NOT EXISTS enem_questions.question_embeddings (
    id SERIAL PRIMARY KEY,
    question_id UUID NOT NULL,
    embedding_vector vector(384),
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'sentence-transformers',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_question_embeddings_question_id 
        FOREIGN KEY (question_id) 
        REFERENCES enem_questions."questions"(id) 
        ON DELETE CASCADE,
    CONSTRAINT unique_question_model 
        UNIQUE (question_id, embedding_model)
);

-- Create vector similarity index for efficient cosine similarity search
CREATE INDEX IF NOT EXISTS idx_question_embeddings_vector 
ON enem_questions.question_embeddings 
USING ivfflat (embedding_vector vector_cosine_ops) 
WITH (lists = 100);

-- Create question_images table for image storage and processing
CREATE TABLE IF NOT EXISTS enem_questions.question_images (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL,
    image_sequence INTEGER NOT NULL DEFAULT 1,
    image_data BYTEA, -- Binary image data
    image_format VARCHAR(10) NOT NULL, -- PNG, JPEG, etc.
    image_width INTEGER,
    image_height INTEGER,
    image_size_bytes INTEGER,
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_question_images PRIMARY KEY (id),
    CONSTRAINT fk_question_images_question_id 
        FOREIGN KEY (question_id) 
        REFERENCES enem_questions."questions"(id) 
        ON DELETE CASCADE,
    CONSTRAINT uk_question_image_sequence 
        UNIQUE (question_id, image_sequence)
);

-- Index for question_images
CREATE INDEX IF NOT EXISTS idx_question_images_question_id 
ON enem_questions.question_images (question_id);

CREATE INDEX IF NOT EXISTS idx_question_images_sequence 
ON enem_questions.question_images (image_sequence);

CREATE INDEX IF NOT EXISTS idx_question_images_format 
ON enem_questions.question_images (image_format);

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- Create views for common queries
CREATE VIEW enem_questions."questions_with_answers" AS
SELECT 
    q."id",
    q."question_number",
    q."question_text",
    q."subject",
    em."year",
    em."day",
    em."caderno",
    ak."correct_answer",
    ak."language_option"
FROM enem_questions."questions" q
JOIN enem_questions."exam_metadata" em ON q."exam_metadata_id" = em."id"
LEFT JOIN enem_questions."answer_keys" ak ON ak."question_number" = q."question_number" 
    AND ak."exam_metadata_id" = em."id"
    AND ak."subject" = q."subject";

CREATE VIEW enem_questions."exam_summary" AS
SELECT 
    em."year",
    em."day",
    em."caderno",
    em."application_type",
    em."accessibility",
    COUNT(q."id") as questions_count,
    COUNT(ak."id") as answers_count,
    AVG(q."parsing_confidence") as avg_confidence
FROM enem_questions."exam_metadata" em
LEFT JOIN enem_questions."questions" q ON q."exam_metadata_id" = em."id"
LEFT JOIN enem_questions."answer_keys" ak ON ak."exam_metadata_id" = em."id"
GROUP BY em."id", em."year", em."day", em."caderno", em."application_type", em."accessibility"
ORDER BY em."year" DESC, em."day", em."caderno";

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE '=== ENEM Questions RAG Database Schema ===';
    RAISE NOTICE 'Schema created successfully!';
    RAISE NOTICE 'Tables created: 6 (exam_metadata, questions, question_alternatives, answer_keys, question_embeddings, question_images)';
    RAISE NOTICE 'Indexes created: 20 (including full-text search and vector similarity)';
    RAISE NOTICE 'Views created: 2 (questions_with_answers, exam_summary)';
    RAISE NOTICE 'Functions created: 3 (update_updated_at_column, get_parsing_stats, find_similar_questions)';
    RAISE NOTICE 'Added fields: exam_type, language, exam_year in answer_keys';
    RAISE NOTICE 'Ready for ENEM PDF parsing and RAG operations!';
END $$;
