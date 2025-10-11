#!/usr/bin/env python3
"""
Test database integration with real ENEM PDF files.

This script tests the complete pipeline from PDF parsing to database storage
using actual ENEM files from our downloads directory.
"""

import os
import sys
from pathlib import Path
import time

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from enem_ingestion.db_integration import DatabaseIntegration
import dotenv

# Load environment variables
dotenv.load_dotenv()


def test_single_file_integration():
    """Test integration with a single file."""
    print("🧪 Testing single file integration...")
    
    # Initialize database integration
    db = DatabaseIntegration()
    
    # Test connection
    if not db.test_connection():
        print("❌ Database connection failed!")
        return False
    
    print("✅ Database connection successful")
    
    # Find a gabarito file to test
    data_dir = Path("data/downloads")
    gabarito_files = list(data_dir.rglob("*GB*.pdf"))
    
    if not gabarito_files:
        print("❌ No gabarito files found!")
        return False
    
    # Test with first gabarito
    test_file = gabarito_files[0]
    print(f"📄 Testing with: {test_file}")
    
    result = db.process_pdf_file(test_file)
    
    if result['success']:
        print(f"✅ File processed successfully!")
        print(f"   📊 File type: {result['file_type']}")
        print(f"   📋 Metadata ID: {result['metadata_id']}")
        if 'answer_keys_inserted' in result:
            print(f"   📝 Answer keys inserted: {result['answer_keys_inserted']}")
        if 'questions_inserted' in result:
            print(f"   ❓ Questions inserted: {result['questions_inserted']}")
        return True
    else:
        print(f"❌ File processing failed: {result.get('error', 'Unknown error')}")
        return False


def test_batch_integration():
    """Test integration with multiple files."""
    print("\n🔄 Testing batch integration...")
    
    db = DatabaseIntegration()
    
    # Find files to process (limit to a few for testing)
    data_dir = Path("data/downloads")
    all_files = list(data_dir.rglob("*.pdf"))
    
    # Select a small sample for testing (max 5 files)
    test_files = all_files[:5]
    
    print(f"📁 Processing {len(test_files)} files...")
    
    results = {
        'successful': 0,
        'failed': 0,
        'total_gabaritos': 0,
        'total_cadernos': 0,
        'total_answers': 0,
        'total_questions': 0
    }
    
    for i, file_path in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] Processing: {file_path.name}")
        
        result = db.process_pdf_file(file_path)
        
        if result['success']:
            results['successful'] += 1
            
            if result['file_type'] == 'gabarito':
                results['total_gabaritos'] += 1
                results['total_answers'] += result.get('answer_keys_inserted', 0)
            elif result['file_type'] == 'caderno_questoes':
                results['total_cadernos'] += 1  
                results['total_questions'] += result.get('questions_inserted', 0)
                
            print(f"  ✅ Success")
        else:
            results['failed'] += 1
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
    
    print(f"\n📊 Batch Results:")
    print(f"   ✅ Successful: {results['successful']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   📋 Gabaritos: {results['total_gabaritos']}")
    print(f"   📄 Cadernos: {results['total_cadernos']}")
    print(f"   📝 Total answers: {results['total_answers']}")
    print(f"   ❓ Total questions: {results['total_questions']}")
    
    return results['successful'] > 0


def test_database_queries():
    """Test database queries and statistics."""
    print("\n📊 Testing database queries...")
    
    db = DatabaseIntegration()
    
    # Get statistics
    stats = db.get_statistics()
    
    if stats:
        print("📈 Database Statistics:")
        print(f"   📂 Total exams: {stats.get('total_exams', 0)}")
        print(f"   ❓ Total questions: {stats.get('total_questions', 0)}")
        print(f"   📝 Total alternatives: {stats.get('total_alternatives', 0)}")
        print(f"   🎯 Avg confidence: {stats.get('avg_confidence', 0):.3f}")
        print(f"   🖼️  Questions with images: {stats.get('questions_with_images', 0)}")
        print(f"   📅 Years covered: {stats.get('years_covered', [])}")
    else:
        print("⚠️  No statistics available")
    
    # Test search functionality
    print("\n🔍 Testing search functionality...")
    
    search_terms = ["matemática", "português", "química", "história"]
    
    for term in search_terms:
        results = db.search_questions(term, limit=3)
        print(f"   🔎 '{term}': {len(results)} results")
        
        for result in results[:2]:  # Show first 2 results
            print(f"      Q{result['question_number']} ({result['year']}) - Score: {result['similarity_score']:.3f}")
    
    return True


def test_performance():
    """Test performance with timing."""
    print("\n⏱️  Testing performance...")
    
    db = DatabaseIntegration()
    
    # Find a few files for performance testing
    data_dir = Path("data/downloads")
    test_files = list(data_dir.rglob("*.pdf"))[:3]
    
    start_time = time.time()
    
    for file_path in test_files:
        file_start = time.time()
        result = db.process_pdf_file(file_path)
        file_time = time.time() - file_start
        
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {file_path.name}: {file_time:.2f}s")
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_files) if test_files else 0
    
    print(f"📊 Performance Results:")
    print(f"   ⏱️  Total time: {total_time:.2f}s")
    print(f"   📊 Average per file: {avg_time:.2f}s")
    print(f"   📈 Files per minute: {60/avg_time:.1f}" if avg_time > 0 else "   📈 Files per minute: N/A")
    
    return True


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 ENEM Database Integration Test")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    try:
        # Test 1: Single file integration
        if test_single_file_integration():
            tests_passed += 1
        
        # Test 2: Batch integration
        if test_batch_integration():
            tests_passed += 1
        
        # Test 3: Database queries
        if test_database_queries():
            tests_passed += 1
        
        # Test 4: Performance
        if test_performance():
            tests_passed += 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())