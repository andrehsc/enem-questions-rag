-- Hybrid Search Migration: tsvector column + GIN index on question_chunks
-- Story 7.2: pgvector + tsvector com RRF

-- Add tsvector column to question_chunks
ALTER TABLE enem_questions.question_chunks
    ADD COLUMN IF NOT EXISTS tsv_content tsvector;

-- Populate tsvector from existing content using portuguese_unaccent config
UPDATE enem_questions.question_chunks
SET tsv_content = to_tsvector('portuguese_unaccent', content)
WHERE tsv_content IS NULL;

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_question_chunks_tsv
    ON enem_questions.question_chunks USING gin(tsv_content);

-- Trigger to keep tsvector updated on INSERT/UPDATE
CREATE OR REPLACE FUNCTION enem_questions.update_tsv_content()
RETURNS trigger AS $$
BEGIN
    NEW.tsv_content := to_tsvector('portuguese_unaccent', NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_tsv_content
    ON enem_questions.question_chunks;
CREATE TRIGGER trg_update_tsv_content
    BEFORE INSERT OR UPDATE OF content
    ON enem_questions.question_chunks
    FOR EACH ROW
    EXECUTE FUNCTION enem_questions.update_tsv_content();
