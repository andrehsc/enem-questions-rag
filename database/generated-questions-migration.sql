-- Migration: generated_questions table (Story 4.2)
-- AI-generated questions stored separately from real ENEM corpus

CREATE TABLE IF NOT EXISTS enem_questions.generated_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject         VARCHAR(100) NOT NULL,
    topic           VARCHAR(255) NOT NULL,
    difficulty      VARCHAR(20) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    style           VARCHAR(50) NOT NULL DEFAULT 'enem',
    stem            TEXT NOT NULL,
    context_text    TEXT,
    alternatives    JSONB NOT NULL,
    answer          CHAR(1) NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D', 'E')),
    explanation     TEXT NOT NULL,
    source_context_ids UUID[] NOT NULL DEFAULT '{}',
    model_used      VARCHAR(50) NOT NULL DEFAULT 'gpt-4o',
    requested_by    VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gen_questions_subject
    ON enem_questions.generated_questions (subject);
CREATE INDEX IF NOT EXISTS idx_gen_questions_created_at
    ON enem_questions.generated_questions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gen_questions_requested_by
    ON enem_questions.generated_questions (requested_by);
CREATE INDEX IF NOT EXISTS idx_gen_questions_difficulty
    ON enem_questions.generated_questions (difficulty);

-- DOWN: Revert migration
-- DROP TABLE IF EXISTS enem_questions.generated_questions;
