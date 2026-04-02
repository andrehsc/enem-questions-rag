#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-powered question repair service for ENEM PDF extraction.
Repairs incomplete or malformed questions using LLama3.
"""

import logging
import json
import asyncio
import aiohttp
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class RepairType(Enum):
    """Types of repairs that can be performed."""
    MISSING_ALTERNATIVES = "missing_alternatives"
    INCOMPLETE_TEXT = "incomplete_text"
    OCR_ARTIFACTS = "ocr_artifacts"
    FORMATTING_ISSUES = "formatting_issues"
    MISSING_QUESTION_NUMBER = "missing_question_number"

@dataclass
class RepairRequest:
    """Request for question repair."""
    question_number: Optional[int]
    original_text: str
    available_alternatives: List[str]
    repair_types: List[RepairType]
    context_text: str = ""
    expected_alternatives_count: int = 5

@dataclass
class RepairResult:
    """Result of AI question repair."""
    success: bool
    repaired_question_text: str
    repaired_alternatives: List[str]
    confidence_score: float  # 0.0 - 1.0
    repairs_applied: List[str]
    warnings: List[str]
    raw_ai_response: str

class QuestionRepairService:
    """AI-powered repair service for malformed ENEM questions."""
    
    def __init__(self, llama_host: str = "http://localhost:11434", timeout: int = 45):
        """Initialize the repair service.
        
        Args:
            llama_host: LLama3 service endpoint
            timeout: Request timeout in seconds (longer for repair operations)
        """
        self.llama_host = llama_host
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_repair_attempts = 2
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _create_repair_prompt(self, request: RepairRequest) -> str:
        """Create repair prompt for LLama3."""
        repair_instructions = self._get_repair_instructions(request.repair_types)
        
        prompt = f"""
Você é um especialista em restauração de questões do ENEM. Sua tarefa é reparar uma questão que foi extraída de PDF com problemas.

QUESTÃO ORIGINAL (COM PROBLEMAS):
Número: {request.question_number or "Não identificado"}
Texto: {request.original_text}

ALTERNATIVAS DISPONÍVEIS ({len(request.available_alternatives)} de {request.expected_alternatives_count}):
{chr(10).join([f"{chr(65+i)}) {alt}" for i, alt in enumerate(request.available_alternatives)])}

PROBLEMAS IDENTIFICADOS:
{chr(10).join([f"- {repair_type.value}" for repair_type in request.repair_types])}

INSTRUÇÕES DE REPARO:
{repair_instructions}

CONTEXTO ADICIONAL:
{request.context_text or "Nenhum contexto adicional disponível"}

Regras importantes:
1. Mantenha o formato padrão ENEM
2. Preserve o conteúdo original sempre que possível
3. Complete alternativas faltantes de forma coerente
4. Corrija artifacts OCR mantendo o sentido
5. Garanta numeração correta da questão

