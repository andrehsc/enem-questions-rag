-- ================================================================
-- ENEM RAG SYSTEM - COMPLETE DATABASE CREATION SCRIPT
-- ================================================================
-- This script creates the complete database schema for ENEM RAG system
-- Run this script as PostgreSQL superuser (postgres)
-- 
-- Usage:
--   psql -U postgres -c "CREATE DATABASE teachershub_enem;"
--   psql -U postgres -d teachershub_enem -f create_database_complete.sql
-- ================================================================

-- ================================================================
-- USERS AND PERMISSIONS
-- ================================================================

-- Create user and grant permissions
DROP USER IF EXISTS enem_rag_service;
CREATE USER enem_rag_service WITH PASSWORD 'enem123';
GRANT ALL PRIVILEGES ON DATABASE teachershub_enem TO enem_rag_service;

-- Create schema
DROP SCHEMA IF EXISTS enem_questions CASCADE;
CREATE SCHEMA IF NOT EXISTS enem_questions;
GRANT ALL PRIVILEGES ON SCHEMA enem_questions TO enem_rag_service;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA enem_questions GRANT ALL ON TABLES TO enem_rag_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA enem_questions GRANT ALL ON SEQUENCES TO enem_rag_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA enem_questions GRANT ALL ON FUNCTIONS TO enem_rag_service;

-- Set search path
SET search_path TO enem_questions, public;

-- ================================================================
-- TABLES CREATION
-- ================================================================

-- Table: exam_metadata
-- Stores metadata for each exam/caderno
CREATE TABLE exam_metadata (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    year INTEGER NOT NULL,
    exam_type VARCHAR(50), -- 'ENEM', 'PPL', etc.
    application_type VARCHAR(50) NOT NULL, -- 'regular', 'reaplicacao', etc.
    language VARCHAR(50), -- 'portuguese', 'spanish', 'english', etc.
    pdf_filename VARCHAR(255) NOT NULL,
    pdf_path TEXT,
    day INTEGER, -- 1 or 2
    caderno VARCHAR(10), -- CD1, CD2, etc.
    file_type VARCHAR(10) NOT NULL, -- 'PV' or 'GB'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_year CHECK (year >= 1998 AND year <= 2030),
    CONSTRAINT check_day CHECK (day IN (1, 2)),
    CONSTRAINT check_file_type CHECK (file_type IN ('PV', 'GB')),
    CONSTRAINT unique_exam_file UNIQUE (year, application_type, language, day, caderno, file_type)
);

-- Table: questions
-- Stores individual questions from exams
CREATE TABLE questions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    exam_id INTEGER, -- Sequential exam ID for compatibility
    exam_metadata_id UUID NOT NULL REFERENCES exam_metadata(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    competency TEXT,
    skill TEXT,
    question_text TEXT NOT NULL,
    question_html TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_question_number CHECK (question_number >= 1 AND question_number <= 180),
    CONSTRAINT unique_question_per_exam UNIQUE (exam_metadata_id, question_number)
);

-- Table: question_alternatives
-- Stores multiple choice alternatives for questions
CREATE TABLE question_alternatives (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    alternative_letter CHAR(1) NOT NULL,
    alternative_text TEXT NOT NULL,
    alternative_html TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_alternative_letter CHECK (alternative_letter IN ('A', 'B', 'C', 'D', 'E')),
    CONSTRAINT unique_alternative_per_question UNIQUE (question_id, alternative_letter)
);

