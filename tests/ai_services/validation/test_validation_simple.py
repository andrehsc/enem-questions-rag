#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified tests for AI validation service - Core functionality only.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.ai_services.validation.service import QuestionValidationService
from src.ai_services.common.base_types import EnemQuestionData
from src.ai_services.common.llama_client import LLamaAPIClient, DefaultServiceConfig


class TestQuestionValidationServiceSimplified:
    """Simplified test suite focusing on core functionality."""
    
    def test_service_initialization(self):
        """Test service can be initialized with dependency injection."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        
        # Act
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        # Assert
        assert service._llama_client == mock_client
        assert service.config == mock_config
        assert hasattr(service, 'process_request')
        assert hasattr(service, 'process_batch')
    
    def test_legacy_compatibility_methods_exist(self):
        """Test that legacy compatibility methods exist."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        # Assert - Check that legacy methods exist
        assert hasattr(service, 'parse_ai_response')
        assert hasattr(service, 'create_fallback_result')
        assert hasattr(service, 'create_validation_prompt')
        assert hasattr(service, '_parse_ai_response')
        assert hasattr(service, '_create_fallback_result')
    
    def test_parse_ai_response_valid_json(self):
        """Test parsing valid JSON response."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        valid_json = '{"valid": true, "confidence": 0.9, "issues": [], "suggestions": []}'
        
        # Act
        result = service.parse_ai_response(valid_json)
        
        # Assert
        assert result['valid'] is True
        assert result['confidence'] == 0.9
        assert result['issues'] == []
        assert result['suggestions'] == []
    
    def test_parse_ai_response_invalid_json(self):
        """Test parsing invalid JSON falls back gracefully."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        invalid_json = "invalid json response"
        
        # Act
        result = service.parse_ai_response(invalid_json)
        
        # Assert
        assert result['valid'] is False
        assert result['confidence'] == 0.0
        assert 'Failed to parse AI response' in result['issues']
    
    def test_create_fallback_result(self):
        """Test fallback result creation."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        # Act
        result = service.create_fallback_result()
        
        # Assert
        assert result['valid'] is False
        assert result['confidence'] == 0.0
        assert 'Failed to parse AI response' in result['issues']
        assert result['suggestions'] == []
    
    def test_create_validation_prompt(self):
        """Test validation prompt creation."""
        # Arrange
        mock_client = Mock(spec=LLamaAPIClient)
        mock_config = Mock(spec=DefaultServiceConfig)
        service = QuestionValidationService(config=mock_config, llama_client=mock_client)
        
        # Create a simple request object
        request = Mock()
        request.question_text = "Test question?"
        request.question_type = "multiple_choice"
        request.context = "Test context"
        
        # Act
        prompt = service.create_validation_prompt(request)
        
        # Assert
        assert "Test question?" in prompt
        assert "multiple_choice" in prompt
        assert "Test context" in prompt
        assert "JSON" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
