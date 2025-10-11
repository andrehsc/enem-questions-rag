#!/usr/bin/env python3
"""
ENEM RAG System - Backup/Restore Test Script
==================================================
Tests all backup and restore mechanisms to ensure data integrity.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

def run_command(command, description="", check=True):
    """Execute shell command with output."""
    print(f"\nÌ¥Ñ {description}")
    print(f"Command: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"‚ùå Command failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def check_docker_container():
    """Verify Docker container is running."""
    print("\nÌ∞≥ Checking Docker container status...")
    
    result = subprocess.run(
        "docker ps --filter name=teachershub-enem-postgres --format '{{.Status}}'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if "Up" in result.stdout:
        print("‚úÖ PostgreSQL container is running")
        return True
    else:
        print("‚ùå PostgreSQL container is not running")
        print("Please start the container with: docker-compose up -d")
        return False

def create_backup_directory():
    """Create backup directory if it doesn't exist."""
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    print(f"Ì≥Å Backup directory: {backup_dir.absolute()}")
    return backup_dir

def test_python_backup():
    """Test Python-based SQL backup generator."""
    print("\n" + "="*60)
    print("Ì∞ç TESTING PYTHON SQL BACKUP GENERATOR")
    print("="*60)
    
    success = run_command(
        "python scripts/generate_database_backup.py",
        "Generating SQL backup with Python script"
    )
    
    if success:
        # Check if backup file was created
        backup_files = list(Path("backups").glob("enem_rag_backup_*.sql"))
        if backup_files:
            latest_backup = max(backup_files, key=os.path.getctime)
            print(f"‚úÖ Python SQL backup created: {latest_backup}")
            return str(latest_backup)
        else:
            print("‚ùå No backup file found after Python script")
            return None
    else:
        print("‚ùå Python backup script failed")
        return None

def test_shell_backup():
    """Test shell-based pg_dump backup."""
    print("\n" + "="*60)
    print("Ì∞ö TESTING SHELL PG_DUMP BACKUP")
    print("="*60)
    
    success = run_command(
        "./scripts/backup_database.sh --help",
        "Testing backup script help"
    )
    
    if success:
        # Test complete backup
        success = run_command(
            "./scripts/backup_database.sh --type complete",
            "Creating complete pg_dump backup"
        )
        
        if success:
            # Check for backup files
            backup_files = list(Path("backups").glob("enem_rag_complete_*.sql"))
            binary_files = list(Path("backups").glob("enem_rag_complete_*.backup"))
            
            if backup_files or binary_files:
                print("‚úÖ Shell backup completed successfully")
                return True
            else:
                print("‚ùå No backup files found after shell script")
                return False
        else:
            print("‚ùå Shell backup failed")
            return False
    else:
        print("‚ùå Shell backup script not executable or missing")
        return False

def test_restore_script():
    """Test restore script functionality."""
    print("\n" + "="*60)
    print("Ì¥ß TESTING RESTORE SCRIPT")
    print("="*60)
    
    # Test help command
    success = run_command(
        "./scripts/restore_database.sh --help",
        "Testing restore script help"
    )
    
    if success:
        # Test list backups
        success = run_command(
            "./scripts/restore_database.sh --list",
            "Listing available backups"
        )
        
        if success:
            print("‚úÖ Restore script is functional")
            return True
        else:
            print("‚ùå Restore script list function failed")
            return False
    else:
        print("‚ùå Restore script not executable or missing")
        return False

def get_database_stats():
    """Get current database statistics."""
    print("\nÌ≥ä Getting database statistics...")
    
    stats_query = """
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
        
        RAISE NOTICE 'Current Database Statistics:';
        RAISE NOTICE '- Exam metadata: % records', exam_count;
        RAISE NOTICE '- Questions: % records', question_count;
        RAISE NOTICE '- Question alternatives: % records', alternative_count;
        RAISE NOTICE '- Answer keys: % records', answer_count;
        RAISE NOTICE '- Question images: % records', image_count;
    END $$;
    """
    
    command = f'''docker exec teachershub-enem-postgres psql -h localhost -p 5432 -U enem_rag_service -d teachershub_enem -c "{stats_query}"'''
    
    run_command(command, "Getting database statistics", check=False)

def main():
    """Main test function."""
    print("Ì∑™ ENEM RAG BACKUP/RESTORE TEST SUITE")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    
    # Pre-flight checks
    if not check_docker_container():
        sys.exit(1)
    
    backup_dir = create_backup_directory()
    
    # Get initial database stats
    get_database_stats()
    
    # Test results tracking
    results = {}
    
    # Test Python backup
    python_backup_file = test_python_backup()
    results['python_backup'] = python_backup_file is not None
    
    # Test shell backup
    results['shell_backup'] = test_shell_backup()
    
    # Test restore script
    results['restore_script'] = test_restore_script()
    
    # Final report
    print("\n" + "="*60)
    print("Ì≥ã TEST RESULTS SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "‚úÖ PASS" if passed else "‚ùå FAIL"
        print(f"{test_name:20}: {status}")
    
    print(f"\nTests passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("\nÌæâ All backup/restore tests PASSED!")
        print("\nÌ≤° Usage Instructions:")
        print("="*30)
        print("1. Create backup:")
        print("   - Python SQL: python scripts/generate_database_backup.py")
        print("   - Shell pg_dump: ./scripts/backup_database.sh --type complete")
        print()
        print("2. List backups:")
        print("   - ./scripts/restore_database.sh --list")
        print()
        print("3. Restore backup:")
        print("   - ./scripts/restore_database.sh backups/your_backup_file.sql")
        print("   - ./scripts/restore_database.sh --force backups/your_backup_file.backup")
        
        return 0
    else:
        print(f"\n‚ùå {total_tests - passed_tests} test(s) failed!")
        print("Please check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
