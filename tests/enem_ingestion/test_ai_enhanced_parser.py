#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for AI-Enhanced ENEM Parser Hybrid Pipeline
Validates SOLID architecture and integration between traditional + AI services.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.enem_ingestion.ai_enhanced_parser import (
    AIEnhancedEnemParser, 
    ExtractionResult, 
    ExtractionMetrics,
    create_ai_enhanced_parser
)
from src.ai_services.common.base_types import EnemQuestionData
from src.ai_services.repair.service import RepairType


class TestAIEnhancedEnemParser:
    """Test suite for AI-Enhanced ENEM Parser."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock configuration
        self.mock_config = Mock()
        self.mock_config.ai_confidence_threshold = 0.4
        self.mock_config.ai_batch_size = 3
        self.mock_config.enable_missing_detection = True
        self.mock_config.enable_repair = True
        
        # Mock services
        self.mock_traditional_parser = Mock()
        self.mock_ai_validator = AsyncMock()
        self.mock_ai_repairer = AsyncMock() 
        self.mock_missing_detector = AsyncMock()
        
        # Create parser with mocked dependencies
        self.parser = AIEnhancedEnemParser(self.mock_config)
        self.parser.traditional_parser = self.mock_traditional_parser
        self.parser.ai_validator = self.mock_ai_validator
        self.parser.ai_repairer = self.mock_ai_repairer
        self.parser.missing_detector = self.mock_missing_detector
    
    def test_determine_repair_types_missing_alternatives(self):
        """Test repair type detection for missing alternatives."""
        # Arrange
        question = {
            'text': 'This is a complete question text with sufficient length for processing.',
            'alternatives': ['A) Answer 1', 'B) Answer 2']  # Only 2 alternatives, should be 5
        }
        
        # Act
        repair_types = self.parser._determine_repair_types(question)
        
        # Assert
        assert RepairType.MISSING_ALTERNATIVES in repair_types
    
    def test_determine_repair_types_ocr_artifacts(self):
        """Test repair type detection for OCR artifacts."""
        # Arrange
        question = {
            'text': 'Question with OCR artifacts like □ and ■ symbols and ﬁ ligature',
            'alternatives': ['A) Alt1', 'B) Alt2', 'C) Alt3', 'D) Alt4', 'E) Alt5']
        }
        
        # Act
        repair_types = self.parser._determine_repair_types(question)
        
        # Assert
        assert RepairType.OCR_ARTIFACTS in repair_types
    
    def test_estimate_question_range_day_1(self):
        """Test question range estimation for day 1 (1-45)."""
        # Arrange
        found_numbers = [1, 5, 10, 20, 35]
        
        # Act
        range_estimate = self.parser._estimate_question_range(found_numbers)
        
        # Assert
        assert range_estimate == (1, 45)
    
    def test_calculate_confidence_scores(self):
        """Test confidence score calculation from questions."""
        # Arrange
        questions = [
            {'number': 1, 'metadata': {'confidence': 0.9}},
            {'number': 2, 'metadata': {'confidence': 0.7}},
            {'number': 3, 'metadata': {}}  # No confidence, should default to 0.5
        ]
        
        # Act
        confidence_scores = self.parser._calculate_confidence_scores(questions)
        
        # Assert
        assert confidence_scores[1] == 0.9
        assert confidence_scores[2] == 0.7
        assert confidence_scores[3] == 0.5
    
    def test_calculate_metrics(self):
        """Test extraction metrics calculation."""
        # Arrange
        result = ExtractionResult(
            questions=[
                {'number': 1, 'text': 'Q1'},
                {'number': 2, 'text': 'Q2'},
                {'number': 3, 'text': 'Q3'}
            ],
            traditional_count=2,
            ai_validated_count=3,
            ai_repaired_count=1,
            ai_missing_detected=1,
            processing_time_seconds=5.5,
            confidence_scores={1: 0.9, 2: 0.8, 3: 0.7},
            issues_found=[]
        )
        
        # Act
        metrics = self.parser.calculate_metrics(result, "test.pdf")
        
        # Assert
        assert metrics.pdf_filename == "test.pdf"
        assert metrics.traditional_questions_found == 2
        assert metrics.ai_questions_found == 3
        assert metrics.ai_repaired_questions == 1
        assert metrics.ai_missing_detected == 1
        assert metrics.improvement_percentage == 50.0  # (3-2)/2 * 100


class TestFactoryFunction:
    """Test suite for factory function."""
    
    def test_create_ai_enhanced_parser_default_config(self):
        """Test factory function with default configuration."""
        # Act
        parser = create_ai_enhanced_parser()
        
        # Assert
        assert isinstance(parser, AIEnhancedEnemParser)
        assert parser.confidence_threshold == 0.4  # Default value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
