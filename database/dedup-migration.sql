-- Dedup columns for Epic 8 (Story 8.4)
-- Adds content_hash and canonical_question_id for cross-booklet deduplication

ALTER TABLE enem_questions.questions
    ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16),
    ADD COLUMN IF NOT EXISTS canonical_question_id UUID DEFAULT NULL;

-- Unique index so we can do conflict-based dedup during ingestion
CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_content_hash
    ON enem_questions.questions (content_hash)
    WHERE content_hash IS NOT NULL;

-- Index for quick lookup of duplicates by canonical ID
CREATE INDEX IF NOT EXISTS idx_questions_canonical
    ON enem_questions.questions (canonical_question_id)
    WHERE canonical_question_id IS NOT NULL;
