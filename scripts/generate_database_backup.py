#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM RAG System - Database Backup Generator
============================================
Generates a complete SQL backup script of the current database state.
This can be used to restore the database to its current state.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path
import argparse
import sys

class DatabaseBackupGenerator:
    """Generates SQL backup scripts from live database"""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def generate_backup_script(self, output_file: Path, include_data: bool = True):
        """Generate complete backup SQL script"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(self._get_header())
            
            # Write schema recreation (optional - assumes schema exists)
            f.write("\n-- ================================================================\n")
            f.write("-- SCHEMA VERIFICATION\n")
            f.write("-- ================================================================\n\n")
            f.write("-- Verify tables exist, create if missing\n")
            f.write("-- (Assumes schema was created with create_database_complete.sql)\n\n")
            
            if include_data:
                # Generate data for each table in dependency order
                tables = ['exam_metadata', 'questions', 'question_alternatives', 'answer_keys', 'question_images']
                
                for table in tables:
                    f.write(f"\n-- ================================================================\n")
                    f.write(f"-- DATA BACKUP - {table.upper()}\n")
                    f.write(f"-- ================================================================\n\n")
                    
                    # Get table data
                    data_sql = self._generate_table_data(table)
                    f.write(data_sql)
                    f.write("\n")
            
            # Write footer
            f.write(self._get_footer())
            
        print(f"âœ… Backup script generated: {output_file}")
        
    def _get_header(self) -> str:
        """Generate SQL header"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""-- ================================================================
-- ENEM RAG SYSTEM - COMPLETE DATABASE BACKUP
-- ================================================================
-- Generated: {timestamp}
-- Contains complete backup of database state for restoration
-- 
-- Usage:
--   psql -U enem_rag_service -d teachershub_enem -f scripts/backup_current_database.sql
-- 
-- Prerequisites:
--   - Database and schema must exist
--   - Run create_database_complete.sql first if starting fresh
-- ================================================================

-- Disable triggers and constraints during restore for performance
SET session_replication_role = replica;
SET check_function_bodies = false;
SET client_min_messages = warning;

-- Start transaction
BEGIN;

"""
    
    def _get_footer(self) -> str:
        """Generate SQL footer"""
        return """
-- Re-enable triggers and constraints
SET session_replication_role = DEFAULT;

-- Update sequences to correct values
SELECT setval('answer_keys_id_seq', COALESCE((SELECT MAX(id) FROM answer_keys), 1));

-- Commit transaction
COMMIT;

-- Final verification
DO $$
DECLARE
    exam_count INTEGER;
    question_count INTEGER;
    alternative_count INTEGER;
    answer_count INTEGER;
    image_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO exam_count FROM exam_metadata;
    SELECT COUNT(*) INTO question_count FROM questions;
    SELECT COUNT(*) INTO alternative_count FROM question_alternatives;
    SELECT COUNT(*) INTO answer_count FROM answer_keys;
    SELECT COUNT(*) INTO image_count FROM question_images;
    
    RAISE NOTICE '=== DATABASE RESTORE COMPLETED ===';
    RAISE NOTICE 'Exam metadata: % records', exam_count;
    RAISE NOTICE 'Questions: % records', question_count;
    RAISE NOTICE 'Question alternatives: % records', alternative_count;
    RAISE NOTICE 'Answer keys: % records', answer_count;
    RAISE NOTICE 'Question images: % records', image_count;
    RAISE NOTICE '=================================';
