#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-powered question repair service for ENEM PDF extraction.
Refactored following SOLID principles and Clean Code practices.
"""

import logging
import json
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..common.base_types import (
    AIRequest, AIResponse, AIServiceInterface, EnemQuestionData,
    ServiceConfigInterface, LLamaClientInterface
)
from ..common.llama_client import LLamaAPIClient, DefaultServiceConfig, BatchProcessor

logger = logging.getLogger(__name__)


class RepairType(Enum):
    """Types of repairs that can be performed."""
    MISSING_ALTERNATIVES = "missing_alternatives"
    INCOMPLETE_TEXT = "incomplete_text"
    OCR_ARTIFACTS = "ocr_artifacts"
    FORMATTING_ISSUES = "formatting_issues"
    MISSING_QUESTION_NUMBER = "missing_question_number"


@dataclass
class RepairRequest(AIRequest):
    """Request for question repair - extends base AIRequest."""
    question_data: Optional[EnemQuestionData] = None
    repair_types: Optional[List[RepairType]] = None
    context_text: str = ""
    expected_alternatives_count: int = 5
    
    def __post_init__(self):
        super().__post_init__()


@dataclass
class RepairResponse(AIResponse):
    """Response from repair service - extends base AIResponse."""
    repaired_question_data: Optional[EnemQuestionData] = None
    repairs_applied: Optional[List[str]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.repairs_applied is None:
            self.repairs_applied = []


class RepairAnalyzer:
    """Analyzes questions to determine what repairs are needed - SRP."""
    
    @staticmethod
    def analyze_question_problems(question_data: EnemQuestionData) -> List[RepairType]:
        """Analyze a question to determine what repairs are needed.
        
        Args:
            question_data: Question to analyze
            
        Returns:
            List of repair types needed
        """
        problems = []
        
        # Check for missing alternatives
        if not question_data.alternatives or len(question_data.alternatives) < 5:
            problems.append(RepairType.MISSING_ALTERNATIVES)
        
        # Check for incomplete text (very short or obviously cut off)
        text = question_data.text or ""
        if len(text.strip()) < 50 or text.endswith(('...', '-')):
            problems.append(RepairType.INCOMPLETE_TEXT)
        
        # Check for OCR artifacts (common patterns) - more specific detection
        ocr_indicators = [' rn ', ' ll ', '0o', ' vv ', ' ii ', '||', ' fi ']
        if any(indicator in f" {text.lower()} " for indicator in ocr_indicators):
            problems.append(RepairType.OCR_ARTIFACTS)
        
        # Check for formatting issues
        if '  ' in text or '\n\n' in text or text.count('\n') > 10:
            problems.append(RepairType.FORMATTING_ISSUES)
        
        # Check for missing question number
        if question_data.number is None and not any(char.isdigit() for char in text[:50]):
            problems.append(RepairType.MISSING_QUESTION_NUMBER)
        
        return problems
    
    @staticmethod
    def should_repair_question(question_data: EnemQuestionData,
                             confidence_threshold: float = 0.7) -> bool:
        """Determine if a question should be sent for repair.
        
        Args:
            question_data: Question to evaluate
            confidence_threshold: Confidence threshold for repair decision
            
        Returns:
            True if question should be repaired
        """
        problems = RepairAnalyzer.analyze_question_problems(question_data)
        
        # Always repair if missing alternatives
        if RepairType.MISSING_ALTERNATIVES in problems:
            return True
        
        # Repair if multiple problems detected
        if len(problems) >= 2:
            return True
        
        # Repair if text is very short (likely incomplete)
        text = question_data.text or ""
        if len(text.strip()) < 50:
            return True
        
        return False


class RepairPromptBuilder:
    """Builds repair prompts following Single Responsibility Principle."""
    
    @staticmethod
    def create_repair_prompt(request: RepairRequest) -> str:
        """Create repair prompt for LLama3.
        
        Args:
            request: Repair request with question data and repair types
            
        Returns:
            Formatted prompt string
        """
        question = request.question_data
        repair_instructions = RepairPromptBuilder._get_repair_instructions(request.repair_types)
        
        prompt = f"""
Esta questão ENEM foi extraída com problemas. Repare-a:

QUESTÃO PROBLEMÁTICA:
Número: {question.number or 'Não identificado'}
Texto: {question.text}
Alternativas disponíveis: {question.alternatives or []}

PROBLEMAS IDENTIFICADOS:
{repair_instructions}

CONTEXTO DO PDF (texto ao redor):
{request.context_text}

INSTRUÇÕES DE REPARO:
- Reconstitua a questão seguindo padrão ENEM
- Enunciado claro e completo em português
- Exatamente 5 alternativas (A, B, C, D, E)
- Formatação adequada
- Sem artifacts de OCR
- Mantenha o significado original sempre que possível

