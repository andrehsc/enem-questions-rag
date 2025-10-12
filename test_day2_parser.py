#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from enem_ingestion.parser import EnemPDFParser
from pathlib import Path

def test_day2_parsing():
    """Test improved parser on Day 2 files (Math/Science)."""
    
    parser = EnemPDFParser()
    
    # Test with a Day 2 file
    test_file = Path("data/downloads/2024/2024_PV_impresso_D2_CD5.pdf")
    
    print(f"Testing Day 2 parser improvements: {test_file.name}")
    
    try:
        questions = parser.parse_questions(test_file)
        print(f"Parsed: {len(questions)} questions")
        
        # Count questions by alternatives found
        alt_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for q in questions:
            alt_count = len(q.alternatives)
            alt_counts[alt_count] = alt_counts.get(alt_count, 0) + 1
        
        print(f"\nAlternatives distribution:")
        for count, num_questions in alt_counts.items():
            if num_questions > 0:
                print(f"  {count} alternatives: {num_questions} questions")
        
        # Check some specific questions that had problems before
        problem_questions = [91, 92, 94, 96, 102, 103]
        print(f"\nChecking previously problematic questions:")
        
        for q in questions:
            if q.number in problem_questions:
                print(f"  Q{q.number}: {len(q.alternatives)} alternatives")
                for i, alt in enumerate(q.alternatives):
                    print(f"    {alt[:60]}...")
                    if i >= 2:  # Show first 3 alternatives
                        break
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_day2_parsing()
