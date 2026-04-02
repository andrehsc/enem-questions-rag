#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-powered question validation service for ENEM PDF extraction.
Integrates with LLama3 to validate extracted questions.
"""

import logging
import json
import asyncio
import aiohttp
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of AI question validation."""
    question_valid: bool
    confidence_score: float  # 0.0 - 1.0
    issues_found: List[str]
    suggestions: List[str]
    alternatives_complete: bool
    text_quality_score: float
    raw_ai_response: str

@dataclass
class QuestionValidationRequest:
    """Request for question validation."""
    question_number: int
    question_text: str
    alternatives: List[str]
    context: str = ""
    
class QuestionValidationService:
    """AI-powered validation service for extracted ENEM questions."""
    
    def __init__(self, llama_host: str = "http://localhost:11434", timeout: int = 30):
        """Initialize the validation service.
        
        Args:
            llama_host: LLama3 service endpoint
            timeout: Request timeout in seconds
        """
        self.llama_host = llama_host
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _create_validation_prompt(self, request: QuestionValidationRequest) -> str:
        """Create validation prompt for LLama3."""
        prompt = f"""
Você é um especialista em análise de questões do ENEM. Analise a questão abaixo e forneça uma avaliação estruturada.

QUESTÃO {request.question_number}:
{request.question_text}

ALTERNATIVAS:
{chr(10).join([f"{chr(65+i)}) {alt}" for i, alt in enumerate(request.alternatives)])}

Avalie esta questão considerando:
1. Completude do enunciado
2. Clareza e correção do texto
3. Presença de todas as 5 alternativas (A-E)
4. Qualidade das alternativas
5. Formatação adequada para ENEM

Responda APENAS com um JSON válido no formato:
{{
    "question_valid": true/false,
    "confidence_score": 0.0-1.0,
    "issues_found": ["lista de problemas encontrados"],
    "suggestions": ["lista de sugestões de melhoria"],
    "alternatives_complete": true/false,
    "text_quality_score": 0.0-1.0,
    "reasoning": "explicação da avaliação"
}}
"""
        return prompt.strip()
    
    async def validate_question(self, request: QuestionValidationRequest) -> ValidationResult:
        """Validate a single question using AI.
        
        Args:
            request: Validation request with question data
            
        Returns:
            ValidationResult with AI analysis
        """
        if not self.session:
            raise RuntimeError("Service not initialized. Use async context manager.")
            
        try:
            prompt = self._create_validation_prompt(request)
            
            # Call LLama3 API
            async with self.session.post(
                f"{self.llama_host}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistency
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"LLama3 API error: {response.status}")
                    return self._create_fallback_result("API Error")
                
                result = await response.json()
                ai_response = result.get("response", "")
                
                return self._parse_ai_response(ai_response)
                
        except asyncio.TimeoutError:
            logger.error("LLama3 request timeout")
            return self._create_fallback_result("Timeout")
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return self._create_fallback_result(f"Error: {str(e)}")
    
    def _parse_ai_response(self, ai_response: str) -> ValidationResult:
        """Parse AI JSON response into ValidationResult."""
        try:
            # Extract JSON from response (may have extra text)
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON found in response")
            
            json_str = ai_response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return ValidationResult(
                question_valid=parsed.get("question_valid", False),
                confidence_score=float(parsed.get("confidence_score", 0.0)),
                issues_found=parsed.get("issues_found", []),
                suggestions=parsed.get("suggestions", []),
                alternatives_complete=parsed.get("alternatives_complete", False),
                text_quality_score=float(parsed.get("text_quality_score", 0.0)),
                raw_ai_response=ai_response
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._create_fallback_result(f"Parse error: {str(e)}")
    
    def _create_fallback_result(self, error_msg: str) -> ValidationResult:
        """Create fallback result when AI validation fails."""
        return ValidationResult(
            question_valid=False,
            confidence_score=0.0,
            issues_found=[f"AI validation failed: {error_msg}"],
            suggestions=["Manual review required"],
            alternatives_complete=False,
            text_quality_score=0.0,
            raw_ai_response=f"ERROR: {error_msg}"
        )
    
    async def validate_batch(self, requests: List[QuestionValidationRequest]) -> List[ValidationResult]:
        """Validate multiple questions in parallel.
        
        Args:
            requests: List of validation requests
            
        Returns:
            List of validation results
        """
        if not requests:
            return []
            
        # Process in parallel with semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def validate_with_semaphore(request):
            async with semaphore:
                return await self.validate_question(request)
        
        tasks = [validate_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        validated_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Validation failed for question {requests[i].question_number}: {result}")
                validated_results.append(self._create_fallback_result(str(result)))
            else:
                validated_results.append(result)
        
        return validated_results

# Integration helper for existing parser
class AIValidationIntegrator:
    """Integrates AI validation with existing ENEM parser."""
    
    def __init__(self, validation_service: QuestionValidationService):
        """Initialize integrator.
        
        Args:
            validation_service: Configured AI validation service
        """
        self.validation_service = validation_service
    
    async def validate_parsed_questions(self, questions: List) -> List[ValidationResult]:
        """Validate questions from existing parser.
        
        Args:
            questions: List of Question objects from parser
            
        Returns:
            List of validation results
        """
        requests = []
        
        for question in questions:
            request = QuestionValidationRequest(
                question_number=question.number,
                question_text=question.text,
                alternatives=question.alternatives,
                context=""  # Could add more context if available
            )
            requests.append(request)
        
        return await self.validation_service.validate_batch(requests)
    
    def filter_high_confidence_questions(self, 
                                       questions: List, 
                                       validation_results: List[ValidationResult],
                                       confidence_threshold: float = 0.8) -> List:
        """Filter questions that pass AI validation.
        
        Args:
            questions: Original questions from parser
            validation_results: AI validation results
            confidence_threshold: Minimum confidence score
            
        Returns:
            List of validated questions
        """
        validated_questions = []
        
        for question, result in zip(questions, validation_results):
            if (result.question_valid and 
                result.confidence_score >= confidence_threshold and
                result.alternatives_complete):
                validated_questions.append(question)
            else:
                logger.info(f"Question {question.number} failed validation: "
                          f"confidence={result.confidence_score:.2f}, "
                          f"issues={result.issues_found}")
        
        return validated_questions