END $$;
"""
    
    def _generate_table_data(self, table_name: str) -> str:
        """Generate INSERT statements for a table"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get table structure
                    cur.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        ORDER BY ordinal_position
                    """, (table_name,))
                    
                    columns = cur.fetchall()
                    if not columns:
                        return f"-- No columns found for table {table_name}\n"
                    
                    column_names = [col['column_name'] for col in columns]
                    
                    # Get row count
                    cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    row_count = cur.fetchone()['count']
                    
                    if row_count == 0:
                        return f"-- No data found in table {table_name}\n"
                    
                    # Clear existing data
                    sql_output = f"-- Clear existing data\nTRUNCATE TABLE {table_name} {'CASCADE' if table_name == 'exam_metadata' else ''};\n\n"
                    sql_output += f"-- Insert {row_count} records\n"
                    
                    # Get all data
                    cur.execute(f"SELECT * FROM {table_name} ORDER BY id")
                    rows = cur.fetchall()
                    
                    if rows:
                        # Generate INSERT statements in batches
                        batch_size = 100
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i:i + batch_size]
                            
                            sql_output += f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES\n"
                            
                            value_strings = []
                            for row in batch:
                                values = []
                                for col_name in column_names:
                                    value = row[col_name]
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        # Escape single quotes
                                        escaped_value = value.replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    elif isinstance(value, bytes):
                                        # Handle binary data (images)
                                        values.append(f"'\\x{value.hex()}'")
                                    elif isinstance(value, bool):
                                        values.append('TRUE' if value else 'FALSE')
                                    else:
                                        values.append(str(value))
                                
                                value_strings.append(f"({', '.join(values)})")
                            
                            sql_output += ',\n'.join(value_strings)
                            sql_output += ";\n\n"
                    
                    return sql_output
                    
        except Exception as e:
            return f"-- Error generating data for table {table_name}: {e}\n"
    
    def generate_data_only_script(self, output_file: Path):
        """Generate script with only data (no schema)"""
        self.generate_backup_script(output_file, include_data=True)
    
    def get_database_stats(self) -> dict:
        """Get current database statistics"""
        stats = {}
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get counts for each table
                    tables = ['exam_metadata', 'questions', 'question_alternatives', 'answer_keys', 'question_images']
                    
                    for table in tables:
                        cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                        result = cur.fetchone()
                        stats[table] = result['count'] if result else 0
                    
                    # Get additional stats
                    cur.execute("SELECT COUNT(DISTINCT year) as years FROM exam_metadata")
                    result = cur.fetchone()
                    stats['distinct_years'] = result['years'] if result else 0
                    
                    cur.execute("SELECT COUNT(DISTINCT subject) as subjects FROM questions")
                    result = cur.fetchone()
                    stats['distinct_subjects'] = result['subjects'] if result else 0
                    
        except Exception as e:
            print(f"Error getting database stats: {e}")
            
        return stats

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate ENEM RAG Database Backup')
    parser.add_argument('--output', '-o', type=str, 
                       default='scripts/backup_current_database.sql',
                       help='Output file path')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show database statistics')
    parser.add_argument('--connection-url', type=str,
                       default='postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem',
                       help='Database connection URL')
    
    args = parser.parse_args()
    
    generator = DatabaseBackupGenerator(args.connection_url)
    
    if args.stats_only:
        print("í³Š Current Database Statistics:")
        print("=" * 40)
        stats = generator.get_database_stats()
        for table, count in stats.items():
            print(f"  {table}: {count:,}")
        return
    
    # Generate backup
    output_path = Path(args.output)
    print(f"í´„ Generating database backup...")
    print(f"í³ Output: {output_path}")
    
    # Show current stats
    stats = generator.get_database_stats()
    print(f"\ní³Š Database Statistics:")
    for table, count in stats.items():
        if isinstance(count, int) and count > 0:
            print(f"  {table}: {count:,} records")
    
    # Generate backup
    generator.generate_backup_script(output_path)
    
    print(f"\nâœ… Backup script generated successfully!")
    print(f"í³ File: {output_path}")
    print(f"í²¾ Size: {output_path.stat().st_size / 1024:.1f} KB")
    
    print(f"\ní´§ To restore this backup:")
    print(f"   psql -U enem_rag_service -d teachershub_enem -f {output_path}")

if __name__ == "__main__":
    main()
