#!/bin/bash
# ================================================================
# ENEM RAG System - Database Restore Script
# ================================================================
# Restores database from backup files
# ================================================================

# Configuration
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="teachershub_enem"
DB_USER="enem_rag_service"
BACKUP_DIR="backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_usage() {
    echo "Ì¥ß ENEM RAG Database Restore Tool"
    echo "================================="
    echo ""
    echo "Usage: $0 [OPTIONS] <backup_file>"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE     Backup type: sql, binary, or auto (default: auto)"
    echo "  -l, --list          List available backup files"
    echo "  -f, --force         Force restore without confirmation"
    echo "  -s, --schema-only   Restore schema only (for SQL backups)"
    echo "  -d, --data-only     Restore data only (for SQL backups)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list                                    # List backups"
    echo "  $0 backups/enem_rag_complete_20241011.sql   # Restore complete backup"
    echo "  $0 --type binary backup.backup              # Restore binary backup"
    echo "  $0 --data-only data_backup.sql              # Restore data only"
    echo ""
}

list_backups() {
    echo "Ì≥Å Available Backup Files:"
    echo "=========================="
    
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "‚ùå Backup directory not found: $BACKUP_DIR"
        return 1
    fi
    
    local found=false
    for file in "$BACKUP_DIR"/*; do
        if [ -f "$file" ]; then
            found=true
            local size=$(du -h "$file" | cut -f1)
            local date=$(stat -c %y "$file" 2>/dev/null || stat -f %Sm "$file" 2>/dev/null)
            echo "  Ì≥Ñ $(basename "$file") - $size - $date"
        fi
    done
    
    if [ "$found" = false ]; then
        echo "  No backup files found in $BACKUP_DIR"
    fi
}

confirm_restore() {
    local backup_file=$1
    
    echo ""
    echo -e "${YELLOW}‚ö†Ô∏è  WARNING: This will replace ALL current database data!${NC}"
    echo "Ì≥Å Backup file: $backup_file"
    echo "Ì∑ÑÔ∏è  Target database: $DB_NAME"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "‚ùå Restore cancelled."
        exit 1
    fi
}

get_backup_type() {
    local file=$1
    
    if [[ "$file" == *.backup || "$file" == *.dump ]]; then
        echo "binary"
    elif [[ "$file" == *.sql ]]; then
        echo "sql"
    else
        echo "unknown"
    fi
}

restore_sql_backup() {
    local backup_file=$1
    local restore_options=$2
    
    echo "Ì¥Ñ Restoring SQL backup: $backup_file"
    
    # Use Docker to run psql
    docker exec -i teachershub-enem-postgres psql \
        -h localhost -p 5432 -U $DB_USER -d $DB_NAME \
        $restore_options < "$backup_file"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}‚úÖ SQL backup restored successfully!${NC}"
        return 0
    else
        echo -e "${RED}‚ùå SQL backup restore failed!${NC}"
        return 1
    fi
}

restore_binary_backup() {
    local backup_file=$1
    local restore_options=$2
    
    echo "Ì¥Ñ Restoring binary backup: $backup_file"
    
    # Copy backup file into container temporarily
    docker cp "$backup_file" teachershub-enem-postgres:/tmp/restore.backup
    
    # Use Docker to run pg_restore
    docker exec teachershub-enem-postgres pg_restore \
        -h localhost -p 5432 -U $DB_USER -d $DB_NAME \
        --clean --if-exists $restore_options \
        /tmp/restore.backup
    
    local result=$?
    
    # Clean up temporary file
    docker exec teachershub-enem-postgres rm -f /tmp/restore.backup
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}‚úÖ Binary backup restored successfully!${NC}"
        return 0
    else
        echo -e "${RED}‚ùå Binary backup restore failed!${NC}"
        return 1
    fi
}

verify_restore() {
    echo ""
    echo "Ì¥ç Verifying restore..."
    
    # Use Docker to run verification query
    docker exec teachershub-enem-postgres psql \
        -h localhost -p 5432 -U $DB_USER -d $DB_NAME \
        -c "
        DO \$\$
        DECLARE
            exam_count INTEGER;
            question_count INTEGER;
            alternative_count INTEGER;
            answer_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO exam_count FROM exam_metadata;
            SELECT COUNT(*) INTO question_count FROM questions;
            SELECT COUNT(*) INTO alternative_count FROM question_alternatives;
            SELECT COUNT(*) INTO answer_count FROM answer_keys;
            
            RAISE NOTICE '=== DATABASE VERIFICATION ===';
            RAISE NOTICE 'Exam metadata: % records', exam_count;
            RAISE NOTICE 'Questions: % records', question_count;
            RAISE NOTICE 'Question alternatives: % records', alternative_count;
            RAISE NOTICE 'Answer keys: % records', answer_count;
            RAISE NOTICE '============================';
        END \$\$;
        "
}

# Parse command line arguments
BACKUP_TYPE="auto"
FORCE=false
SCHEMA_ONLY=false
DATA_ONLY=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -s|--schema-only)
            SCHEMA_ONLY=true
            shift
            ;;
        -d|--data-only)
            DATA_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}‚ùå Error: Backup file not specified${NC}"
    echo ""
    show_usage
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}‚ùå Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Auto-detect backup type if not specified
if [ "$BACKUP_TYPE" = "auto" ]; then
    BACKUP_TYPE=$(get_backup_type "$BACKUP_FILE")
fi

# Validate backup type
if [ "$BACKUP_TYPE" != "sql" ] && [ "$BACKUP_TYPE" != "binary" ]; then
    echo -e "${RED}‚ùå Error: Unknown backup type. Use 'sql' or 'binary'${NC}"
    exit 1
fi

# Confirm restore unless forced
if [ "$FORCE" != true ]; then
    confirm_restore "$BACKUP_FILE"
fi

# Prepare restore options
RESTORE_OPTIONS=""
if [ "$SCHEMA_ONLY" = true ]; then
    RESTORE_OPTIONS="--schema-only"
elif [ "$DATA_ONLY" = true ]; then
    RESTORE_OPTIONS="--data-only"
fi

# Perform restore
echo ""
echo -e "${BLUE}Ì¥Ñ Starting database restore...${NC}"
echo "Ì≥Å File: $BACKUP_FILE"
echo "Ì≥ä Type: $BACKUP_TYPE"
echo "Ì∑ÑÔ∏è  Database: $DB_NAME"
echo ""

if [ "$BACKUP_TYPE" = "sql" ]; then
    restore_sql_backup "$BACKUP_FILE" "$RESTORE_OPTIONS"
elif [ "$BACKUP_TYPE" = "binary" ]; then
    restore_binary_backup "$BACKUP_FILE" "$RESTORE_OPTIONS"
fi

# Verify if restore was successful
if [ $? -eq 0 ]; then
    verify_restore
    echo ""
    echo -e "${GREEN}Ìæâ Database restore completed successfully!${NC}"
else
    echo -e "${RED}‚ùå Database restore failed!${NC}"
    exit 1
fi
