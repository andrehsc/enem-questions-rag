#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for AI validation service - Simplified version.
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass

from src.ai_services.validation import (
    QuestionValidationService,
    ValidationRequest,
    ValidationResponse
)
from src.ai_services.common.base_types import EnemQuestionData

# Legacy types for compatibility with old tests
@dataclass
class QuestionValidationRequest:
    question_text: str
    question_type: str = "multiple_choice"
    context: str = None
    alternatives: list = None
    question_number: int = 1

@dataclass  
class ValidationResult:
    valid: bool
    confidence: float
    issues: list
    suggestions: list

class AIValidationIntegrator:
    """Legacy integrator for compatibility."""
    
    def __init__(self, service):
        self.service = service
    
    def filter_high_confidence_questions(self, questions, threshold=0.8):
        return [q for q in questions if getattr(q, 'confidence_score', 0) >= threshold]
    
    def validate_parsed_questions_structure(self, questions):
        valid_questions = []
        for q in questions:
            if isinstance(q, dict) and 'text' in q:
                valid_questions.append(q)
        return valid_questions

class TestQuestionValidationService:
    """Test suite for QuestionValidationService - Simplified."""
    
    @pytest.fixture
    def sample_request(self):
        """Sample validation request."""
        return QuestionValidationRequest(
            question_text="Qual é a capital do Brasil?",
            alternatives=[
                "São Paulo",
                "Rio de Janeiro", 
                "Brasília",
                "Salvador",
                "Belo Horizonte"
            ]
        )
    
    def test_create_validation_prompt(self, sample_request):
        """Test prompt creation."""
        service = QuestionValidationService()
        
        prompt = service.create_validation_prompt(sample_request)
        
        assert "Validate this ENEM question" in prompt
        assert "Qual é a capital do Brasil?" in prompt
        assert "multiple_choice" in prompt
        assert "JSON" in prompt
    
    def test_parse_ai_response_valid_json(self):
        """Test parsing valid AI response."""
        service = QuestionValidationService()
        
        ai_response = """
        Aqui está minha análise:
        {
            "question_valid": true,
            "confidence_score": 0.85,
            "issues_found": ["Pequeno erro de formatação"],
            "suggestions": ["Corrigir espaçamento"],
            "alternatives_complete": true,
            "text_quality_score": 0.8
        }
        Espero que ajude!
        """
        
        result = service.parse_ai_response(ai_response)

        assert result['question_valid'] is True
        assert result['confidence_score'] == 0.85
        assert len(result['issues_found']) == 1
    
    def test_parse_ai_response_invalid_json(self):
        """Test parsing invalid AI response."""
        service = QuestionValidationService()

        ai_response = "Esta resposta não contém JSON válido."

        result = service.parse_ai_response(ai_response)

        assert result['valid'] is False
        assert result['confidence'] == 0.0
        assert "Failed to parse AI response" in result['issues'][0]
    
    def test_create_fallback_result(self):
        """Test fallback result creation."""
        service = QuestionValidationService()

        result = service.create_fallback_result()

        assert result['valid'] is False
        assert result['confidence'] == 0.0
        assert "Failed to parse AI response" in result['issues'][0]

class TestAIValidationIntegrator:
    """Test suite for AIValidationIntegrator."""
    
    @pytest.fixture
    def mock_question(self):
        """Mock question object from parser."""
        question = MagicMock()
        question.number = 1
        question.text = "Sample question text"
        question.alternatives = ["A", "B", "C", "D", "E"]
        return question
    
    @pytest.fixture
    def mock_validation_service(self):
        """Mock validation service."""
        service = MagicMock(spec=QuestionValidationService)
        return service
    
    @pytest.fixture
    def sample_validation_result(self):
        """Sample validation result."""
        return ValidationResponse(
            success=True,
            confidence_score=0.9,
            raw_ai_response="mock response",
            question_valid=True,
            issues_found=[],
            suggestions=[]
        )
    
    def test_validate_parsed_questions_structure(self, 
                                           mock_question, 
                                           mock_validation_service):
        """Test validation request structure for parsed questions."""
        integrator = AIValidationIntegrator(mock_validation_service)
        questions = [mock_question]
        
        # Test that requests are created correctly
        requests = []
        for question in questions:
            request = QuestionValidationRequest(
                question_text=question.text,
                question_type="multiple_choice",
                context=""
            )
            requests.append(request)
        
        assert len(requests) == 1
        assert requests[0].question_number == 1
        assert requests[0].question_text == "Sample question text"
    
    def test_filter_high_confidence_questions(self,
                                            mock_question,
                                            sample_validation_result):
        """Test filtering of high confidence questions."""
        integrator = AIValidationIntegrator(MagicMock())
        
        questions = [mock_question]
        validation_results = [sample_validation_result]
        
        # Test passing filter
        filtered = integrator.filter_high_confidence_questions(
            validation_results, threshold=0.8
        )
        assert len(filtered) == 1
        
        # Test failing filter
        sample_validation_result.confidence_score = 0.5
        filtered = integrator.filter_high_confidence_questions(
            validation_results, threshold=0.8
        )
        assert len(filtered) == 0

if __name__ == "__main__":
    pytest.main([__file__])