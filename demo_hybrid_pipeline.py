#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo script for AI-Enhanced ENEM Parser Hybrid Pipeline
Demonstrates the integration of traditional parsing with AI services.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.enem_ingestion.ai_enhanced_parser import AIEnhancedEnemParser, create_ai_enhanced_parser
from src.enem_ingestion.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoConfig(Config):
    """Demo configuration for AI-enhanced parser."""
    
    def __init__(self):
        super().__init__()
        self.ai_confidence_threshold = 0.4
        self.ai_batch_size = 3  # Smaller batches for demo
        self.enable_missing_detection = True
        self.enable_repair = True


async def demo_hybrid_extraction():
    """Demonstrate the hybrid AI-enhanced extraction pipeline."""
    
    print("Ì∫Ä AI-Enhanced ENEM Parser - Hybrid Pipeline Demo")
    print("=" * 60)
    
    # Create parser with demo configuration
    config = DemoConfig()
    parser = create_ai_enhanced_parser(config)
    
    print(f"‚úÖ Parser initialized with:")
    print(f"   - Confidence threshold: {config.ai_confidence_threshold}")
    print(f"   - Batch size: {config.ai_batch_size}")
    print(f"   - Missing detection: {config.enable_missing_detection}")
    print(f"   - Repair enabled: {config.enable_repair}")
    print()
    
    # Find a sample PDF to process
    data_dir = Path("data/downloads")
    if data_dir.exists():
        pdf_files = list(data_dir.glob("*.pdf"))
        if pdf_files:
            sample_pdf = pdf_files[0]
            print(f"Ì≥Ñ Processing sample PDF: {sample_pdf.name}")
            print()
            
            try:
                # Process with hybrid pipeline
                result = await parser.extract_questions_hybrid(sample_pdf)
                
                # Display results
                print("Ì≥ä Extraction Results:")
                print(f"   ‚úÖ Success: {result.success}")
                print(f"   Ì≥ö Total questions found: {len(result.questions)}")
                print(f"   Ì¥ç Traditional extraction: {result.traditional_count}")
                print(f"   ‚úîÔ∏è  AI validated: {result.ai_validated_count}")
                print(f"   Ì¥ß AI repaired: {result.ai_repaired_count}")
                print(f"   ÌµµÔ∏è  Missing detected: {result.ai_missing_detected}")
                print(f"   ‚è±Ô∏è  Processing time: {result.processing_time_seconds:.2f}s")
                print()
                
                # Display confidence scores
                if result.confidence_scores:
                    print("ÌæØ Confidence Scores:")
                    for question_num, confidence in sorted(result.confidence_scores.items()):
                        emoji = "Ìø¢" if confidence > 0.8 else "Ìø°" if confidence > 0.5 else "Ì¥¥"
                        print(f"   Question {question_num}: {confidence:.2f} {emoji}")
                    print()
                
                # Display issues if any
                if result.issues_found:
                    print("‚ö†Ô∏è  Issues Found:")
                    for issue in result.issues_found[:5]:  # Show first 5 issues
                        print(f"   - {issue}")
                    if len(result.issues_found) > 5:
                        print(f"   ... and {len(result.issues_found) - 5} more")
                    print()
                
                # Calculate and display metrics
                metrics = parser.calculate_metrics(result, sample_pdf.name)
                print("Ì≥à Performance Metrics:")
                print(f"   Ì≥ä Improvement: {metrics.improvement_percentage:.1f}%")
                print(f"   ÌæØ Extraction rate: {metrics.final_extraction_rate:.1f}%")
                print(f"   Ì¥ß AI repairs: {metrics.ai_repaired_questions}")
                print(f"   ÌµµÔ∏è  Missing found: {metrics.ai_missing_detected}")
                print()
                
                # Show sample questions
                if result.questions:
                    print("Ì≥ù Sample Questions (first 2):")
                    for i, question in enumerate(result.questions[:2]):
                        print(f"\n   Question {question.get('number', i+1)}:")
                        text = question.get('text', '')[:100] + "..." if len(question.get('text', '')) > 100 else question.get('text', '')
                        print(f"   Text: {text}")
                        print(f"   Alternatives: {len(question.get('alternatives', []))} found")
                        metadata = question.get('metadata', {})
                        method = metadata.get('extraction_method', 'unknown')
                        confidence = metadata.get('confidence', 0.0)
                        print(f"   Method: {method} (confidence: {confidence:.2f})")
                
                print("\nÌæâ Hybrid pipeline demo completed successfully!")
                
            except Exception as e:
                logger.error(f"Demo failed: {e}")
                print(f"‚ùå Demo failed: {e}")
                
        else:
            print("‚ùå No PDF files found in data/downloads/")
            print("   Please add some ENEM PDF files to test the pipeline.")
            
    else:
        print("‚ùå data/downloads/ directory not found.")
        print("   Please create the directory and add ENEM PDF files.")


