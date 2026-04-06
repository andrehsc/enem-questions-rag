-- extraction-v2-migration.sql
-- Story 5.2: Add confidence scoring and extraction method columns
-- Idempotent — safe to run multiple times.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'enem_questions'
        AND table_name = 'questions'
        AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE enem_questions.questions ADD COLUMN confidence_score FLOAT DEFAULT NULL;
        ALTER TABLE enem_questions.questions ADD COLUMN extraction_method VARCHAR(30) DEFAULT 'pdfplumber';
        ALTER TABLE enem_questions.questions ADD COLUMN extraction_errors JSONB DEFAULT NULL;
        ALTER TABLE enem_questions.questions ADD CONSTRAINT chk_extraction_method
            CHECK (extraction_method IN ('pdfplumber', 'pymupdf4llm', 'azure_di', 'manual'));
        CREATE INDEX idx_questions_confidence ON enem_questions.questions(confidence_score);
        CREATE INDEX idx_questions_extraction_method ON enem_questions.questions(extraction_method);
    END IF;
END $$;
