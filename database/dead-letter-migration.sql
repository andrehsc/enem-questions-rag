-- dead-letter-migration.sql
-- Story 6.2: Create dead_letter_questions table for manual review queue.
-- Idempotent — safe to run multiple times.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'enem_questions'
        AND table_name = 'dead_letter_questions'
    ) THEN
        CREATE TABLE enem_questions.dead_letter_questions (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            question_number INTEGER,
            pdf_filename VARCHAR(255) NOT NULL,
            page_numbers VARCHAR(50),
            raw_text TEXT NOT NULL,
            extraction_errors JSONB DEFAULT '[]',
            confidence_score FLOAT NOT NULL,
            extraction_method VARCHAR(30) NOT NULL,
            failed_layers TEXT[] NOT NULL DEFAULT '{}',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            resolved_by VARCHAR(100),
            resolved_at TIMESTAMP WITH TIME ZONE,
            resolution_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_dl_status CHECK (status IN ('pending', 'resolved', 'reingested'))
        );

        CREATE INDEX idx_dl_status ON enem_questions.dead_letter_questions(status);
        CREATE INDEX idx_dl_created_at ON enem_questions.dead_letter_questions(created_at);
    END IF;
END $$;
