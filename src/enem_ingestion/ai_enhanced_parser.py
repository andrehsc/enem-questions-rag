#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI-Enhanced ENEM Parser - Hybrid Processing Pipeline
Integrates traditional parsing with AI validation, repair, and missing question detection.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple
import asyncio
import logging
import time
from pathlib import Path

from ..ai_services.validation.service import QuestionValidationService, ValidationRequest
from ..ai_services.repair.service import QuestionRepairService, RepairRequest, RepairType
from ..ai_services.detection.service import MissingQuestionDetector, DetectionRequest
from ..ai_services.common.base_types import EnemQuestionData
from ..ai_services.common.llama_client import LLamaAPIClient, DefaultServiceConfig

from .parser import EnemPDFParser
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from hybrid AI-enhanced extraction."""
    questions: List[Dict[str, Union[str, int, List[str]]]]
    traditional_count: int
    ai_validated_count: int
    ai_repaired_count: int
    ai_missing_detected: int
    processing_time_seconds: float
    confidence_scores: Dict[int, float]
    issues_found: List[str]
    success: bool = True


@dataclass
class ExtractionMetrics:
    """Metrics comparing traditional vs AI-enhanced extraction."""
    pdf_filename: str
    traditional_questions_found: int
    traditional_complete_questions: int
    ai_questions_found: int
    ai_complete_questions: int
    ai_repaired_questions: int
    ai_missing_detected: int
    improvement_percentage: float
    final_extraction_rate: float
    processing_time_seconds: float


class AIEnhancedEnemParser:
    """
    Hybrid AI-Enhanced ENEM Parser following SOLID principles.
    Orchestrates traditional parsing + AI validation + repair + missing detection.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the hybrid parser with dependency injection."""
        self.config = config or Config()
        
        # Traditional parser (existing system)
        self.traditional_parser = EnemPDFParser()
        
        # AI Services with dependency injection
        self.service_config = DefaultServiceConfig()
        self.llama_client = LLamaAPIClient(self.service_config)
        
        self.ai_validator = QuestionValidationService(self.llama_client, self.service_config)
        self.ai_repairer = QuestionRepairService(self.llama_client, self.service_config)
        self.missing_detector = MissingQuestionDetector(self.llama_client, self.service_config)
        
        # Processing configuration
        self.confidence_threshold = getattr(config, 'ai_confidence_threshold', 0.4)
        self.batch_size = getattr(config, 'ai_batch_size', 5)
        self.enable_missing_detection = getattr(config, 'enable_missing_detection', True)
        self.enable_repair = getattr(config, 'enable_repair', True)
        
    async def extract_questions_hybrid(self, pdf_path: Union[str, Path]) -> ExtractionResult:
        """
        Extract questions using hybrid AI-enhanced pipeline.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ExtractionResult with enhanced questions and metrics
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        logger.info(f"Starting hybrid extraction for {pdf_path.name}")
        
        try:
            # Phase 1: Traditional extraction (baseline)
            traditional_result = await self._extract_traditional(pdf_path)
            
            # Phase 2: AI validation of extracted questions
            validated_questions = await self._validate_questions(traditional_result['questions'])
            
            # Phase 3: AI repair of low-confidence questions
            repaired_questions, repair_count = await self._repair_questions(validated_questions)
            
            # Phase 4: Missing question detection
            missing_questions = []
            missing_count = 0
            if self.enable_missing_detection:
                missing_questions, missing_count = await self._detect_missing_questions(
                    pdf_path, repaired_questions
                )
            
            # Phase 5: Combine results
            final_questions = repaired_questions + missing_questions
            
            processing_time = time.time() - start_time
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(final_questions)
            
            result = ExtractionResult(
                questions=final_questions,
                traditional_count=len(traditional_result['questions']),
                ai_validated_count=len(validated_questions),
                ai_repaired_count=repair_count,
                ai_missing_detected=missing_count,
                processing_time_seconds=processing_time,
                confidence_scores=confidence_scores,
                issues_found=self._collect_issues(final_questions),
                success=True
            )
            
            logger.info(f"Hybrid extraction completed: {len(final_questions)} questions in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Hybrid extraction failed for {pdf_path.name}: {e}")
            # Fallback to traditional parser
            return await self._fallback_extraction(pdf_path, start_time, str(e))
    
    async def _extract_traditional(self, pdf_path: Path) -> Dict[str, Union[List, int]]:
        """Extract questions using traditional parser."""
        logger.debug("Phase 1: Traditional extraction")
        
        # Use existing parser
        questions = self.traditional_parser.parse_questions(str(pdf_path))
        
        # Convert to compatible format
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'number': getattr(q, 'number', 0),
                'text': getattr(q, 'text', ''),
                'alternatives': getattr(q, 'alternatives', []),
                'metadata': {
                    'extraction_method': 'traditional',
                    'confidence': 0.8  # Default confidence for traditional
                }
            })
        
        return {
            'questions': formatted_questions,
            'count': len(formatted_questions)
        }
    
    async def _validate_questions(self, questions: List[Dict]) -> List[Dict]:
        """Validate questions using AI service."""
        logger.debug(f"Phase 2: AI validation of {len(questions)} questions")
        
        validated_questions = []
        
        # Process in batches for efficiency
        for i in range(0, len(questions), self.batch_size):
            batch = questions[i:i + self.batch_size]
            batch_requests = []
            
            for question in batch:
                # Convert to EnemQuestionData
                question_data = EnemQuestionData(
                    number=question.get('number'),
                    text=question.get('text', ''),
                    alternatives=question.get('alternatives', [])
                )
                
                # Create validation request
                validation_request = ValidationRequest(
                    request_id=f"validate_{question.get('number', i)}",
                    question_data=question_data
                )
                batch_requests.append(validation_request)
            
            # Process batch
            try:
                batch_results = await self.ai_validator.process_batch(batch_requests)
                
                # Process results
                for question, result in zip(batch, batch_results):
                    if result.success and result.confidence_score > self.confidence_threshold:
                        question['metadata']['ai_validated'] = True
                        question['metadata']['confidence'] = result.confidence_score
                        validated_questions.append(question)
                    else:
                        # Mark for repair
                        question['metadata']['ai_validated'] = False
                        question['metadata']['confidence'] = result.confidence_score
                        question['metadata']['needs_repair'] = True
                        validated_questions.append(question)
                        
            except Exception as e:
                logger.warning(f"Validation batch failed: {e}")
                # Add questions with low confidence
                for question in batch:
                    question['metadata']['ai_validated'] = False
                    question['metadata']['confidence'] = 0.3
                    question['metadata']['validation_error'] = str(e)
                    validated_questions.extend(batch)
        
        logger.info(f"Validation completed: {len(validated_questions)} questions processed")
        return validated_questions
    
    async def _repair_questions(self, questions: List[Dict]) -> Tuple[List[Dict], int]:
        """Repair questions that need improvement."""
        if not self.enable_repair:
            return questions, 0
            
        logger.debug("Phase 3: AI repair of low-confidence questions")
        
        repaired_questions = []
        repair_count = 0
        
        for question in questions:
            needs_repair = question.get('metadata', {}).get('needs_repair', False)
            confidence = question.get('metadata', {}).get('confidence', 1.0)
            
            if needs_repair or confidence < self.confidence_threshold:
                try:
                    # Determine repair types needed
                    repair_types = self._determine_repair_types(question)
                    
                    if repair_types:
                        # Convert to EnemQuestionData
                        question_data = EnemQuestionData(
                            number=question.get('number'),
                            text=question.get('text', ''),
                            alternatives=question.get('alternatives', [])
                        )
                        
                        # Create repair request
                        repair_request = RepairRequest(
                            request_id=f"repair_{question.get('number', repair_count)}",
                            question_data=question_data,
                            repair_types=repair_types
                        )
                        
                        # Process repair
                        repair_result = await self.ai_repairer.process_request(repair_request)
                        
                        if repair_result.success and repair_result.repaired_question_data:
                            # Update question with repaired data
                            repaired_data = repair_result.repaired_question_data
                            question['text'] = repaired_data.text
                            question['alternatives'] = repaired_data.alternatives or []
                            question['metadata']['ai_repaired'] = True
                            question['metadata']['repairs_applied'] = repair_result.repairs_applied
                            question['metadata']['confidence'] = min(0.9, confidence + 0.3)
                            repair_count += 1
                        else:
                            question['metadata']['repair_failed'] = True
                            
                except Exception as e:
                    logger.warning(f"Repair failed for question {question.get('number')}: {e}")
                    question['metadata']['repair_error'] = str(e)
            
            repaired_questions.append(question)
        
        logger.info(f"Repair completed: {repair_count} questions repaired")
        return repaired_questions, repair_count
    
    def _determine_repair_types(self, question: Dict) -> List[RepairType]:
        """Determine what types of repair are needed for a question."""
        repair_types = []
        
        text = question.get('text', '')
        alternatives = question.get('alternatives', [])
        
        # Check for missing alternatives
        if len(alternatives) < 5:
            repair_types.append(RepairType.MISSING_ALTERNATIVES)
        
        # Check for OCR artifacts
        if any(char in text for char in ['□', '■', '�', 'ﬁ', 'ﬂ']):
            repair_types.append(RepairType.OCR_ARTIFACTS)
        
        # Check for incomplete text
        if len(text.strip()) < 50:
            repair_types.append(RepairType.INCOMPLETE_TEXT)
        
        # Check for formatting issues
        if not any(alt.strip().startswith(letter) for alt in alternatives for letter in ['A)', 'B)', 'C)', 'D)', 'E)']):
            repair_types.append(RepairType.FORMATTING_ISSUES)
        
        return repair_types
    
    async def _detect_missing_questions(self, pdf_path: Path, extracted_questions: List[Dict]) -> Tuple[List[Dict], int]:
        """Detect and reconstruct missing questions."""
        logger.debug("Phase 4: Missing question detection")
        
        try:
            # Prepare detection request
            found_numbers = [q.get('number', 0) for q in extracted_questions if q.get('number')]
            expected_range = self._estimate_question_range(found_numbers)
            
            detection_request = DetectionRequest(
                request_id=f"detect_{pdf_path.stem}",
                pdf_path=str(pdf_path),
                found_question_numbers=found_numbers,
                expected_range=expected_range
            )
            
            # Process detection
            detection_result = await self.missing_detector.process_request(detection_request)
            
            missing_questions = []
            if detection_result.success and detection_result.missing_candidates:
                for candidate in detection_result.missing_candidates:
                    if candidate.confidence_score > self.confidence_threshold:
                        question_dict = {
                            'number': candidate.question_data.number,
                            'text': candidate.question_data.text,
                            'alternatives': candidate.question_data.alternatives or [],
                            'metadata': {
                                'extraction_method': 'ai_detection',
                                'confidence': candidate.confidence_score,
                                'detection_method': candidate.detection_method,
                                'reconstruction_notes': candidate.reconstruction_notes
                            }
                        }
                        missing_questions.append(question_dict)
            
            logger.info(f"Missing detection completed: {len(missing_questions)} questions found")
            return missing_questions, len(missing_questions)
            
        except Exception as e:
            logger.warning(f"Missing question detection failed: {e}")
            return [], 0
    
    def _estimate_question_range(self, found_numbers: List[int]) -> Tuple[int, int]:
        """Estimate the expected range of question numbers."""
        if not found_numbers:
            return (1, 45)  # Default ENEM range
        
        min_found = min(found_numbers)
        max_found = max(found_numbers)
        
        # Estimate based on typical ENEM structure
        if max_found <= 45:
            return (1, 45)  # Day 1
        elif max_found <= 90:
            return (46, 90)  # Day 2
        else:
            return (min_found, max_found + 10)  # Custom range
    
    def _calculate_confidence_scores(self, questions: List[Dict]) -> Dict[int, float]:
        """Calculate confidence scores for all questions."""
        confidence_scores = {}
        
        for question in questions:
            number = question.get('number', 0)
            confidence = question.get('metadata', {}).get('confidence', 0.5)
            confidence_scores[number] = confidence
        
        return confidence_scores
    
    def _collect_issues(self, questions: List[Dict]) -> List[str]:
        """Collect issues found during processing."""
        issues = []
        
        for question in questions:
            metadata = question.get('metadata', {})
            
            if metadata.get('validation_error'):
                issues.append(f"Question {question.get('number')}: Validation error")
            
            if metadata.get('repair_failed'):
                issues.append(f"Question {question.get('number')}: Repair failed")
            
            if metadata.get('confidence', 1.0) < 0.5:
                issues.append(f"Question {question.get('number')}: Low confidence score")
        
        return issues
    
    async def _fallback_extraction(self, pdf_path: Path, start_time: float, error: str) -> ExtractionResult:
        """Fallback to traditional parsing when AI pipeline fails."""
        logger.warning(f"Falling back to traditional parsing: {error}")
        
        try:
            traditional_result = await self._extract_traditional(pdf_path)
            processing_time = time.time() - start_time
            
            return ExtractionResult(
                questions=traditional_result['questions'],
                traditional_count=traditional_result['count'],
                ai_validated_count=0,
                ai_repaired_count=0,
                ai_missing_detected=0,
                processing_time_seconds=processing_time,
                confidence_scores={},
                issues_found=[f"AI pipeline failed: {error}"],
                success=False
            )
            
        except Exception as fallback_error:
            logger.error(f"Fallback extraction also failed: {fallback_error}")
            return ExtractionResult(
                questions=[],
                traditional_count=0,
                ai_validated_count=0,
                ai_repaired_count=0,
                ai_missing_detected=0,
                processing_time_seconds=time.time() - start_time,
                confidence_scores={},
                issues_found=[f"All extraction methods failed: {error}, {fallback_error}"],
                success=False
            )
    
    def calculate_metrics(self, result: ExtractionResult, pdf_filename: str) -> ExtractionMetrics:
        """Calculate extraction metrics for comparison."""
        # Calculate improvement percentage
        if result.traditional_count > 0:
            total_found = len(result.questions)
            improvement = ((total_found - result.traditional_count) / result.traditional_count) * 100
        else:
            improvement = 0.0
        
        # Calculate extraction rate (assuming typical ENEM has 45 questions per day)
        expected_questions = 45
        extraction_rate = (len(result.questions) / expected_questions) * 100 if expected_questions > 0 else 0.0
        
        return ExtractionMetrics(
            pdf_filename=pdf_filename,
            traditional_questions_found=result.traditional_count,
            traditional_complete_questions=result.traditional_count,
            ai_questions_found=len(result.questions),
            ai_complete_questions=result.ai_validated_count,
            ai_repaired_questions=result.ai_repaired_count,
            ai_missing_detected=result.ai_missing_detected,
            improvement_percentage=improvement,
            final_extraction_rate=extraction_rate,
            processing_time_seconds=result.processing_time_seconds
        )


# Factory function for easy instantiation
def create_ai_enhanced_parser(config: Optional[Config] = None) -> AIEnhancedEnemParser:
    """Factory function to create AI-enhanced parser with default configuration."""
    return AIEnhancedEnemParser(config)
