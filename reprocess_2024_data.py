#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from enem_ingestion.parser import EnemPDFParser
from enem_ingestion.db_integration_final import DatabaseIntegration  
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_2024_data():
    """Re-process 2024 data with improved parser."""
    
    # Initialize components
    parser = EnemPDFParser()
    db_integrator = DatabaseIntegration()
    
    # Find 2024 question files (PV = Primeira Vez, actual question booklets)
    data_dir = Path("data/downloads/2024")
    pv_files = list(data_dir.glob("*PV_impresso_D*_CD*.pdf"))
    
    print(f"Found {len(pv_files)} 2024 PV files to process")
    
    total_processed = 0
    total_questions = 0
    
    for pdf_file in pv_files:
        try:
            print(f"\nProcessing: {pdf_file.name}")
            
            # Parse questions
            questions = parser.parse_questions(pdf_file)
            print(f"  Parsed: {len(questions)} questions")
            
            if questions:
                # Process with database integrator
                results = db_integrator.process_pdf_file(str(pdf_file))
                print(f"  DB Result: {results}")
                
                total_questions += len(questions)
                total_processed += 1
            else:
                print(f"  WARNING: No questions found in {pdf_file.name}")
                
        except Exception as e:
            print(f"  ERROR processing {pdf_file.name}: {e}")
            logger.exception(f"Error processing {pdf_file}")
    
    print(f"\nSUMMARY:")
    print(f"Files processed: {total_processed}/{len(pv_files)}")
    print(f"Total questions: {total_questions}")
    print(f"Average per file: {total_questions/total_processed if total_processed > 0 else 0:.1f}")

if __name__ == "__main__":
    reprocess_2024_data()
