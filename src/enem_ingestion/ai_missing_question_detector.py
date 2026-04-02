#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-powered missing question detection service for ENEM PDF extraction.
Detects questions that were missed by the traditional parser using LLama3.
"""

import logging
import json
import asyncio
import aiohttp
import re
from typing import List, Dict, Optional, Union, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import pdfplumber

logger = logging.getLogger(__name__)


class DetectionMethod(Enum):
    """Methods for detecting missing questions."""
    QUESTION_NUMBER_ANALYSIS = "question_number_analysis"
    TEXT_CHUNK_ANALYSIS = "text_chunk_analysis"
    AI_PATTERN_DETECTION = "ai_pattern_detection"
    ALTERNATIVE_ORPHAN_DETECTION = "alternative_orphan_detection"


@dataclass
class MissingQuestionHint:
    """Hint about a potentially missing question."""
    estimated_number: Optional[int]
    text_chunk: str
    chunk_location: str  # Page/position info
    detection_method: DetectionMethod
    confidence: float  # 0.0 - 1.0
    raw_patterns: List[str]  # Patterns that triggered detection


@dataclass
class MissingQuestionCandidate:
    """Candidate for a missing question found by AI."""
    question_number: Optional[int]
    question_text: str
    alternatives: List[str]
    confidence_score: float  # 0.0 - 1.0
    location_info: str
    reconstruction_method: str
    warnings: List[str]


@dataclass
class DetectionRequest:
    """Request for missing question detection."""
    pdf_path: str
    found_question_numbers: List[int]
    expected_range: Tuple[int, int]  # (start, end)
    pdf_text_chunks: List[str]
    metadata: Dict[str, Union[str, int]]


@dataclass
class DetectionResult:
    """Result of missing question detection."""
    missing_candidates: List[MissingQuestionCandidate]
    gaps_found: List[Tuple[int, int]]  # (start, end) of number gaps
    detection_summary: Dict[str, Union[int, float]]
    processed_chunks: int
    raw_ai_responses: List[str]


class MissingQuestionDetector:
    """AI-powered detector for missing questions in ENEM PDFs."""
    
    def __init__(self, llama_host: str = "http://localhost:11434", timeout: int = 45):
        """Initialize the missing question detector.
        
        Args:
            llama_host: LLama3 API endpoint
            timeout: Timeout for AI requests in seconds
        """
        self.llama_host = llama_host
        self.timeout = timeout
        self.session = None
        
        # Question number pattern for ENEM
        self.question_number_pattern = re.compile(r'(?:QUESTÃO|Questão|questão)\s*(\d+)', re.IGNORECASE)
        self.loose_number_pattern = re.compile(r'\b(\d{1,3})\b')
        self.alternative_pattern = re.compile(r'\b([A-E])\s*\)', re.MULTILINE)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _analyze_question_number_gaps(self, found_numbers: List[int], 
                                    expected_range: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Analyze gaps in question numbers to find missing ones.
        
        Args:
            found_numbers: List of question numbers already found
            expected_range: Expected range (start, end) for this PDF
            
        Returns:
            List of gaps as (start, end) tuples
        """
        if not found_numbers:
            return [expected_range]
            
        sorted_numbers = sorted(found_numbers)
        gaps = []
        
        # Check gap at beginning
        if sorted_numbers[0] > expected_range[0]:
            gaps.append((expected_range[0], sorted_numbers[0] - 1))
        
        # Check gaps in middle
        for i in range(len(sorted_numbers) - 1):
            current = sorted_numbers[i]
            next_num = sorted_numbers[i + 1]
            
            if next_num - current > 1:
                gaps.append((current + 1, next_num - 1))
        
        # Check gap at end
        if sorted_numbers[-1] < expected_range[1]:
            gaps.append((sorted_numbers[-1] + 1, expected_range[1]))
            
        return gaps

    def _extract_text_chunks_from_pdf(self, pdf_path: str, chunk_size: int = 2000) -> List[Tuple[str, str]]:
        """Extract text chunks from PDF with location info.
        
        Args:
            pdf_path: Path to PDF file
            chunk_size: Size of each text chunk
            
        Returns:
            List of (text_chunk, location_info) tuples
        """
        chunks = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    
                    # Split page into chunks
                    text_len = len(page_text)
                    for start in range(0, text_len, chunk_size):
                        chunk_text = page_text[start:start + chunk_size]
                        location = f"Page {page_num}, chars {start}-{start + len(chunk_text)}"
                        chunks.append((chunk_text, location))
                        
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            
        return chunks

    def _find_question_hints(self, text_chunk: str, location: str) -> List[MissingQuestionHint]:
        """Find hints about missing questions in a text chunk.
        
        Args:
            text_chunk: Text to analyze
            location: Location info for this chunk
            
        Returns:
            List of question hints found
        """
        hints = []
        
        # Method 1: Look for question number patterns
        question_matches = self.question_number_pattern.findall(text_chunk)
        for match in question_matches:
            try:
                question_num = int(match)
                hints.append(MissingQuestionHint(
                    estimated_number=question_num,
                    text_chunk=text_chunk,
                    chunk_location=location,
                    detection_method=DetectionMethod.QUESTION_NUMBER_ANALYSIS,
                    confidence=0.9,
                    raw_patterns=[f"QUESTÃO {question_num}"]
                ))
            except ValueError:
                continue
        
        # Method 2: Look for orphaned alternatives (A), B), etc. without clear question
        alternative_matches = self.alternative_pattern.findall(text_chunk)
        if len(alternative_matches) >= 3:  # At least 3 alternatives suggest a question
            hints.append(MissingQuestionHint(
                estimated_number=None,
                text_chunk=text_chunk,
                chunk_location=location,
                detection_method=DetectionMethod.ALTERNATIVE_ORPHAN_DETECTION,
                confidence=0.6,
                raw_patterns=[f"Alternatives: {', '.join(alternative_matches)}"]
            ))
        
        # Method 3: Look for loose numbers that might be question numbers
        loose_numbers = self.loose_number_pattern.findall(text_chunk)
        for num_str in loose_numbers:
            try:
                num = int(num_str)
                # Only consider numbers in typical ENEM question range (1-180)
                if 1 <= num <= 180:
                    hints.append(MissingQuestionHint(
                        estimated_number=num,
                        text_chunk=text_chunk,
                        chunk_location=location,
                        detection_method=DetectionMethod.TEXT_CHUNK_ANALYSIS,
                        confidence=0.3,
                        raw_patterns=[f"Loose number: {num}"]
                    ))
            except ValueError:
                continue
                
        return hints

    def _create_missing_detection_prompt(self, text_chunk: str, found_numbers: List[int], 
                                       expected_range: Tuple[int, int], 
                                       metadata: Dict[str, Union[str, int]]) -> str:
        """Create prompt for AI to detect missing questions.
        
        Args:
            text_chunk: Text chunk to analyze
            found_numbers: Question numbers already found
            expected_range: Expected question number range
            metadata: PDF metadata (year, caderno, etc.)
            
        Returns:
            Formatted prompt string
        """
        found_numbers_str = ", ".join(map(str, sorted(found_numbers)))
        
        prompt = f"""
Analise este trecho de texto de PDF ENEM para encontrar questões perdidas pelo parser automático:

TEXTO PARA ANÁLISE:
{text_chunk}

CONTEXTO:
- Ano: {metadata.get('year', 'N/A')}
- Caderno: {metadata.get('caderno', 'N/A')}
- Questões já encontradas: {found_numbers_str}
- Range esperado: questões {expected_range[0]} a {expected_range[1]}

INSTRUÇÕES:
1. Procure por padrões típicos de questão ENEM:
   - Números de questão (ex: "QUESTÃO 91", "91.", "91)")  
   - Enunciados seguidos de alternativas A), B), C), D), E)
   - Textos que parecem enunciados sem numeração clara
   - Alternativas órfãs sem questão associada

2. Para cada questão perdida encontrada, tente reconstituir:
   - Número da questão (se possível determinar)
   - Texto do enunciado
   - Lista de alternativas

3. Considere que questões ENEM:
   - Têm enunciado em português (pode ter textos em outras línguas como contexto)
   - Sempre têm 5 alternativas (A, B, C, D, E)
   - Podem ter textos de apoio (poemas, gráficos, etc.)

Responda APENAS com JSON válido:
{{
  "missing_questions": [
    {{
      "estimated_number": 91,
      "question_text": "texto do enunciado encontrado",
      "alternatives": ["texto alternativa A", "texto alternativa B", "texto alternativa C", "texto alternativa D", "texto alternativa E"],
      "confidence": 0.8,
      "location_info": "posição aproximada no chunk",
      "reconstruction_method": "método usado para reconstituir"
    }}
  ],
  "analysis_notes": "observações sobre o que foi encontrado"
}}
"""
        return prompt

    async def _call_llama_api(self, prompt: str) -> str:
        """Call LLama3 API for missing question detection.
        
        Args:
            prompt: Prompt for question detection
            
        Returns:
            AI response text
        """
        payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 2000
            }
        }
        
        try:
            async with self.session.post(f"{self.llama_host}/api/generate", 
                                       json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "")
                else:
                    logger.error(f"LLama API error: {response.status}")
                    return f"API Error: {response.status}"
                    
        except asyncio.TimeoutError:
            logger.error("LLama API timeout")
            return "Timeout Error"
        except Exception as e:
            logger.error(f"LLama API call failed: {e}")
            return f"Error: {str(e)}"

    def _parse_detection_response(self, ai_response: str, chunk_location: str) -> List[MissingQuestionCandidate]:
        """Parse AI response into missing question candidates.
        
        Args:
            ai_response: Response from AI
            chunk_location: Location info for the analyzed chunk
            
        Returns:
            List of missing question candidates
        """
        candidates = []
        
        try:
            # Extract JSON from response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return candidates  # No valid JSON found
            
            json_str = ai_response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            missing_questions = parsed.get("missing_questions", [])
            
            for mq in missing_questions:
                alternatives = mq.get("alternatives", [])
                if len(alternatives) == 5:  # Must have exactly 5 alternatives
                    candidates.append(MissingQuestionCandidate(
                        question_number=mq.get("estimated_number"),
                        question_text=mq.get("question_text", ""),
                        alternatives=alternatives,
                        confidence_score=float(mq.get("confidence", 0.0)),
                        location_info=f"{chunk_location} - {mq.get('location_info', '')}",
                        reconstruction_method=mq.get("reconstruction_method", "ai_detection"),
                        warnings=[]
                    ))
                    
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse detection response: {e}")
            
        return candidates

    async def detect_missing_questions(self, request: DetectionRequest) -> DetectionResult:
        """Detect missing questions in PDF using AI analysis.
        
        Args:
            request: Detection request with PDF info
            
        Returns:
            Detection result with found candidates
        """
        logger.info(f"Starting missing question detection for {request.pdf_path}")
        
        # Analyze question number gaps
        gaps = self._analyze_question_number_gaps(request.found_question_numbers, request.expected_range)
        logger.info(f"Found {len(gaps)} potential gaps: {gaps}")
        
        # Extract text chunks from PDF if not provided
        if not request.pdf_text_chunks:
            text_chunks_with_location = self._extract_text_chunks_from_pdf(request.pdf_path)
            text_chunks = [chunk for chunk, _ in text_chunks_with_location]
        else:
            text_chunks = request.pdf_text_chunks
            text_chunks_with_location = [(chunk, f"Chunk {i}") for i, chunk in enumerate(text_chunks)]
        
        # Find hints in each chunk
        all_hints = []
        for chunk, location in text_chunks_with_location:
            hints = self._find_question_hints(chunk, location)
            all_hints.extend(hints)
        
        logger.info(f"Found {len(all_hints)} question hints using pattern analysis")
        
        # Use AI to analyze chunks with high potential
        missing_candidates = []
        raw_responses = []
        processed_chunks = 0
        
        # Process chunks with semaphore to limit concurrent AI calls
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent AI calls
        
        async def process_chunk(chunk: str, location: str) -> List[MissingQuestionCandidate]:
            async with semaphore:
                prompt = self._create_missing_detection_prompt(
                    chunk, request.found_question_numbers, request.expected_range, request.metadata
                )
                
                response = await self._call_llama_api(prompt)
                raw_responses.append(response)
                
                candidates = self._parse_detection_response(response, location)
                logger.debug(f"Chunk at {location}: found {len(candidates)} candidates")
                
                return candidates
        
        # Process promising chunks (those with hints or in gap areas)
        processing_tasks = []
        
        for chunk, location in text_chunks_with_location:
            # Check if this chunk has hints or might contain missing questions
            chunk_hints = [h for h in all_hints if h.chunk_location == location]
            
            if chunk_hints or any(self._chunk_might_contain_gap(chunk, gap) for gap in gaps):
                processing_tasks.append(process_chunk(chunk, location))
                processed_chunks += 1
        
        # Execute AI analysis in parallel
        if processing_tasks:
            chunk_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            for result in chunk_results:
                if isinstance(result, Exception):
                    logger.error(f"Chunk processing failed: {result}")
                else:
                    missing_candidates.extend(result)
        
        # Remove duplicates and sort by confidence
        unique_candidates = self._deduplicate_candidates(missing_candidates)
        unique_candidates.sort(key=lambda c: c.confidence_score, reverse=True)
        
        # Generate summary
        summary = {
            "total_candidates_found": len(unique_candidates),
            "high_confidence_candidates": len([c for c in unique_candidates if c.confidence_score > 0.7]),
            "gaps_analyzed": len(gaps),
            "chunks_processed": processed_chunks,
            "average_confidence": sum(c.confidence_score for c in unique_candidates) / len(unique_candidates) if unique_candidates else 0.0
        }
        
        logger.info(f"Detection complete: {summary}")
        
        return DetectionResult(
            missing_candidates=unique_candidates,
            gaps_found=gaps,
            detection_summary=summary,
            processed_chunks=processed_chunks,
            raw_ai_responses=raw_responses
        )

    def _chunk_might_contain_gap(self, chunk: str, gap: Tuple[int, int]) -> bool:
        """Check if a text chunk might contain questions from a number gap.
        
        Args:
            chunk: Text chunk to check
            gap: Gap range (start, end)
            
        Returns:
            True if chunk might contain gap questions
        """
        # Look for any numbers in the gap range
        numbers_in_chunk = self.loose_number_pattern.findall(chunk)
        
        for num_str in numbers_in_chunk:
            try:
                num = int(num_str)
                if gap[0] <= num <= gap[1]:
                    return True
            except ValueError:
                continue
                
        return False

    def _deduplicate_candidates(self, candidates: List[MissingQuestionCandidate]) -> List[MissingQuestionCandidate]:
        """Remove duplicate candidates based on question number and text similarity.
        
        Args:
            candidates: List of candidates to deduplicate
            
        Returns:
            Deduplicated list of candidates
        """
        if not candidates:
            return candidates
            
        unique_candidates = []
        
        for candidate in candidates:
            # Check for duplicate question numbers - keep higher confidence
            if candidate.question_number:
                existing_with_same_number = None
                for i, existing in enumerate(unique_candidates):
                    if existing.question_number == candidate.question_number:
                        existing_with_same_number = (i, existing)
                        break
                
                if existing_with_same_number:
                    idx, existing = existing_with_same_number
                    # Keep the one with higher confidence
                    if candidate.confidence_score > existing.confidence_score:
                        unique_candidates[idx] = candidate
                    # Skip current candidate if existing has higher confidence
                    continue
                    
            # Check for very similar text (simple similarity check)
            is_duplicate = False
            for i, existing in enumerate(unique_candidates):
                if self._are_similar_texts(candidate.question_text, existing.question_text):
                    # Keep the one with higher confidence
                    if candidate.confidence_score > existing.confidence_score:
                        unique_candidates[i] = candidate
                    # Mark as duplicate either way
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_candidates.append(candidate)
        
        return unique_candidates

    def _are_similar_texts(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are similar enough to be considered duplicates.
        
        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            True if texts are similar
        """
        if not text1 or not text2:
            return False
            
        # Simple similarity check based on common words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0.0
        
        return similarity >= threshold

    async def detect_missing_batch(self, requests: List[DetectionRequest]) -> List[DetectionResult]:
        """Detect missing questions for multiple PDFs.
        
        Args:
            requests: List of detection requests
            
        Returns:
            List of detection results
        """
        semaphore = asyncio.Semaphore(2)  # Max 2 PDFs processed concurrently
        
        async def process_request(request: DetectionRequest) -> DetectionResult:
            async with semaphore:
                return await self.detect_missing_questions(request)
        
        tasks = [process_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Request {i} failed: {result}")
                # Create empty result for failed requests
                final_results.append(DetectionResult(
                    missing_candidates=[],
                    gaps_found=[],
                    detection_summary={"error": str(result)},
                    processed_chunks=0,
                    raw_ai_responses=[]
                ))
            else:
                final_results.append(result)
                
        return final_results


# Integration helper for existing parser
class MissingQuestionIntegrator:
    """Integrates missing question detection with existing ENEM parser."""
    
    def __init__(self, detector: MissingQuestionDetector):
        """Initialize integrator.
        
        Args:
            detector: Missing question detector instance
        """
        self.detector = detector
    
    def convert_candidates_to_questions(self, candidates: List[MissingQuestionCandidate], 
                                      metadata: Dict[str, Union[str, int]]) -> List[Dict[str, Union[str, int, List[str]]]]:
        """Convert missing question candidates to parser-compatible format.
        
        Args:
            candidates: List of missing question candidates
            metadata: PDF metadata
            
        Returns:
            List of questions in parser format
        """
        questions = []
        
        for candidate in candidates:
            # Only include high-confidence candidates
            if candidate.confidence_score >= 0.6:
                question_dict = {
                    "number": candidate.question_number or 0,
                    "text": candidate.question_text,
                    "alternatives": candidate.alternatives,
                    "confidence_score": candidate.confidence_score,
                    "source": "ai_missing_detection",
                    "location_info": candidate.location_info,
                    "reconstruction_method": candidate.reconstruction_method,
                    "warnings": candidate.warnings
                }
                questions.append(question_dict)
        
        return questions
    
    async def enhance_extraction_with_missing_detection(self, pdf_path: str, 
                                                       traditional_questions: List[Dict], 
                                                       expected_question_count: int) -> Dict[str, Union[List, int, float]]:
        """Enhance traditional extraction with missing question detection.
        
        Args:
            pdf_path: Path to PDF file
            traditional_questions: Questions found by traditional parser
            expected_question_count: Expected number of questions
            
        Returns:
            Enhanced extraction result
        """
        found_numbers = [q.get("number", 0) for q in traditional_questions if q.get("number")]
        
        # Estimate expected range based on question count and existing numbers
        if found_numbers:
            min_found = min(found_numbers)
            max_found = max(found_numbers)
            expected_range = (min_found, min_found + expected_question_count - 1)
        else:
            expected_range = (1, expected_question_count)
        
        # Create detection request
        detection_request = DetectionRequest(
            pdf_path=pdf_path,
            found_question_numbers=found_numbers,
            expected_range=expected_range,
            pdf_text_chunks=[],  # Will be extracted from PDF
            metadata={
                "year": 2024,  # Could be extracted from filename
                "caderno": "CD1"  # Could be extracted from filename
            }
        )
        
        # Run detection
        detection_result = await self.detector.detect_missing_questions(detection_request)
        
        # Convert candidates to questions
        missing_questions = self.convert_candidates_to_questions(
            detection_result.missing_candidates,
            detection_request.metadata
        )
        
        # Combine results
        all_questions = traditional_questions + missing_questions
        
        return {
            "questions": all_questions,
            "traditional_count": len(traditional_questions),
            "missing_detected": len(missing_questions),
            "total_count": len(all_questions),
            "expected_count": expected_question_count,
            "extraction_rate": len(all_questions) / expected_question_count if expected_question_count > 0 else 0.0,
            "detection_summary": detection_result.detection_summary,
            "gaps_found": detection_result.gaps_found
        }