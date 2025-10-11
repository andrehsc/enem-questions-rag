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
