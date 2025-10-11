#!/bin/bash
# ================================================================
# ENEM RAG System - Database Backup Script
# ================================================================
# Creates backups using pg_dump for reliable backup and restore
# ================================================================

# Configuration
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="teachershub_enem"
DB_USER="enem_rag_service"
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Ì¥Ñ Starting ENEM RAG Database Backup..."
echo "Ì≥Ö Timestamp: $TIMESTAMP"
echo "Ì∑ÑÔ∏è  Database: $DB_NAME"
echo "Ì≥Å Backup Directory: $BACKUP_DIR"
echo ""

# Function to create different types of backups
create_backup() {
    local backup_type=$1
    local backup_file=$2
    local pg_dump_args=$3
    
    echo "Ì¥Ñ Creating $backup_type backup..."
    
    # Use Docker to run pg_dump
    docker exec teachershub-enem-postgres pg_dump \
        -h localhost -p 5432 -U $DB_USER -d $DB_NAME \
        $pg_dump_args > "$backup_file"
    
    if [ $? -eq 0 ]; then
        local file_size=$(du -h "$backup_file" | cut -f1)
        echo "‚úÖ $backup_type backup completed: $backup_file ($file_size)"
    else
        echo "‚ùå $backup_type backup failed!"
        return 1
    fi
}

# 1. Complete backup (schema + data)
echo "1Ô∏è‚É£  Complete Database Backup (Schema + Data)"
create_backup "Complete" "$BACKUP_DIR/enem_rag_complete_$TIMESTAMP.sql" "--verbose --no-owner --no-privileges"

# 2. Data-only backup
echo ""
echo "2Ô∏è‚É£  Data-Only Backup"
create_backup "Data-only" "$BACKUP_DIR/enem_rag_data_only_$TIMESTAMP.sql" "--data-only --verbose --no-owner --no-privileges"

# 3. Schema-only backup
echo ""
echo "3Ô∏è‚É£  Schema-Only Backup"
create_backup "Schema-only" "$BACKUP_DIR/enem_rag_schema_only_$TIMESTAMP.sql" "--schema-only --verbose --no-owner --no-privileges"

# 4. Binary backup (faster restore)
echo ""
echo "4Ô∏è‚É£  Binary Backup (Custom Format)"
create_backup "Binary" "$BACKUP_DIR/enem_rag_binary_$TIMESTAMP.backup" "--format=custom --verbose --no-owner --no-privileges"

# Show backup summary
echo ""
echo "Ì≥ä Backup Summary:"
echo "=================="
ls -lh "$BACKUP_DIR"/*$TIMESTAMP* | while read line; do
    echo "  $line"
done

echo ""
echo "‚úÖ All backups completed successfully!"
echo ""
echo "Ì¥ß To restore backups:"
echo "   Complete SQL: psql -U $DB_USER -d $DB_NAME -f $BACKUP_DIR/enem_rag_complete_$TIMESTAMP.sql"
echo "   Data only:    psql -U $DB_USER -d $DB_NAME -f $BACKUP_DIR/enem_rag_data_only_$TIMESTAMP.sql"
echo "   Binary:       pg_restore -U $DB_USER -d $DB_NAME $BACKUP_DIR/enem_rag_binary_$TIMESTAMP.backup"
echo ""
echo "Ì≤° Binary backups are faster to restore and preserve all PostgreSQL-specific features"
