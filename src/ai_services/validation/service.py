#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-powered question validation service for ENEM PDF extraction.
Refactored following SOLID principles and Clean Code practices.
"""

import logging
import json
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..common.base_types import (
    AIRequest, AIResponse, AIServiceInterface, EnemQuestionData,
    ServiceConfigInterface, LLamaClientInterface
)
from ..common.llama_client import LLamaAPIClient, DefaultServiceConfig, BatchProcessor

logger = logging.getLogger(__name__)


@dataclass
class ValidationRequest(AIRequest):
    """Request for question validation - extends base AIRequest."""
    question_data: Optional[EnemQuestionData] = None
    validation_criteria: Optional[List[str]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.validation_criteria is None:
            self.validation_criteria = [
                "completeness", "alternatives_count", "text_quality", 
                "ocr_artifacts", "question_numbering"
            ]


@dataclass
class ValidationResponse(AIResponse):
    """Response from validation service - extends base AIResponse."""
    question_valid: bool = False
    issues_found: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    alternatives_complete: bool = False
    text_quality_score: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        if self.issues_found is None:
            self.issues_found = []
        if self.suggestions is None:
            self.suggestions = []


class ValidationPromptBuilder:
    """Builds validation prompts following Single Responsibility Principle."""
    
    @staticmethod
    def create_validation_prompt(request: ValidationRequest) -> str:
        """Create validation prompt for LLama3.
        
        Args:
            request: Validation request with question data
            
        Returns:
            Formatted prompt string
        """
        question = request.question_data
        
        # Build alternatives section
        alternatives_text = ""
        if question.alternatives:
            for i, alt in enumerate(question.alternatives[:5]):  # Max 5 alternatives
                letter = chr(65 + i)  # A, B, C, D, E
                alternatives_text += f"{letter}) {alt}\n"
        
        prompt = f"""
Analise se esta questão ENEM foi extraída corretamente de um PDF:

QUESTÃO #{question.number or 'N/A'}:
{question.text}

ALTERNATIVAS:
{alternatives_text}

METADADOS:
- Ano: {question.metadata.get('year', 'N/A')}
- Matéria: {question.metadata.get('subject', 'N/A')}
- Caderno: {question.metadata.get('caderno', 'N/A')}

Avalie seguindo critérios:
1. Enunciado está completo e faz sentido?
2. Tem exatamente 5 alternativas (A-E)?  
3. Alternativas estão bem formatadas?
4. Texto não tem artifacts OCR (caracteres estranhos)?
5. Numeração da questão é consistente?

