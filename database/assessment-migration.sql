-- Assessment tables migration (Story 4.1)
-- UP: Create assessment tracking tables

CREATE TABLE IF NOT EXISTS enem_questions.assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500),
    subject         VARCHAR(100) NOT NULL,
    difficulty      VARCHAR(20) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard', 'mixed')),
    question_count  INTEGER NOT NULL CHECK (question_count BETWEEN 1 AND 50),
    years_filter    INTEGER[],
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enem_questions.assessment_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID NOT NULL REFERENCES enem_questions.assessments(id) ON DELETE CASCADE,
    question_id     INTEGER NOT NULL REFERENCES enem_questions.questions(id),
    question_order  INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_assessment_question UNIQUE (assessment_id, question_id),
    CONSTRAINT uq_assessment_order UNIQUE (assessment_id, question_order)
);

CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment_id
    ON enem_questions.assessment_questions (assessment_id);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_question_id
    ON enem_questions.assessment_questions (question_id);
CREATE INDEX IF NOT EXISTS idx_assessments_subject
    ON enem_questions.assessments (subject);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at
    ON enem_questions.assessments (created_at DESC);

-- DOWN: Revert migration
-- DROP TABLE IF EXISTS enem_questions.assessment_questions;
-- DROP TABLE IF EXISTS enem_questions.assessments;