Responda APENAS com um JSON válido:
{{
    "success": true/false,
    "repaired_question_text": "texto da questão reparado",
    "repaired_alternatives": ["A", "B", "C", "D", "E"],
    "confidence_score": 0.0-1.0,
    "repairs_applied": ["lista de reparos realizados"],
    "warnings": ["avisos sobre limitações do reparo"],
    "reasoning": "explicação do processo de reparo"
}}
"""
        return prompt.strip()
    
    def _get_repair_instructions(self, repair_types: List[RepairType]) -> str:
        """Get specific repair instructions based on repair types."""
        instructions = []
        
        for repair_type in repair_types:
            if repair_type == RepairType.MISSING_ALTERNATIVES:
                instructions.append("- Complete as alternativas faltantes (A-E) baseando-se no contexto da questão")
            elif repair_type == RepairType.INCOMPLETE_TEXT:
                instructions.append("- Reconstitua o texto completo da questão removendo quebras e fragments")
            elif repair_type == RepairType.OCR_ARTIFACTS:
                instructions.append("- Corrija caracteres mal interpretados pelo OCR (ex: 'rn' → 'm', '0' → 'o')")
            elif repair_type == RepairType.FORMATTING_ISSUES:
                instructions.append("- Corrija formatação, espaçamento e estrutura da questão")
            elif repair_type == RepairType.MISSING_QUESTION_NUMBER:
                instructions.append("- Identifique e adicione o número correto da questão")
        
        return "\n".join(instructions) if instructions else "- Reparo geral da questão"
    
    async def repair_question(self, request: RepairRequest) -> RepairResult:
        """Repair a single question using AI.
        
        Args:
            request: Repair request with question data
            
        Returns:
            RepairResult with repaired question
        """
        if not self.session:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        for attempt in range(self.max_repair_attempts):
            try:
                prompt = self._create_repair_prompt(request)
                
                # Call LLama3 API
                async with self.session.post(
                    f"{self.llama_host}/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # Slightly higher for creative repair
                            "top_p": 0.9,
                            "max_tokens": 2000  # More tokens for repair operations
                        }
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"LLama3 API error (attempt {attempt + 1}): {response.status}")
                        if attempt == self.max_repair_attempts - 1:
                            return self._create_fallback_result("API Error", request)
                        continue
                    
                    result = await response.json()
                    ai_response = result.get("response", "")
                    
                    repair_result = self._parse_repair_response(ai_response, request)
                    
                    # If successful, return result
                    if repair_result.success:
                        logger.info(f"Question repair successful on attempt {attempt + 1}")
                        return repair_result
                    
                    # If not successful but parseable, try again
                    logger.warning(f"Repair attempt {attempt + 1} failed, retrying...")
                    
            except asyncio.TimeoutError:
                logger.error(f"LLama3 request timeout (attempt {attempt + 1})")
                if attempt == self.max_repair_attempts - 1:
                    return self._create_fallback_result("Timeout", request)
            except Exception as e:
                logger.error(f"Repair error (attempt {attempt + 1}): {e}")
                if attempt == self.max_repair_attempts - 1:
                    return self._create_fallback_result(f"Error: {str(e)}", request)
        
        return self._create_fallback_result("Max attempts exceeded", request)
    
    def _parse_repair_response(self, ai_response: str, request: RepairRequest) -> RepairResult:
        """Parse AI JSON response into RepairResult."""
        try:
            # Extract JSON from response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON found in response")
            
            json_str = ai_response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return RepairResult(
                success=parsed.get("success", False),
                repaired_question_text=parsed.get("repaired_question_text", request.original_text),
                repaired_alternatives=parsed.get("repaired_alternatives", request.available_alternatives),
                confidence_score=float(parsed.get("confidence_score", 0.0)),
                repairs_applied=parsed.get("repairs_applied", []),
                warnings=parsed.get("warnings", []),
                raw_ai_response=ai_response
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse repair response: {e}")
            return self._create_fallback_result(f"Parse error: {str(e)}", request)
    
    def _create_fallback_result(self, error_msg: str, request: RepairRequest) -> RepairResult:
        """Create fallback result when repair fails."""
        return RepairResult(
            success=False,
            repaired_question_text=request.original_text,  # Return original text
            repaired_alternatives=request.available_alternatives,  # Return original alternatives
            confidence_score=0.0,
            repairs_applied=[],
            warnings=[f"Repair failed: {error_msg}"],
            raw_ai_response=f"ERROR: {error_msg}"
        )
    
    async def repair_batch(self, requests: List[RepairRequest]) -> List[RepairResult]:
        """Repair multiple questions in parallel.
        
        Args:
            requests: List of repair requests
            
        Returns:
            List of repair results
        """
        if not requests:
            return []
        
        # Process with smaller semaphore due to complexity of repair operations
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent repairs
        
        async def repair_with_semaphore(request):
            async with semaphore:
                return await self.repair_question(request)
        
        tasks = [repair_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        repair_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Repair failed for question {requests[i].question_number}: {result}")
                repair_results.append(self._create_fallback_result(str(result), requests[i]))
            else:
                repair_results.append(result)
        
        return repair_results

# Helper functions for repair analysis
class RepairAnalyzer:
    """Analyzes questions to determine what repairs are needed."""
    
    @staticmethod
    def analyze_question_problems(question_text: str, alternatives: List[str], 
                                question_number: Optional[int] = None) -> List[RepairType]:
        """Analyze a question to determine what repairs are needed.
        
        Args:
            question_text: The question text
            alternatives: List of alternatives
            question_number: Question number (if available)
            
        Returns:
            List of repair types needed
        """
        problems = []
        
        # Check for missing alternatives
        if len(alternatives) < 5:
            problems.append(RepairType.MISSING_ALTERNATIVES)
        
        # Check for incomplete text (very short or obviously cut off)
        if len(question_text.strip()) < 50 or question_text.endswith(('...', '-')):
            problems.append(RepairType.INCOMPLETE_TEXT)
        
        # Check for OCR artifacts (common patterns) - more specific detection
        ocr_indicators = [' rn ', ' ll ', '0o', ' vv ', ' ii ', '||', ' fi ']
        if any(indicator in f" {question_text.lower()} " for indicator in ocr_indicators):
            problems.append(RepairType.OCR_ARTIFACTS)
        
        # Check for formatting issues
        if '  ' in question_text or '\n\n' in question_text or question_text.count('\n') > 10:
            problems.append(RepairType.FORMATTING_ISSUES)
        
        # Check for missing question number
        if question_number is None and not any(char.isdigit() for char in question_text[:50]):
            problems.append(RepairType.MISSING_QUESTION_NUMBER)
        
        return problems
    
    @staticmethod
    def should_repair_question(question_text: str, alternatives: List[str],
                             confidence_threshold: float = 0.7) -> bool:
        """Determine if a question should be sent for repair.
        
        Args:
            question_text: The question text
            alternatives: List of alternatives
            confidence_threshold: Confidence threshold for repair decision
            
        Returns:
            True if question should be repaired
        """
        problems = RepairAnalyzer.analyze_question_problems(question_text, alternatives)
        
        # Always repair if missing alternatives
        if RepairType.MISSING_ALTERNATIVES in problems:
            return True
        
        # Repair if multiple problems detected
        if len(problems) >= 2:
            return True
        
        # Repair if text is very short (likely incomplete)
        if len(question_text.strip()) < 50:  # Lowered threshold
            return True
        
        return False