def demo_architecture_explanation():
    """Explain the SOLID architecture of the hybrid pipeline."""
    
    print("\n" + "=" * 60)
    print("ÌøóÔ∏è  SOLID Architecture Explanation")
    print("=" * 60)
    
    print("\nÌ≥ê Single Responsibility Principle (SRP):")
    print("   ‚úÖ AIEnhancedEnemParser: Orchestrates the pipeline")
    print("   ‚úÖ QuestionValidationService: Validates question quality")
    print("   ‚úÖ QuestionRepairService: Repairs malformed questions")
    print("   ‚úÖ MissingQuestionDetector: Finds missing questions")
    print("   ‚úÖ ExtractionResult: Data container for results")
    
    print("\nÌ¥ì Open/Closed Principle (OCP):")
    print("   ‚úÖ Easy to add new AI services without changing existing code")
    print("   ‚úÖ New repair types can be added via RepairType enum")
    print("   ‚úÖ Pipeline phases are extensible")
    
    print("\nÌ¥Ñ Liskov Substitution Principle (LSP):")
    print("   ‚úÖ All AI services implement AIServiceInterface")
    print("   ‚úÖ Different LLama clients can be substituted")
    print("   ‚úÖ Config objects are interchangeable")
    
    print("\nÌ¥ß Interface Segregation Principle (ISP):")
    print("   ‚úÖ AIServiceInterface: Core service operations")
    print("   ‚úÖ LLamaClientInterface: API client operations")
    print("   ‚úÖ ServiceConfigInterface: Configuration management")
    
    print("\n‚ö° Dependency Inversion Principle (DIP):")
    print("   ‚úÖ Parser depends on abstractions (interfaces)")
    print("   ‚úÖ Services injected via constructor")
    print("   ‚úÖ Easy to mock for testing")
    
    print("\nÌ¥Ñ Hybrid Pipeline Flow:")
    print("   1Ô∏è‚É£  Traditional Parser: Baseline extraction")
    print("   2Ô∏è‚É£  AI Validation: Validate each question")
    print("   3Ô∏è‚É£  AI Repair: Fix low-confidence questions")
    print("   4Ô∏è‚É£  Missing Detection: Find lost questions")
    print("   5Ô∏è‚É£  Results Compilation: Merge all results")
    
    print("\nÌæØ Benefits Achieved:")
    print("   ‚úÖ Maintainable: Clear separation of concerns")
    print("   ‚úÖ Testable: Dependency injection for mocking")
    print("   ‚úÖ Extensible: Easy to add new AI services")
    print("   ‚úÖ Robust: Graceful fallback to traditional parsing")
    print("   ‚úÖ Performance: Batch processing and parallel execution")


async def main():
    """Main demo function."""
    try:
        await demo_hybrid_extraction()
        demo_architecture_explanation()
        
    except KeyboardInterrupt:
        print("\n‚è∏Ô∏è  Demo interrupted by user.")
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        print(f"\n‚ùå Demo failed: {e}")


if __name__ == "__main__":
    print("Ì¥ñ Starting AI-Enhanced ENEM Parser Demo...")
    asyncio.run(main())
