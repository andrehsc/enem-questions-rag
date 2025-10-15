#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for AI repair service - Simplified version.
"""

import pytest
import json
from unittest.mock import MagicMock

from src.enem_ingestion.ai_repair_service import (
    QuestionRepairService,
    RepairRequest,
    RepairResult,
    RepairType,
    RepairAnalyzer
)

class TestQuestionRepairService:
    """Test suite for QuestionRepairService."""
    
    @pytest.fixture
    def sample_repair_request(self):
        """Sample repair request."""
        return RepairRequest(
            question_number=1,
            original_text="Qual é a capital do Brasil? (texto incompleto...)",
            available_alternatives=["São Paulo", "Rio de Janeiro", "Brasília"],
            repair_types=[RepairType.MISSING_ALTERNATIVES, RepairType.INCOMPLETE_TEXT]
        )
    
    def test_create_repair_prompt(self, sample_repair_request):
        """Test repair prompt creation."""
        service = QuestionRepairService()
        
        prompt = service._create_repair_prompt(sample_repair_request)
        
        assert "QUESTÃO ORIGINAL" in prompt
        assert "Qual é a capital do Brasil?" in prompt
        assert "missing_alternatives" in prompt
        assert "incomplete_text" in prompt
        assert "JSON válido" in prompt
    
    def test_get_repair_instructions(self):
        """Test repair instructions generation."""
        service = QuestionRepairService()
        
        repair_types = [RepairType.MISSING_ALTERNATIVES, RepairType.OCR_ARTIFACTS]
        instructions = service._get_repair_instructions(repair_types)
        
        assert "Complete as alternativas faltantes" in instructions
        assert "Corrija caracteres mal interpretados" in instructions
    
    def test_parse_repair_response_valid_json(self, sample_repair_request):
        """Test parsing valid repair response."""
        service = QuestionRepairService()
        
        ai_response = """
        Aqui está o reparo:
        {
            "success": true,
            "repaired_question_text": "Qual é a capital do Brasil?",
            "repaired_alternatives": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Belo Horizonte"],
            "confidence_score": 0.9,
            "repairs_applied": ["Completou alternativas faltantes", "Removeu texto incompleto"],
            "warnings": [],
            "reasoning": "Questão reparada com sucesso"
        }
        """
        
        result = service._parse_repair_response(ai_response, sample_repair_request)
        
        assert result.success is True
        assert result.confidence_score == 0.9
        assert len(result.repaired_alternatives) == 5
        assert len(result.repairs_applied) == 2
    
    def test_parse_repair_response_invalid_json(self, sample_repair_request):
        """Test parsing invalid repair response."""
        service = QuestionRepairService()
        
        ai_response = "Esta resposta não contém JSON válido."
        
        result = service._parse_repair_response(ai_response, sample_repair_request)
        
        assert result.success is False
        assert result.confidence_score == 0.0
        assert "Parse error" in result.warnings[0]
    
    def test_create_fallback_result(self, sample_repair_request):
        """Test fallback result creation."""
        service = QuestionRepairService()
        
        result = service._create_fallback_result("Test error", sample_repair_request)
        
        assert result.success is False
        assert result.confidence_score == 0.0
        assert result.repaired_question_text == sample_repair_request.original_text
        assert "Test error" in result.warnings[0]

class TestRepairAnalyzer:
    """Test suite for RepairAnalyzer."""
    
    def test_analyze_question_problems_missing_alternatives(self):
        """Test detection of missing alternatives."""
        problems = RepairAnalyzer.analyze_question_problems(
            "Qual é a capital do Brasil?",
            ["São Paulo", "Rio de Janeiro"]  # Only 2 alternatives
        )
        
        assert RepairType.MISSING_ALTERNATIVES in problems
    
    def test_analyze_question_problems_incomplete_text(self):
        """Test detection of incomplete text."""
        problems = RepairAnalyzer.analyze_question_problems(
            "Texto muito curto...",  # Short and ends with ...
            ["A", "B", "C", "D", "E"]
        )
        
        assert RepairType.INCOMPLETE_TEXT in problems
    
    def test_analyze_question_problems_ocr_artifacts(self):
        """Test detection of OCR artifacts."""
        problems = RepairAnalyzer.analyze_question_problems(
            "Esta questão tem artefatos de OCR como rn e ii que devem ser corrigidos",
            ["A", "B", "C", "D", "E"]
        )
        
        assert RepairType.OCR_ARTIFACTS in problems
    
    def test_analyze_question_problems_formatting_issues(self):
        """Test detection of formatting issues."""
        problems = RepairAnalyzer.analyze_question_problems(
            "Esta questão tem    espaços duplos e\n\n\nmuitas quebras",
            ["A", "B", "C", "D", "E"]
        )
        
        assert RepairType.FORMATTING_ISSUES in problems
    
    def test_should_repair_question_missing_alternatives(self):
        """Test repair decision with missing alternatives."""
        should_repair = RepairAnalyzer.should_repair_question(
            "Questão normal com texto adequado",
            ["A", "B", "C"]  # Missing alternatives
        )
        
        assert should_repair is True
    
    def test_should_repair_question_multiple_problems(self):
        """Test repair decision with multiple problems."""
        should_repair = RepairAnalyzer.should_repair_question(
            "Texto com rn artifacts e    espaçamento",  # OCR + formatting issues
            ["A", "B", "C", "D", "E"]
        )
        
        assert should_repair is True
    
    def test_should_repair_question_short_text(self):
        """Test repair decision with very short text."""
        should_repair = RepairAnalyzer.should_repair_question(
            "Curto",  # Very short text
            ["A", "B", "C", "D", "E"]
        )
        
        assert should_repair is True
    
    def test_should_not_repair_good_question(self):
        """Test no repair needed for good question."""
        should_repair = RepairAnalyzer.should_repair_question(
            "Esta é uma questão bem estruturada do ENEM com texto completo e adequado para análise dos estudantes, apresentando um contexto claro e alternativas bem elaboradas.",
            ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Belo Horizonte"]
        )
        
        assert should_repair is False

if __name__ == "__main__":
    pytest.main([__file__])