#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from enem_ingestion.parser import EnemPDFParser
from pathlib import Path
import json

def test_2024_parsing():
    """Test parsing improvements on 2024 files."""
    parser = EnemPDFParser()
    
    # Find a 2024 file to test
    test_file = Path("data/downloads/2024/2024_PV_impresso_D1_CD1.pdf")
    if not test_file.exists():
        print("No 2024 test file found")
        return
    
    print(f"Testing parser improvements on: {test_file}")
    
    try:
        # First, let's see what the raw extraction gives us
        import pdfplumber
        with pdfplumber.open(test_file) as pdf:
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text()
                print(f"\nFirst page raw text preview (first 500 chars):")
                print(repr(first_page_text[:500]) if first_page_text else "No text extracted")
                
                # Look for question patterns
                import re
                question_pattern = re.compile(r'QUESTÃO\s+(\d+)', re.IGNORECASE)
                matches = question_pattern.findall(first_page_text or "")
                print(f"\nFound question patterns: {matches}")
        
        questions = parser.parse_questions(test_file)
        print(f"\nParsed {len(questions)} questions")
        
        if questions:
            # Show first question
            first_q = questions[0]
            print(f"\nFirst question (#{first_q.number}):")
            print(f"Text length: {len(first_q.text)} characters")
            print(f"Text preview: {first_q.text[:300]}...")
            print(f"Alternatives: {len(first_q.alternatives)}")
            for i, alt in enumerate(first_q.alternatives[:5]):  # Show all 5
                print(f"  {i+1}. {alt[:100]}...")
                
            # Check for repetitive patterns
            if 'ENEM2024' in first_q.text:
                print("\n⚠️ WARNING: Still contains ENEM2024 patterns")
            else:
                print("\n✅ ENEM2024 patterns successfully removed")
        else:
            print("\n⚠️ No questions found - debugging extraction process")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_2024_parsing()
