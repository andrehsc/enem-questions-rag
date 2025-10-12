#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM RAG SYSTEM - COMPLETE DATABASE LOADER
============================================
This script performs a complete data load for the ENEM RAG system.
It processes all PDFs and loads questions, alternatives, and answer keys.

Usage:
    python scripts/load_database_complete.py [options]

Options:
    --clear-db          Clear all data before loading
    --parallel          Use parallel processing (default: True)
    --workers N         Number of parallel workers (default: 4)
    --batch-size N      Batch size for processing (default: 8)
    --questions-only    Load only questions (skip gabaritos)
    --gabaritos-only    Load only gabaritos (skip questions)
    --verbose           Enable verbose output
"""

import argparse
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

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
    ‚Ä¢ Questions from PDF files (PV)
    ‚Ä¢ Answer keys from gabarito files (GB)  
    ‚Ä¢ Exam metadata and relationships
    
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
        print(f"‚ùå Missing required directories: {missing_dirs}")
        return False
    
    # Check if we have PDF files
    pdf_count = len(list(Path("data/downloads").rglob("*.pdf")))
    if pdf_count == 0:
        print("‚ùå No PDF files found in data/downloads")
        return False
    
    print(f"‚úÖ Found {pdf_count} PDF files to process")
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
            logger.info("Ì∑ëÔ∏è  Clearing database...")
            processor.clear_database()
            logger.info("‚úÖ Database cleared successfully")
        
        # Find files to process
        question_files = processor.find_question_files()
        answer_files = processor.find_answer_files()
        
        logger.info(f"Found {len(question_files)} question files")
        logger.info(f"Found {len(answer_files)} answer files")
        
        # Process based on options
        start_time = datetime.now()
        results = {}
        
        if not args.gabaritos_only:
            logger.info("Ì¥Ñ Processing questions...")
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
            logger.info("Ì¥Ñ Processing gabaritos...")
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
        
        logger.info("Ì¥ç Verifying final data...")
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
        logger.info("‚úÖ Database load completed successfully!")
        
    except KeyboardInterrupt:
        logger.warning("‚ö†Ô∏è  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"‚ùå Fatal error during processing: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
