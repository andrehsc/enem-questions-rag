-- Script de inicialização do banco PostgreSQL para Docker

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Configurar busca textual em português
CREATE TEXT SEARCH CONFIGURATION portuguese_unaccent (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portuguese_unaccent
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;

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
DROP TABLE IF EXISTS "question_alternatives" CASCADE;
DROP TABLE IF EXISTS "answer_keys" CASCADE;
DROP TABLE IF EXISTS "questions" CASCADE;
DROP TABLE IF EXISTS "exam_metadata" CASCADE;

-- ========================================
-- CORE TABLES
-- ========================================

-- Create exam_metadata table (stores PDF file metadata)
CREATE TABLE "exam_metadata" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "year" integer NOT NULL,
    "day" integer NOT NULL CHECK ("day" IN (1, 2)),
    "caderno" varchar(10) NOT NULL, -- CD1, CD2, etc.
    "application_type" varchar(50) NOT NULL DEFAULT 'regular', -- regular, reaplicacao_PPL
    "accessibility" varchar(50), -- libras, braille_ledor, PPL
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
CREATE TABLE "questions" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_number" integer NOT NULL,
    "question_text" text NOT NULL,
    "context_text" text, -- Supporting text/images description
    "subject" varchar(50) NOT NULL, -- linguagens, ciencias_humanas, ciencias_natureza, matematica
    "exam_metadata_id" uuid NOT NULL,
    "raw_text" text, -- Raw extracted text for debugging
    "parsing_confidence" decimal(3,2), -- 0.00 to 1.00
    "has_images" boolean DEFAULT FALSE,
    "images_description" text,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    "updated_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_questions" PRIMARY KEY ("id"),
    CONSTRAINT "fk_questions_exam_metadata" FOREIGN KEY ("exam_metadata_id") 
        REFERENCES "exam_metadata" ("id") ON DELETE CASCADE,
    CONSTRAINT "uk_questions_number_exam" UNIQUE ("question_number", "exam_metadata_id")
);

-- Create question_alternatives table (stores multiple choice alternatives)
CREATE TABLE "question_alternatives" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_id" uuid NOT NULL,
    "alternative_letter" char(1) NOT NULL CHECK ("alternative_letter" IN ('A', 'B', 'C', 'D', 'E')),
    "alternative_text" text NOT NULL,
    "alternative_order" integer NOT NULL DEFAULT 0,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_question_alternatives" PRIMARY KEY ("id"),
    CONSTRAINT "fk_alternatives_questions" FOREIGN KEY ("question_id") 
        REFERENCES "questions" ("id") ON DELETE CASCADE,
    CONSTRAINT "uk_alternatives_letter_question" UNIQUE ("alternative_letter", "question_id")
);

-- Create answer_keys table (stores correct answers from gabaritos)
CREATE TABLE "answer_keys" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "question_number" integer NOT NULL,
    "correct_answer" char(1) NOT NULL CHECK ("correct_answer" IN ('A', 'B', 'C', 'D', 'E')),
    "subject" varchar(50) NOT NULL,
    "language_option" varchar(20), -- ingles, espanhol (for language questions)
    "exam_metadata_id" uuid NOT NULL,
    "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "pk_answer_keys" PRIMARY KEY ("id"),
    CONSTRAINT "fk_answer_keys_exam_metadata" FOREIGN KEY ("exam_metadata_id") 
        REFERENCES "exam_metadata" ("id") ON DELETE CASCADE,
    CONSTRAINT "uk_answer_keys_question_exam_lang" UNIQUE ("question_number", "exam_metadata_id", "language_option")
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Exam metadata indexes
CREATE INDEX "idx_exam_metadata_year" ON "exam_metadata" ("year");
CREATE INDEX "idx_exam_metadata_year_day" ON "exam_metadata" ("year", "day");
CREATE INDEX "idx_exam_metadata_caderno" ON "exam_metadata" ("caderno");
CREATE INDEX "idx_exam_metadata_application_type" ON "exam_metadata" ("application_type");
CREATE INDEX "idx_exam_metadata_accessibility" ON "exam_metadata" ("accessibility");
CREATE INDEX "idx_exam_metadata_created_at" ON "exam_metadata" ("created_at");

