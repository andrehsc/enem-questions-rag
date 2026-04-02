#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency Validation Script
==========================
Validates all required dependencies for enhanced PDF/image extraction.
"""

import sys
import importlib.util
from pathlib import Path

# Core dependencies for enhanced extraction
REQUIRED_DEPS = {
    'core': [
        'requests', 'beautifulsoup4', 'lxml', 'PyPDF2', 'pdfplumber'
    ],
    'pdf_image': [
        'fitz',  # PyMuPDF
        'PIL',   # Pillow
        'cv2'    # opencv-python
    ],
    'text_processing': [
        'chardet', 'unicodedata'
    ],
    'database': [
        'psycopg2', 'sqlalchemy'
    ],
    'api': [
        'fastapi', 'uvicorn'
    ],
    'testing': [
        'pytest'
    ]
}

def check_dependency(module_name):
    """Check if a dependency is available."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            return True, "OK"
        else:
            return False, "Module not found"
    except (ImportError, AttributeError, ValueError) as e:
        return False, str(e)

def validate_dependencies():
    """Validate all required dependencies."""
    print("Enhanced PDF/Image Extraction - Dependency Validation")
    print("=" * 60)
    
    all_good = True
    
    for category, deps in REQUIRED_DEPS.items():
        print(f"\n{category.upper()} Dependencies:")
        print("-" * 30)
        
        for dep in deps:
            available, status = check_dependency(dep)
            status_symbol = "✓" if available else "✗"
            print(f"  {status_symbol} {dep:<20} {status}")
            
            if not available:
                all_good = False
    
    # Test enhanced extractor
    print(f"\nENHANCED EXTRACTOR Integration:")
    print("-" * 30)
    
    try:
        sys.path.insert(0, 'src')
        from enem_ingestion.alternative_extractor import EnhancedAlternativeExtractor
        extractor = EnhancedAlternativeExtractor()
        
        # Test with sample text
        test_text = """
        Teste de extração.
        A primeira alternativa
        B segunda alternativa  
        C terceira alternativa
        D quarta alternativa
        E quinta alternativa
        """
        
        result = extractor.extract_alternatives(test_text)
        success = len(result.alternatives) == 5 and result.confidence > 0.8
        
        status_symbol = "✓" if success else "✗" 
        print(f"  {status_symbol} Enhanced Extractor    {'Working correctly' if success else 'Issues detected'}")
        
        if success:
            print(f"    - Found {len(result.alternatives)}/5 alternatives")
            print(f"    - Confidence: {result.confidence:.2f}")
            print(f"    - Strategy: {result.strategy_used.value}")
        
        if not success:
            all_good = False
            
    except Exception as e:
        print(f"  ✗ Enhanced Extractor    Error: {e}")
        all_good = False
    
    # Summary
    print(f"\n" + "=" * 60)
    if all_good:
        print("✓ ALL DEPENDENCIES VALIDATED - System ready for enhanced extraction!")
        print("\nNext steps:")
        print("  1. Run tests: python tests/test_enhanced_alternatives.py")
        print("  2. Test benchmark: python test_extraction_benchmark.py")
        print("  3. Integration test with real PDFs")
    else:
        print("✗ SOME DEPENDENCIES MISSING - Please install required packages:")
        print("\n  pip install -r requirements.txt")
        
    return all_good

if __name__ == "__main__":
    validate_dependencies()
