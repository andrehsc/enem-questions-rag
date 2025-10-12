#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from enem_ingestion.parser import EnemPDFParser
from enem_ingestion.db_integration_final import DatabaseIntegration
from pathlib import Path

def test_single_file():
    """Test processing a single file to check database fix."""
    
    parser = EnemPDFParser()
    db_integrator = DatabaseIntegration()
    
    # Test with one file
    test_file = Path("data/downloads/2024/2024_PV_impresso_D1_CD1.pdf")
    
    print(f"Testing: {test_file.name}")
    
    try:
        # Parse questions
        questions = parser.parse_questions(test_file)
        print(f"Parsed: {len(questions)} questions")
        
        if questions:
            # Process with database integrator
            results = db_integrator.process_pdf_file(str(test_file))
            print(f"DB Result: {results}")
        else:
            print("No questions found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file()
