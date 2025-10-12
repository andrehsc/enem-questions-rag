#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM RAG System - Database Backup Generator
==========================================
Generates a complete SQL backup of the current database state.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'teachershub_enem',
    'user': 'enem_rag_service',
    'password': 'enem_rag_password'
}

def create_backup_directory():
    """Create backup directory if it doesn't exist."""
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    return backup_dir

def escape_sql_string(value):
    """Escape string values for SQL."""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    elif isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bytes):
        # Convert bytes to hex format for BYTEA
        return f"'\\x{value.hex()}'"
    else:
        return f"'{str(value)}'"

def get_table_info(cursor):
    """Get information about all tables.""" 
    cursor.execute("""
        SELECT DISTINCT tablename 
        FROM pg_tables 
        WHERE schemaname IN ('public', 'enem_questions')
        ORDER BY tablename;
    """)
    return [row['tablename'] for row in cursor.fetchall()]

def get_table_columns(cursor, table_name):
    """Get column information for a table."""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema IN ('public', 'enem_questions')
        ORDER BY ordinal_position;
    """, (table_name,))
    return cursor.fetchall()

def backup_table_data(cursor, table_name, output_file, batch_size=1000):
    """Backup data from a single table."""
    print(f"Backing up table: {table_name}")
    
    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    result = cursor.fetchone()
    total_rows = result['count'] if isinstance(result, dict) else result[0]
    
    if total_rows == 0:
        print(f"  - No data in {table_name}")
        return 0
    
    print(f"  - Total rows: {total_rows}")
    
    # Get column names
    columns_info = get_table_columns(cursor, table_name)
    column_names = [col['column_name'] for col in columns_info]
    columns_str = ', '.join(column_names)
    
    # Write table header
    output_file.write(f"\n-- Backup data for table: {table_name}\n")
    output_file.write(f"-- Total rows: {total_rows}\n")
    
    # Process in batches
    offset = 0
    total_processed = 0
    
    while offset < total_rows:
        first_column = column_names[0]
        cursor.execute(f"""
            SELECT {columns_str} 
            FROM {table_name} 
            ORDER BY {first_column}
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        
        rows = cursor.fetchall()
        if not rows:
            break
        
        # Generate INSERT statements
        for row in rows:
            values = [escape_sql_string(value) for value in row]
            values_str = ', '.join(values)
            
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});\n"
            output_file.write(insert_sql)
        
        total_processed += len(rows)
        offset += batch_size
        
        # Progress update
        progress = (total_processed / total_rows) * 100
        print(f"  - Progress: {total_processed}/{total_rows} ({progress:.1f}%)")
    
    return total_processed

def get_database_statistics(cursor):
    """Get comprehensive database statistics."""
    stats = {}
    
    tables = get_table_info(cursor)
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        result = cursor.fetchone()
        count = result['count'] if isinstance(result, dict) else result[0]
        stats[table] = count
    
    return stats

def generate_backup():
    """Generate complete database backup."""
    print("ENEM RAG Database Backup Generator")
    print("=" * 40)
    
    # Create backup directory
    backup_dir = create_backup_directory()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = backup_dir / f"enem_rag_backup_{timestamp}.sql"
    
    print(f"Backup file: {backup_filename}")
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get database statistics
        print("Collecting database statistics...")
        stats = get_database_statistics(cursor)
        
        # Create backup file
        print("Creating backup file...")
        with open(backup_filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write("-- ENEM RAG Database Backup\n")
            f.write(f"-- Generated: {datetime.now()}\n")
            f.write(f"-- Database: {DB_CONFIG['database']}\n")
            f.write("-- \n")
            f.write("-- This backup contains all data from the ENEM RAG system\n")
            f.write("-- Use with restore_database.sh for restoration\n")
            f.write("--\n\n")
            
            # Write statistics
            f.write("-- DATABASE STATISTICS\n")
            f.write("-- ====================\n")
            total_records = 0
            for table, count in stats.items():
                f.write(f"-- {table}: {count} records\n")
                total_records += count
            f.write(f"-- TOTAL RECORDS: {total_records}\n")
            f.write("--\n\n")
            
            # Disable constraints during restore
            f.write("-- Disable foreign key constraints for faster restore\n")
            f.write("SET session_replication_role = replica;\n\n")
            
            # Backup each table
            tables = get_table_info(cursor)
            total_backed_up = 0
            
            for table in tables:
                if stats[table] > 0:
                    rows_backed_up = backup_table_data(cursor, table, f)
                    total_backed_up += rows_backed_up
            
            # Re-enable constraints
            f.write("\n-- Re-enable foreign key constraints\n")
            f.write("SET session_replication_role = DEFAULT;\n")
            
            # Update sequences (for auto-increment fields)
            f.write("\n-- Update sequences\n")
            try:
                cursor.execute("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema IN ('public', 'enem_questions')
                """)
                
                sequences = cursor.fetchall()
                for seq in sequences:
                    seq_name = seq['sequence_name'] if isinstance(seq, dict) else seq[0]
                    table_name = seq_name.replace('_id_seq', '')
                    f.write(f"SELECT setval('{seq_name}', (SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}), false);\n")
            except Exception as seq_error:
                print(f"Warning: Could not update sequences: {seq_error}")
                f.write("-- Sequence update skipped due to error\n")
            
            f.write("\n-- Backup completed successfully\n")
        
        print("\nBackup Summary:")
        print("=" * 20)
        print(f"Tables backed up: {len([t for t in tables if stats[t] > 0])}")
        print(f"Total records: {total_backed_up}")
        print(f"Backup file: {backup_filename}")
        print(f"File size: {backup_filename.stat().st_size / 1024 / 1024:.2f} MB")
        
        print("\nDatabase Statistics:")
        print("=" * 20)
        for table, count in sorted(stats.items()):
            if count > 0:
                print(f"{table}: {count} records")
        
        print(f"\nBackup completed successfully!")
        print(f"Use this command to restore:")
        print(f"./scripts/restore_database.sh {backup_filename}")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'conn' in locals():
            conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(generate_backup())
