-- TeachersHub-ENEM Hybrid Database Initialization
-- Using EXACT credentials from 00-dev-credentials.md

-- Create application users with EXACT passwords from reference
CREATE USER teachershub_app WITH PASSWORD 'teachershub123';
CREATE USER enem_rag_service WITH PASSWORD 'enem123';

-- Create schemas
CREATE SCHEMA IF NOT EXISTS teachers_hub;
CREATE SCHEMA IF NOT EXISTS enem_questions;
CREATE SCHEMA IF NOT EXISTS shared_resources;

-- Grant schema permissions
-- TeachersHub user permissions
GRANT USAGE ON SCHEMA teachers_hub TO teachershub_app;
GRANT CREATE ON SCHEMA teachers_hub TO teachershub_app;
GRANT USAGE ON SCHEMA shared_resources TO teachershub_app;
GRANT SELECT ON ALL TABLES IN SCHEMA shared_resources TO teachershub_app;

-- ENEM RAG service permissions  
GRANT USAGE ON SCHEMA enem_questions TO enem_rag_service;
GRANT CREATE ON SCHEMA enem_questions TO enem_rag_service;
GRANT USAGE ON SCHEMA shared_resources TO enem_rag_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA shared_resources TO enem_rag_service;

-- Cross-schema read permissions for integration
GRANT USAGE ON SCHEMA enem_questions TO teachershub_app;
GRANT SELECT ON ALL TABLES IN SCHEMA enem_questions TO teachershub_app;

-- Ensure future table permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA teachers_hub GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO teachershub_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA enem_questions GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO enem_rag_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared_resources GRANT SELECT ON TABLES TO teachershub_app, enem_rag_service;

-- Create extensions in shared_resources schema
-- CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA shared_resources;  -- Commented temporarily - requires pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA shared_resources;

-- Database initialization completed successfully