Responda APENAS com JSON válido:
{{
  "success": true,
  "question_number": 91,
  "question_text": "texto do enunciado corrigido...",
  "alternatives": ["texto alternativa A", "texto alternativa B", "texto alternativa C", "texto alternativa D", "texto alternativa E"],
  "confidence_score": 0.85,
  "repairs_applied": ["missing_alternatives", "ocr_correction"],
  "warnings": []
}}
"""
        return prompt
    
    @staticmethod
    def _get_repair_instructions(repair_types: List[RepairType]) -> str:
        """Get specific repair instructions based on problem types."""
        instructions_map = {
            RepairType.MISSING_ALTERNATIVES: "- Faltam alternativas, complete até ter 5 (A-E)",
            RepairType.INCOMPLETE_TEXT: "- Texto incompleto, reconstrua o enunciado",
            RepairType.OCR_ARTIFACTS: "- Corrija caracteres estranhos de OCR",
            RepairType.FORMATTING_ISSUES: "- Corrija problemas de formatação",
            RepairType.MISSING_QUESTION_NUMBER: "- Identifique/adicione número da questão"
        }
        
        instructions = []
        for repair_type in repair_types:
            if repair_type in instructions_map:
                instructions.append(instructions_map[repair_type])
        
        return "\n".join(instructions) if instructions else "- Reparo geral necessário"


class RepairResponseParser:
    """Parses AI repair responses following Single Responsibility Principle."""
    
    @staticmethod
    def parse_response(ai_response: str, request: RepairRequest) -> RepairResponse:
        """Parse AI response into RepairResponse.
        
        Args:
            ai_response: Raw AI response text
            request: Original repair request
            
        Returns:
            Parsed RepairResponse
        """
        try:
            # Extract JSON from response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return RepairResponseParser._create_fallback_response(
                    "No valid JSON found in AI response", request, ai_response
                )
            
            json_str = ai_response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Create repaired question data
            repaired_question = EnemQuestionData(
                number=parsed.get("question_number", request.question_data.number),
                text=parsed.get("question_text", request.question_data.text),
                alternatives=parsed.get("alternatives", request.question_data.alternatives),
                metadata=request.question_data.metadata.copy()
            )
            
            return RepairResponse(
                success=parsed.get("success", False),
                confidence_score=float(parsed.get("confidence_score", 0.0)),
                raw_ai_response=ai_response,
                repaired_question_data=repaired_question,
                repairs_applied=parsed.get("repairs_applied", []),
                warnings=parsed.get("warnings", [])
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse repair response: {e}")
            return RepairResponseParser._create_fallback_response(
                f"Parse error: {str(e)}", request, ai_response
            )
    
    @staticmethod
    def _create_fallback_response(error_msg: str, 
                                request: RepairRequest, 
                                raw_response: str) -> RepairResponse:
        """Create fallback response when parsing fails."""
        return RepairResponse(
            success=False,
            confidence_score=0.0,
            raw_ai_response=raw_response,
            repaired_question_data=request.question_data,  # Return original
            repairs_applied=[],
            warnings=[f"Repair failed: {error_msg}"]
        )


class QuestionRepairService(AIServiceInterface):
    """AI-powered repair service following Interface Segregation Principle."""
    
    def __init__(self, 
                 config: Optional[ServiceConfigInterface] = None,
                 llama_client: Optional[LLamaClientInterface] = None):
        """Initialize repair service with dependency injection.
        
        Args:
            config: Service configuration (uses default if None)
            llama_client: LLama client instance (creates default if None)
        """
        self.config = config or DefaultServiceConfig()
        self._llama_client = llama_client
        self.analyzer = RepairAnalyzer()
        self.prompt_builder = RepairPromptBuilder()
        self.response_parser = RepairResponseParser()
        self.batch_processor = BatchProcessor(max_concurrent=2)  # Lower concurrency for repairs
    
    async def process_request(self, request: RepairRequest) -> RepairResponse:
        """Process single repair request.
        
        Args:
            request: Repair request
            
        Returns:
            Repair response
        """
        try:
            # Validate input data first
            issues = request.question_data.validate()
            if "Question text is too short or empty" in issues:
                # Skip validation for repair requests as they might have incomplete data
                pass
            
            # Create prompt
            prompt = self.prompt_builder.create_repair_prompt(request)
            
            # Call AI service
            async with LLamaAPIClient(self.config) as client:
                ai_response = await client.call_api(prompt)
            
            # Parse response
            return self.response_parser.parse_response(ai_response, request)
            
        except Exception as e:
            logger.error(f"Repair service error: {e}")
            return RepairResponse(
                success=False,
                confidence_score=0.0,
                raw_ai_response=f"ERROR: {str(e)}",
                repaired_question_data=request.question_data,
                repairs_applied=[],
                warnings=[f"Service error: {str(e)}"]
            )
    
    async def process_batch(self, requests: List[RepairRequest]) -> List[RepairResponse]:
        """Process multiple repair requests in batch.
        
        Args:
            requests: List of repair requests
            
        Returns:
            List of repair responses in same order
        """
        if not requests:
            return []
        
        try:
            # Build prompts for all requests
            prompts = [self.prompt_builder.create_repair_prompt(req) for req in requests]
            
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
                    results.append(RepairResponse(
                        success=False,
                        confidence_score=0.0,
                        raw_ai_response=f"ERROR: {str(response)}",
                        repaired_question_data=request.question_data,
                        repairs_applied=[],
                        warnings=[f"Batch processing error: {str(response)}"]
                    ))
                else:
                    results.append(self.response_parser.parse_response(response, request))
            
            return results
            
        except Exception as e:
            logger.error(f"Batch repair error: {e}")
            # Return error responses for all requests
            return [
                RepairResponse(
                    success=False,
                    confidence_score=0.0,
                    raw_ai_response=f"BATCH_ERROR: {str(e)}",
                    repaired_question_data=req.question_data,
                    repairs_applied=[],
                    warnings=[f"Batch error: {str(e)}"]
                ) for req in requests
            ]