-- ================================================================
-- ENEM RAG SYSTEM - COMPLETE DATABASE BACKUP
-- ================================================================
-- This script contains a complete backup of the current database state
-- Generated automatically from the live database
-- 
-- Usage:
--   psql -U postgres -d teachershub_enem -f scripts/backup_current_database.sql
-- ================================================================

-- Disable triggers during restore for performance
SET session_replication_role = replica;

-- ================================================================
-- DATA BACKUP - EXAM_METADATA
-- ================================================================

TRUNCATE TABLE exam_metadata CASCADE;

