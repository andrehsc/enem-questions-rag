-- ========================================
-- INITIAL DATABASE SETUP
-- Setup inicial do banco PostgreSQL para ENEM RAG
-- ========================================

-- Configurar encoding e locale
ALTER DATABASE enem_questions_rag SET client_encoding TO 'UTF8';
ALTER DATABASE enem_questions_rag SET lc_messages TO 'en_US.UTF-8';
ALTER DATABASE enem_questions_rag SET lc_monetary TO 'en_US.UTF-8';
ALTER DATABASE enem_questions_rag SET lc_numeric TO 'en_US.UTF-8';
ALTER DATABASE enem_questions_rag SET lc_time TO 'en_US.UTF-8';

-- Criar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Configurar busca full-text em português
CREATE TEXT SEARCH CONFIGURATION portuguese_config (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portuguese_config
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;

-- Mensagem de sucesso
DO $$ 
BEGIN 
    RAISE NOTICE '=== Database Initialization Complete ===';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_trgm, unaccent';
    RAISE NOTICE 'Text search: portuguese_config created';
    RAISE NOTICE 'Ready for schema creation!';
END $$;