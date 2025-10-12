#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Database Backup and Load Script for ENEM RAG System
============================================================
This script handles backup and restoration of the complete database including question_images.
"""

import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('database_operations.log'),
            logging.StreamHandler()
        ]
    )

def create_complete_backup():
    """Create a complete backup including all tables and data."""
    logger = logging.getLogger(__name__)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        # Backup schema and structure
        schema_file = f"scripts/backup_schema_{timestamp}.sql"
        cmd_schema = [
            'docker', 'exec', 'teachershub-enem-postgres',
            'pg_dump', '-U', 'postgres', '-d', 'teachershub_enem',
            '--schema-only', '--schema=enem_questions',
            '--clean', '--if-exists', '--no-owner', '--no-privileges'
        ]
        
        logger.info(f"Creating schema backup: {schema_file}")
        with open(schema_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd_schema, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"Schema backup failed: {result.stderr}")
            return False
        
        # Backup all data including images
        data_file = f"scripts/backup_data_{timestamp}.sql"
        cmd_data = [
            'docker', 'exec', 'teachershub-enem-postgres',
            'pg_dump', '-U', 'postgres', '-d', 'teachershub_enem',
            '--data-only', '--schema=enem_questions',
            '--no-owner', '--no-privileges'
        ]
        
        logger.info(f"Creating data backup: {data_file}")
        with open(data_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd_data, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"Data backup failed: {result.stderr}")
            return False
        
        # Check file sizes
        schema_size = os.path.getsize(schema_file)
        data_size = os.path.getsize(data_file)
        
        logger.info(f"✅ Backup completed successfully!")
        logger.info(f"   Schema: {schema_file} ({schema_size:,} bytes)")
        logger.info(f"   Data: {data_file} ({data_size:,} bytes)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}")
        return False

def restore_from_backup(schema_file, data_file):
    """Restore database from backup files."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting database restoration...")
        
        # Restore schema first
        if schema_file and os.path.exists(schema_file):
            logger.info(f"Restoring schema from: {schema_file}")
            cmd_schema = [
                'docker', 'exec', '-i', 'teachershub-enem-postgres',
                'psql', '-U', 'postgres', '-d', 'teachershub_enem'
            ]
            
            with open(schema_file, 'r', encoding='utf-8') as f:
                result = subprocess.run(cmd_schema, stdin=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"Schema restore failed: {result.stderr}")
                return False
        
        # Restore data
        if data_file and os.path.exists(data_file):
            logger.info(f"Restoring data from: {data_file}")
            cmd_data = [
                'docker', 'exec', '-i', 'teachershub-enem-postgres',
                'psql', '-U', 'postgres', '-d', 'teachershub_enem'
            ]
            
            with open(data_file, 'r', encoding='utf-8') as f:
                result = subprocess.run(cmd_data, stdin=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"Data restore failed: {result.stderr}")
                return False
        
        logger.info("✅ Database restoration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error restoring database: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Backup and restore complete ENEM RAG database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create backup
    python load_database_complete.py --backup
    
    # Restore from backup
    python load_database_complete.py --restore --schema backup_schema_20231011.sql --data backup_data_20231011.sql
        """
    )
    
    parser.add_argument('--backup', action='store_true', help='Create complete database backup')
    parser.add_argument('--restore', action='store_true', help='Restore database from backup')
    parser.add_argument('--schema', help='Schema backup file for restore')
    parser.add_argument('--data', help='Data backup file for restore')
    
    args = parser.parse_args()
    
    if not args.backup and not args.restore:
        parser.print_help()
        return
    
    setup_logging()
    
    if args.backup:
        success = create_complete_backup()
        sys.exit(0 if success else 1)
    
    if args.restore:
        if not args.schema and not args.data:
            print("❌ Error: --schema or --data file required for restore")
            sys.exit(1)
        
        success = restore_from_backup(args.schema, args.data)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

# Import our existing processor
from full_ingestion_report import FullIngestionProcessor

def setup_logging(verbose=False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Setup logging to file and console
    log_filename = log_dir / f"database_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='ENEM RAG Database Complete Loader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Complete load with default settings
    python scripts/load_database_complete.py
    
    # Clear database and load everything with 8 workers
    python scripts/load_database_complete.py --clear-db --workers 8
    
    # Load only questions in verbose mode
    python scripts/load_database_complete.py --questions-only --verbose
    
    # Load only gabaritos with larger batch size
    python scripts/load_database_complete.py --gabaritos-only --batch-size 16
        """
    )
    
    parser.add_argument('--clear-db', action='store_true',
                       help='Clear all data before loading')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Use parallel processing (default: True)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='Batch size for processing (default: 8)')
    parser.add_argument('--questions-only', action='store_true',
                       help='Load only questions (skip gabaritos)')
    parser.add_argument('--gabaritos-only', action='store_true',
                       help='Load only gabaritos (skip questions)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    return parser.parse_args()

def print_banner():
    """Print application banner"""
    banner = """
    ================================================================
    ENEM RAG SYSTEM - COMPLETE DATABASE LOADER
    ================================================================
    
    This script will load all ENEM data into the database:
    • Questions from PDF files (PV)
    • Answer keys from gabarito files (GB)  
    • Exam metadata and relationships
    
    ================================================================
    """
    print(banner)

def validate_environment():
    """Validate that required directories and files exist"""
    required_dirs = [
        Path("data/downloads"),
        Path("src"),
        Path("scripts")
    ]
    
    missing_dirs = [d for d in required_dirs if not d.exists()]
    if missing_dirs:
        print(f"❌ Missing required directories: {missing_dirs}")
        return False
    
    # Check if we have PDF files
    pdf_count = len(list(Path("data/downloads").rglob("*.pdf")))
    if pdf_count == 0:
        print("❌ No PDF files found in data/downloads")
        return False
    
    print(f"✅ Found {pdf_count} PDF files to process")
    return True

def main():
    """Main execution function"""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    print_banner()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Initialize processor
    logger.info("Initializing ENEM RAG processor...")
    processor = FullIngestionProcessor()
    
    # Configuration summary
    config = {
        'parallel': args.parallel,
        'workers': args.workers,
        'batch_size': args.batch_size,
        'clear_db': args.clear_db,
        'questions_only': args.questions_only,
        'gabaritos_only': args.gabaritos_only,
        'verbose': args.verbose
    }
    
    logger.info("Configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    
    # Validate mutually exclusive options
    if args.questions_only and args.gabaritos_only:
        logger.error("Cannot specify both --questions-only and --gabaritos-only")
        sys.exit(1)
    
    try:
        # Clear database if requested
        if args.clear_db:
            logger.info("���️  Clearing database...")
            processor.clear_database()
            logger.info("✅ Database cleared successfully")
        
        # Find files to process
        question_files = processor.find_question_files()
        answer_files = processor.find_answer_files()
        
        logger.info(f"Found {len(question_files)} question files")
        logger.info(f"Found {len(answer_files)} answer files")
        
        # Process based on options
        start_time = datetime.now()
        results = {}
        
        if not args.gabaritos_only:
            logger.info("��� Processing questions...")
            if args.parallel:
                question_results = processor.process_question_files_batched(
                    question_files,
                    batch_size=args.batch_size,
                    max_workers=args.workers
                )
            else:
                # Sequential processing fallback
                logger.warning("Sequential processing not implemented, using parallel")
                question_results = processor.process_question_files_batched(
                    question_files,
                    batch_size=args.batch_size,
                    max_workers=1
                )
            results['questions'] = question_results
        
        if not args.questions_only:
            logger.info("��� Processing gabaritos...")
            if args.parallel:
                answer_results = processor.process_answer_files_batched(
                    answer_files,
                    batch_size=args.batch_size,
                    max_workers=args.workers
                )
            else:
                # Sequential processing fallback
                logger.warning("Sequential processing not implemented, using parallel")
                answer_results = processor.process_answer_files_batched(
                    answer_files,
                    batch_size=args.batch_size,
                    max_workers=1
                )
            results['answers'] = answer_results
        
        # Final verification
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("��� Verifying final data...")
        processor.verify_final_data()
        
        # Summary report
        logger.info("="*60)
        logger.info("LOAD COMPLETE - SUMMARY REPORT")
        logger.info("="*60)
        
        if 'questions' in results:
            qr = results['questions']
            logger.info(f"Questions processed: {qr.get('success', 0)}")
            logger.info(f"Questions failed: {qr.get('failed', 0)}")
            if qr.get('failed_files'):
                logger.warning(f"Failed question files: {qr['failed_files']}")
        
        if 'answers' in results:
            ar = results['answers']
            logger.info(f"Gabaritos processed: {ar.get('success', 0)}")
            logger.info(f"Gabaritos failed: {ar.get('failed', 0)}")
            if ar.get('failed_files'):
                logger.warning(f"Failed gabarito files: {ar['failed_files']}")
        
        logger.info(f"Total processing time: {duration}")
        logger.info("✅ Database load completed successfully!")
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error during processing: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
