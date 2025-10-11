-- Otimizações para busca textual no PostgreSQL

-- Criar índices de busca textual (Full Text Search)
CREATE INDEX IF NOT EXISTS idx_questions_search 
ON questions USING gin(to_tsvector('portuguese', question_text));

CREATE INDEX IF NOT EXISTS idx_alternatives_search 
ON question_alternatives USING gin(to_tsvector('portuguese', alternative_text));

-- Índices compostos para filtros comuns
CREATE INDEX IF NOT EXISTS idx_questions_year_subject 
ON questions (exam_metadata_id) 
INCLUDE (question_number, question_text);

CREATE INDEX IF NOT EXISTS idx_exam_metadata_filters 
ON exam_metadata (year, application_type) 
WHERE year IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_answer_keys_subject 
ON answer_keys (subject, exam_metadata_id) 
WHERE subject IS NOT NULL;

-- Estatísticas para otimizador
ANALYZE questions;
ANALYZE question_alternatives;
ANALYZE answer_keys;
ANALYZE exam_metadata;

-- Configurações do PostgreSQL para busca textual
SET default_text_search_config = 'portuguese';