Responda APENAS com JSON válido:
{{
  "question_valid": true,
  "confidence_score": 0.95,
  "issues_found": [],
  "suggestions": [],
  "alternatives_complete": true,
  "text_quality_score": 0.9,
  "reasoning": "Questão bem extraída, sem problemas detectados"
}}
"""
        return prompt


class ValidationResponseParser:
    """Parses AI responses following Single Responsibility Principle."""
    
    @staticmethod
    def parse_response(ai_response: str, request: ValidationRequest) -> ValidationResponse:
        """Parse AI response into ValidationResponse.
        
        Args:
            ai_response: Raw AI response text
            request: Original validation request
            
        Returns:
            Parsed ValidationResponse
        """
        try:
            # Extract JSON from response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return ValidationResponseParser._create_fallback_response(
                    "No valid JSON found in AI response", ai_response
                )
            
            json_str = ai_response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return ValidationResponse(
                success=True,
                confidence_score=float(parsed.get("confidence_score", 0.0)),
                raw_ai_response=ai_response,
                question_valid=parsed.get("question_valid", False),
                issues_found=parsed.get("issues_found", []),
                suggestions=parsed.get("suggestions", []),
                alternatives_complete=parsed.get("alternatives_complete", False),
                text_quality_score=float(parsed.get("text_quality_score", 0.0))
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse validation response: {e}")
            return ValidationResponseParser._create_fallback_response(
                f"Parse error: {str(e)}", ai_response
            )
    
    @staticmethod
    def _create_fallback_response(error_msg: str, raw_response: str) -> ValidationResponse:
        """Create fallback response when parsing fails."""
        return ValidationResponse(
            success=False,
            confidence_score=0.0,
            raw_ai_response=raw_response,
            question_valid=False,
            issues_found=[f"AI validation failed: {error_msg}"],
            suggestions=["Manual review required"],
            alternatives_complete=False,
            text_quality_score=0.0,
            warnings=[error_msg]
        )


class QuestionValidationService(AIServiceInterface):
    """AI-powered validation service following Interface Segregation Principle."""
    
    def __init__(self, 
                 config: Optional[ServiceConfigInterface] = None,
                 llama_client: Optional[LLamaClientInterface] = None):
        """Initialize validation service with dependency injection.
        
        Args:
            config: Service configuration (uses default if None)
            llama_client: LLama client instance (creates default if None)
        """
        self.config = config or DefaultServiceConfig()
        self._llama_client = llama_client
        self.prompt_builder = ValidationPromptBuilder()
        self.response_parser = ValidationResponseParser()
        self.batch_processor = BatchProcessor(max_concurrent=3)
        
    async def process_request(self, request: ValidationRequest) -> ValidationResponse:
        """Process single validation request.
        
        Args:
            request: Validation request
            
        Returns:
            Validation response
        """
        try:
            # Validate input data first
            issues = request.question_data.validate()
            if issues:
                return ValidationResponse(
                    success=False,
                    confidence_score=0.0,
                    raw_ai_response="",
                    question_valid=False,
                    issues_found=issues,
                    suggestions=["Fix data validation issues before AI processing"],
                    warnings=["Input validation failed"]
                )
            
            # Create prompt
            prompt = self.prompt_builder.create_validation_prompt(request)
            
            # Call AI service
            async with LLamaAPIClient(self.config) as client:
                ai_response = await client.call_api(prompt)
            
            # Parse response
            return self.response_parser.parse_response(ai_response, request)
            
        except Exception as e:
            logger.error(f"Validation service error: {e}")
            return ValidationResponse(
                success=False,
                confidence_score=0.0,
                raw_ai_response=f"ERROR: {str(e)}",
                question_valid=False,
                issues_found=[f"Service error: {str(e)}"],
                suggestions=["Retry with manual validation"],
                warnings=[str(e)]
            )
    
    async def process_batch(self, requests: List[ValidationRequest]) -> List[ValidationResponse]:
        """Process multiple validation requests in batch.
        
        Args:
            requests: List of validation requests
            
        Returns:
            List of validation responses in same order
        """
        if not requests:
            return []
        
        try:
            # Build prompts for all requests
            prompts = [self.prompt_builder.create_validation_prompt(req) for req in requests]
            
            # Process in batch with concurrency control
            async with LLamaAPIClient(self.config) as client:
                responses = await self.batch_processor.process_batch_with_semaphore(
                    client, prompts
                )
            
            # Parse all responses
            results = []
            for i, (request, response) in enumerate(zip(requests, responses)):
                if isinstance(response, Exception):
                    # Handle exceptions from batch processing
                    results.append(ValidationResponse(
                        success=False,
                        confidence_score=0.0,
                        raw_ai_response=f"ERROR: {str(response)}",
                        question_valid=False,
                        issues_found=[f"Batch processing error: {str(response)}"],
                        suggestions=["Retry individual validation"]
                    ))
                else:
                    results.append(self.response_parser.parse_response(response, request))
            
            return results
            
        except Exception as e:
            logger.error(f"Batch validation error: {e}")
            # Return error responses for all requests
            return [
                ValidationResponse(
                    success=False,
                    confidence_score=0.0,
                    raw_ai_response=f"BATCH_ERROR: {str(e)}",
                    question_valid=False,
                    issues_found=[f"Batch error: {str(e)}"],
                    suggestions=["Retry with individual requests"]
                ) for _ in requests
            ]


# Legacy compatibility layer - for backward compatibility
class AIValidationIntegrator:
    """Legacy integration helper for existing code."""
    
    def __init__(self, service: QuestionValidationService):
        self.service = service
    
    def validate_parsed_questions_structure(self, questions: List[Dict]) -> Dict[str, int]:
        """Legacy method for validating question structure."""
        valid_questions = 0
        
        for question in questions:
            if self._has_valid_structure(question):
                valid_questions += 1
        
        return {
            "total_questions": len(questions),
            "valid_structure": valid_questions,
            "invalid_structure": len(questions) - valid_questions
        }
    
    def filter_high_confidence_questions(self, 
                                       validation_results: List[ValidationResponse], 
                                       threshold: float = 0.8) -> List[ValidationResponse]:
        """Filter validation results by confidence threshold."""
        return [
            result for result in validation_results 
            if result.confidence_score >= threshold
        ]
    
    def _has_valid_structure(self, question: Dict) -> bool:
        """Check if question has valid structure."""
        required_fields = ["text", "alternatives"]
        
        for field in required_fields:
            if field not in question or not question[field]:
                return False
        
        # Check alternatives count
        alternatives = question.get("alternatives", [])
        return len(alternatives) == 5