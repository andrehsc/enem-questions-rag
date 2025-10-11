# ENEM RAG System - Backup & Restore Guide

## Overview

This document describes the comprehensive backup and restore system for the ENEM RAG database. The system provides multiple backup strategies and restore options to ensure data safety and recovery capabilities.

## Ìª†Ô∏è Available Tools

### 1. Python SQL Backup Generator
**File:** `scripts/generate_database_backup.py`

Generates a complete SQL backup using pure Python, creating INSERT statements for all data.

**Features:**
- Batch processing for large datasets
- Binary data handling (BLOB fields)
- Statistics reporting
- Escape handling for special characters
- Progress monitoring

**Usage:**
```bash
python scripts/generate_database_backup.py
```

**Output:** `backups/enem_rag_backup_YYYYMMDD_HHMMSS.sql`

### 2. Shell pg_dump Backup
**File:** `scripts/backup_database.sh`

Uses PostgreSQL's native `pg_dump` utility through Docker for multiple backup formats.

**Features:**
- Multiple backup types (complete, schema-only, data-only)
- Multiple formats (SQL, binary custom format)
- Docker integration
- Comprehensive CLI interface

**Usage:**
```bash
# Show help
./scripts/backup_database.sh --help

# Create complete backup (SQL + binary)
./scripts/backup_database.sh --type complete

# Create schema-only backup
./scripts/backup_database.sh --type schema

# Create data-only backup
./scripts/backup_database.sh --type data
```

### 3. Database Restore Tool
**File:** `scripts/restore_database.sh`

Restores database from backup files with automatic type detection.

**Features:**
- Auto-detection of backup type
- Support for SQL and binary backups
- Confirmation prompts for safety
- Verification after restore
- Flexible restore options

**Usage:**
```bash
# Show help
./scripts/restore_database.sh --help

# List available backups
./scripts/restore_database.sh --list

# Restore with confirmation
./scripts/restore_database.sh backups/your_backup.sql

# Force restore without confirmation
./scripts/restore_database.sh --force backups/your_backup.backup

# Restore schema only
./scripts/restore_database.sh --schema-only backups/your_backup.sql
```

### 4. Test Suite
**File:** `scripts/test_backup_restore.py`

Comprehensive test suite for all backup and restore functionality.

**Usage:**
```bash
python scripts/test_backup_restore.py
```

## Ì≥ä Current Database State

Based on the latest ingestion, the database contains:
- **4,856 answer keys** from gabarito files
- **2,532 questions** extracted from PDF files
- **Multiple exam metadata** records
- **Question alternatives** for each question
- **Image data** (when extracted)

## ÔøΩÔøΩ Backup Strategies

### Strategy 1: Python SQL Backup (Recommended for Small-Medium DBs)
- **Pros:** Platform independent, readable SQL format, detailed control
- **Cons:** Slower for very large datasets, larger file sizes
- **Best for:** Development, testing, cross-platform compatibility

### Strategy 2: pg_dump Binary Backup (Recommended for Large DBs)
- **Pros:** Fast, compact, efficient for large datasets
- **Cons:** PostgreSQL specific, binary format
- **Best for:** Production, large datasets, regular backups

## Ì≥Å Backup Directory Structure

```
backups/
‚îú‚îÄ‚îÄ enem_rag_backup_20241011_143022.sql          # Python SQL backup
‚îú‚îÄ‚îÄ enem_rag_complete_20241011_143155.sql        # pg_dump SQL backup
‚îú‚îÄ‚îÄ enem_rag_complete_20241011_143155.backup     # pg_dump binary backup
‚îú‚îÄ‚îÄ enem_rag_schema_20241011_143200.sql          # Schema-only backup
‚îî‚îÄ‚îÄ enem_rag_data_20241011_143205.sql            # Data-only backup
```

## Ì∫Ä Quick Start

### Creating Your First Backup
```bash
# Method 1: Python SQL backup (cross-platform)
python scripts/generate_database_backup.py

# Method 2: Native pg_dump backup (faster)
./scripts/backup_database.sh --type complete
```

### Listing Available Backups
```bash
./scripts/restore_database.sh --list
```

### Restoring from Backup
```bash
# Interactive restore (recommended)
./scripts/restore_database.sh backups/your_backup_file.sql

# Forced restore (for automation)
./scripts/restore_database.sh --force backups/your_backup_file.sql
```

## ‚ö†Ô∏è Important Notes

### Prerequisites
1. **Docker container running:** The PostgreSQL container must be running
   ```bash
   docker-compose up -d
   ```

2. **Backup directory:** The `backups/` directory will be created automatically

3. **Permissions:** Ensure shell scripts are executable
   ```bash
   chmod +x scripts/*.sh
   ```

### Safety Considerations

1. **Restore Warning:** Restore operations will **REPLACE ALL DATA** in the target database
2. **Confirmation Required:** Restore script asks for confirmation unless `--force` is used
3. **Verification:** Restore script automatically verifies the restore by showing record counts
4. **Backup Before Changes:** Always create a backup before making significant changes

### Performance Considerations

1. **Python Backup:** Takes longer but provides detailed progress and statistics
2. **pg_dump Backup:** Faster and more efficient for large datasets
3. **Binary Format:** Most efficient for storage and restore speed
4. **Batch Processing:** Python backup uses batching to handle large datasets efficiently

## Ì∑™ Testing

Run the comprehensive test suite to verify all backup/restore functionality:

```bash
python scripts/test_backup_restore.py
```

The test suite will:
- Check Docker container status
- Test Python backup generation
- Test shell backup creation
- Test restore script functionality
- Verify database statistics
- Provide usage instructions

## Ì∂ò Troubleshooting

### Common Issues

1. **Container Not Running**
   ```bash
   docker-compose up -d
   ```

2. **Permission Denied**
   ```bash
   chmod +x scripts/*.sh
   ```

3. **Backup Directory Missing**
   - Directory is created automatically
   - Check write permissions in project root

4. **Database Connection Issues**
   - Verify container is running
   - Check database credentials in scripts
   - Ensure Docker network connectivity

### Verification Commands

```bash
# Check container status
docker ps | grep postgres

# Check database connectivity
docker exec teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem -c "SELECT version();"

# Check backup directory
ls -la backups/
```

## Ì≥à Best Practices

1. **Regular Backups:** Create backups before major changes
2. **Multiple Formats:** Use both SQL and binary backups for different scenarios
3. **Version Control:** Don't commit backup files to Git (large binary data)
4. **Testing:** Regularly test restore procedures
5. **Documentation:** Keep backup logs and restore procedures documented
6. **Monitoring:** Monitor backup file sizes and generation times
7. **Storage:** Store critical backups in multiple locations

## Ì¥Æ Future Enhancements

- Automated scheduling of backups
- Compression for large backup files
- Cloud storage integration (S3, Google Cloud)
- Incremental backup support
- Backup integrity verification
- Email notifications for backup status
- Web interface for backup management

---

**Last Updated:** October 11, 2024  
**System Version:** ENEM RAG v1.0 with Complete Backup/Restore System