-- Table: answer_keys
-- Stores correct answers (gabaritos) for questions
CREATE TABLE answer_keys (
    id SERIAL PRIMARY KEY,
    exam_year INTEGER NOT NULL,
    exam_type VARCHAR(50),
    question_number INTEGER NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    exam_metadata_id UUID NOT NULL REFERENCES exam_metadata(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_answer_letter CHECK (correct_answer IN ('A', 'B', 'C', 'D', 'E')),
    CONSTRAINT check_answer_question_number CHECK (question_number >= 1 AND question_number <= 180),
    CONSTRAINT unique_answer_per_exam UNIQUE (exam_metadata_id, question_number)
);

-- Table: question_images (for future image storage)
-- Stores image data and metadata for questions that contain images
CREATE TABLE question_images (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    image_sequence INTEGER NOT NULL DEFAULT 1,
    image_path TEXT,
    image_data BYTEA,
    image_format VARCHAR(10), -- 'PNG', 'JPG', etc.
    image_width INTEGER,
    image_height INTEGER,
    image_size_bytes INTEGER,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT check_image_sequence CHECK (image_sequence >= 1),
    CONSTRAINT unique_image_per_question UNIQUE (question_id, image_sequence)
);

-- ================================================================
-- INDEXES FOR PERFORMANCE
-- ================================================================

-- Indexes for exam_metadata
CREATE INDEX idx_exam_metadata_year ON exam_metadata(year);
CREATE INDEX idx_exam_metadata_type ON exam_metadata(exam_type);
CREATE INDEX idx_exam_metadata_application ON exam_metadata(application_type);
CREATE INDEX idx_exam_metadata_filename ON exam_metadata(pdf_filename);

-- Indexes for questions
CREATE INDEX idx_questions_exam_metadata ON questions(exam_metadata_id);
CREATE INDEX idx_questions_number ON questions(question_number);
CREATE INDEX idx_questions_subject ON questions(subject);
CREATE INDEX idx_questions_exam_id ON questions(exam_id);

-- Indexes for question_alternatives
CREATE INDEX idx_alternatives_question ON question_alternatives(question_id);
CREATE INDEX idx_alternatives_letter ON question_alternatives(alternative_letter);

-- Indexes for answer_keys
CREATE INDEX idx_answer_keys_exam_metadata ON answer_keys(exam_metadata_id);
CREATE INDEX idx_answer_keys_year ON answer_keys(exam_year);
CREATE INDEX idx_answer_keys_question_number ON answer_keys(question_number);

-- Indexes for question_images
CREATE INDEX idx_question_images_question ON question_images(question_id);
CREATE INDEX idx_question_images_sequence ON question_images(image_sequence);

-- ================================================================
-- FUNCTIONS AND TRIGGERS
-- ================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for exam_metadata
CREATE TRIGGER update_exam_metadata_updated_at 
    BEFORE UPDATE ON exam_metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate sequential exam_id
CREATE OR REPLACE FUNCTION generate_exam_id()
RETURNS TRIGGER AS $$
DECLARE
    max_exam_id INTEGER;
BEGIN
    IF NEW.exam_id IS NULL THEN
        SELECT COALESCE(MAX(exam_id), 0) + 1 INTO max_exam_id FROM questions;
        NEW.exam_id = max_exam_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for questions to auto-generate exam_id
CREATE TRIGGER generate_question_exam_id 
    BEFORE INSERT ON questions 
    FOR EACH ROW EXECUTE FUNCTION generate_exam_id();

-- ================================================================
-- VIEWS FOR CONVENIENCE
-- ================================================================

-- View: complete_questions
-- Joins questions with exam metadata and alternatives
CREATE VIEW complete_questions AS
SELECT 
    q.id as question_id,
    q.exam_id,
    q.question_number,
    q.subject,
    q.competency,
    q.skill,
    q.question_text,
    em.year,
    em.exam_type,
    em.application_type,
    em.language,
    em.day,
    em.caderno,
    ak.correct_answer
FROM questions q
JOIN exam_metadata em ON q.exam_metadata_id = em.id
LEFT JOIN answer_keys ak ON em.id = ak.exam_metadata_id AND q.question_number = ak.question_number;

-- View: exam_statistics
-- Provides statistics about exams
CREATE VIEW exam_statistics AS
SELECT 
    em.year,
    em.exam_type,
    em.application_type,
    em.day,
    COUNT(DISTINCT q.id) as total_questions,
    COUNT(DISTINCT qa.id) as total_alternatives,
    COUNT(DISTINCT ak.id) as total_answers,
    COUNT(DISTINCT q.subject) as total_subjects
FROM exam_metadata em
LEFT JOIN questions q ON em.id = q.exam_metadata_id
LEFT JOIN question_alternatives qa ON q.id = qa.question_id  
LEFT JOIN answer_keys ak ON em.id = ak.exam_metadata_id
GROUP BY em.year, em.exam_type, em.application_type, em.day
ORDER BY em.year DESC, em.day;

-- ================================================================
-- GRANTS FOR ENEM_RAG_SERVICE USER
-- ================================================================

-- Grant permissions on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA enem_questions TO enem_rag_service;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA enem_questions TO enem_rag_service;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA enem_questions TO enem_rag_service;

-- ================================================================
-- COMPLETION MESSAGE
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE 'ENEM RAG DATABASE SCHEMA CREATED SUCCESSFULLY!';
    RAISE NOTICE 'Tables created: exam_metadata, questions, question_alternatives, answer_keys, question_images';
    RAISE NOTICE 'Views created: complete_questions, exam_statistics';
    RAISE NOTICE 'User created: enem_rag_service with full permissions';
    RAISE NOTICE 'Ready for data ingestion!';
END $$;