-- Questions indexes
CREATE INDEX "idx_questions_number" ON "questions" ("question_number");
CREATE INDEX "idx_questions_subject" ON "questions" ("subject");
CREATE INDEX "idx_questions_exam_metadata_id" ON "questions" ("exam_metadata_id");
CREATE INDEX "idx_questions_number_subject" ON "questions" ("question_number", "subject");
CREATE INDEX "idx_questions_confidence" ON "questions" ("parsing_confidence");
CREATE INDEX "idx_questions_has_images" ON "questions" ("has_images");

-- Question alternatives indexes
CREATE INDEX "idx_alternatives_question_id" ON "question_alternatives" ("question_id");
CREATE INDEX "idx_alternatives_letter" ON "question_alternatives" ("alternative_letter");
CREATE INDEX "idx_alternatives_question_order" ON "question_alternatives" ("question_id", "alternative_order");

-- Answer keys indexes
CREATE INDEX "idx_answer_keys_question_number" ON "answer_keys" ("question_number");
CREATE INDEX "idx_answer_keys_subject" ON "answer_keys" ("subject");
CREATE INDEX "idx_answer_keys_exam_metadata_id" ON "answer_keys" ("exam_metadata_id");
CREATE INDEX "idx_answer_keys_language_option" ON "answer_keys" ("language_option");

-- Full-text search indexes (for RAG queries)
CREATE INDEX "idx_questions_text_search" ON "questions" USING gin(to_tsvector('portuguese', "question_text"));
CREATE INDEX "idx_alternatives_text_search" ON "question_alternatives" USING gin(to_tsvector('portuguese', "alternative_text"));
CREATE INDEX "idx_context_text_search" ON "questions" USING gin(to_tsvector('portuguese', "context_text"));

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
CREATE TRIGGER update_exam_metadata_updated_at BEFORE UPDATE ON "exam_metadata"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON "questions"
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
        (SELECT COUNT(*) FROM "exam_metadata"),
        (SELECT COUNT(*) FROM "questions"),
        (SELECT COUNT(*) FROM "question_alternatives"),
        (SELECT ROUND(AVG("parsing_confidence"), 3) FROM "questions" WHERE "parsing_confidence" IS NOT NULL),
        (SELECT COUNT(*) FROM "questions" WHERE "has_images" = TRUE),
        (SELECT ARRAY_AGG(DISTINCT "year" ORDER BY "year") FROM "exam_metadata");
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
    FROM "questions" q
    JOIN "exam_metadata" em ON q."exam_metadata_id" = em."id"
    WHERE to_tsvector('portuguese', q."question_text") @@ plainto_tsquery('portuguese', search_text)
    ORDER BY similarity_score DESC
    LIMIT limit_count;
END;
$$ language 'plpgsql';

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- Create views for common queries
CREATE VIEW "questions_with_answers" AS
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
FROM "questions" q
JOIN "exam_metadata" em ON q."exam_metadata_id" = em."id"
LEFT JOIN "answer_keys" ak ON ak."question_number" = q."question_number" 
    AND ak."exam_metadata_id" = em."id"
    AND ak."subject" = q."subject";

CREATE VIEW "exam_summary" AS
SELECT 
    em."year",
    em."day",
    em."caderno",
    em."application_type",
    em."accessibility",
    COUNT(q."id") as questions_count,
    COUNT(ak."id") as answers_count,
    AVG(q."parsing_confidence") as avg_confidence
FROM "exam_metadata" em
LEFT JOIN "questions" q ON q."exam_metadata_id" = em."id"
LEFT JOIN "answer_keys" ak ON ak."exam_metadata_id" = em."id"
GROUP BY em."id", em."year", em."day", em."caderno", em."application_type", em."accessibility"
ORDER BY em."year" DESC, em."day", em."caderno";

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE '=== ENEM Questions RAG Database Schema ===';
    RAISE NOTICE 'Schema created successfully!';
    RAISE NOTICE 'Tables created: 4 (exam_metadata, questions, question_alternatives, answer_keys)';
    RAISE NOTICE 'Indexes created: 15 (including full-text search)';
    RAISE NOTICE 'Views created: 2 (questions_with_answers, exam_summary)';
    RAISE NOTICE 'Functions created: 3 (update_updated_at_column, get_parsing_stats, find_similar_questions)';
    RAISE NOTICE 'Ready for ENEM PDF parsing and RAG operations!';
END $$;
