#!/usr/bin/env python3
"""
Test database connection and schema validation for ENEM Questions RAG
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import psycopg2
from psycopg2 import sql
import dotenv

# Load environment variables
dotenv.load_dotenv()

def test_connection():
    """Test basic database connection."""
    print("🔍 Testing database connection...")
    
    try:
        # Connection parameters
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5433'),
            'database': os.getenv('POSTGRES_DB', 'teachershub_enem'),
            'user': os.getenv('POSTGRES_USER', 'enem_rag_service'),
            'password': os.getenv('POSTGRES_PASSWORD', 'enem123')
        }
        
        print(f"📡 Connecting to: {conn_params['user']}@{conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
        
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Test basic query
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"✅ Connected to PostgreSQL: {version[:50]}...")
                
                # Test current database
                cur.execute("SELECT current_database(), current_user, now();")
                db_info = cur.fetchone()
                print(f"📊 Database: {db_info[0]}, User: {db_info[1]}, Time: {db_info[2]}")
                
                return True
                
    except psycopg2.Error as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_schema():
    """Test if our schema exists and is properly created."""
    print("\n🏗️  Testing database schema...")
    
    try:
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5433'),
            'database': os.getenv('POSTGRES_DB', 'teachershub_enem'),
            'user': os.getenv('POSTGRES_USER', 'enem_rag_service'),
            'password': os.getenv('POSTGRES_PASSWORD', 'enem123')
        }
        
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Check tables
                expected_tables = ['exam_metadata', 'questions', 'question_alternatives', 'answer_keys']
                
                for table in expected_tables:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        );
                    """, (table,))
                    
                    exists = cur.fetchone()[0]
                    if exists:
                        print(f"✅ Table '{table}' exists")
                        
                        # Count records
                        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                            sql.Identifier(table)
                        ))
                        count = cur.fetchone()[0]
                        print(f"   📊 Records: {count}")
                    else:
                        print(f"❌ Table '{table}' missing")
                        return False
                
                # Check views
                expected_views = ['questions_with_answers', 'exam_summary']
                for view in expected_views:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.views 
                            WHERE table_name = %s
                        );
                    """, (view,))
                    
                    exists = cur.fetchone()[0]
                    if exists:
                        print(f"✅ View '{view}' exists")
                    else:
                        print(f"❌ View '{view}' missing")
                
                # Check functions
                cur.execute("""
                    SELECT routine_name 
                    FROM information_schema.routines 
                    WHERE routine_type = 'FUNCTION' 
                    AND routine_schema = 'public'
                    AND routine_name IN ('get_parsing_stats', 'find_similar_questions');
                """)
                
                functions = [row[0] for row in cur.fetchall()]
                for func in ['get_parsing_stats', 'find_similar_questions']:
                    if func in functions:
                        print(f"✅ Function '{func}' exists")
                    else:
                        print(f"❌ Function '{func}' missing")
                
                # Test extensions
                cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent');")
                extensions = [row[0] for row in cur.fetchall()]
                
                for ext in ['uuid-ossp', 'pg_trgm', 'unaccent']:
                    if ext in extensions:
                        print(f"✅ Extension '{ext}' installed")
                    else:
                        print(f"⚠️  Extension '{ext}' missing")
                
                return True
                
    except psycopg2.Error as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_sample_operations():
    """Test sample database operations."""
    print("\n🧪 Testing sample operations...")
    
    try:
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'enem_questions_rag'),
            'user': os.getenv('POSTGRES_USER', 'enem_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'enem_password_2024')
        }
        
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Test UUID generation
                cur.execute("SELECT gen_random_uuid();")
                uuid_val = cur.fetchone()[0]
                print(f"✅ UUID generation: {uuid_val}")
                
                # Test parsing stats function
                cur.execute("SELECT * FROM get_parsing_stats();")
                stats = cur.fetchone()
                if stats:
                    print(f"✅ Parsing stats: {stats[0]} exams, {stats[1]} questions")
                else:
                    print("⚠️  No parsing stats available (empty database)")
                
                # Test full-text search setup
                cur.execute("SELECT to_tsvector('portuguese', 'questão de matemática');")
                result = cur.fetchone()[0]
                print(f"✅ Portuguese text search: {result}")
                
                return True
                
    except psycopg2.Error as e:
        print(f"❌ Sample operations failed: {e}")
        return False

def wait_for_database(max_attempts=30, delay=2):
    """Wait for database to be ready."""
    print(f"⏳ Waiting for database to be ready (max {max_attempts * delay}s)...")
    
    for attempt in range(max_attempts):
        try:
            conn_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'enem_questions_rag'),
                'user': os.getenv('POSTGRES_USER', 'enem_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'enem_password_2024')
            }
            
            with psycopg2.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    print("✅ Database is ready!")
                    return True
                    
        except psycopg2.Error:
            if attempt < max_attempts - 1:
                print(f"⏳ Attempt {attempt + 1}/{max_attempts} - waiting {delay}s...")
                time.sleep(delay)
            else:
                print("❌ Database failed to become ready")
                return False

def main():
    """Main test function."""
    print("=" * 50)
    print("🧪 ENEM Questions RAG - Database Test")
    print("=" * 50)
    
    # Wait for database
    if not wait_for_database():
        sys.exit(1)
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_connection():
        tests_passed += 1
    
    if test_schema():
        tests_passed += 1
    
    if test_sample_operations():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Database is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())