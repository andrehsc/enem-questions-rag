#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for AI Missing Question Detector service.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from src.enem_ingestion.ai_missing_question_detector import (
    MissingQuestionDetector,
    DetectionRequest,
    DetectionResult,
    MissingQuestionCandidate,
    MissingQuestionHint,
    DetectionMethod,
    MissingQuestionIntegrator
)


class TestMissingQuestionDetector:
    """Test suite for MissingQuestionDetector."""
    
    def test_analyze_question_number_gaps_simple(self):
        """Test basic gap analysis."""
        detector = MissingQuestionDetector()
        
        found_numbers = [1, 2, 4, 6]
        expected_range = (1, 6)
        
        gaps = detector._analyze_question_number_gaps(found_numbers, expected_range)
        
        assert len(gaps) == 2
        assert (3, 3) in gaps
        assert (5, 5) in gaps
    
    def test_analyze_question_number_gaps_beginning_end(self):
        """Test gap analysis with missing at beginning and end."""
        detector = MissingQuestionDetector()
        
        found_numbers = [3, 4, 5]
        expected_range = (1, 7)
        
        gaps = detector._analyze_question_number_gaps(found_numbers, expected_range)
        
        assert len(gaps) == 2
        assert (1, 2) in gaps
        assert (6, 7) in gaps
    
    def test_analyze_question_number_gaps_no_gaps(self):
        """Test gap analysis with no gaps."""
        detector = MissingQuestionDetector()
        
        found_numbers = [1, 2, 3, 4, 5]
        expected_range = (1, 5)
        
        gaps = detector._analyze_question_number_gaps(found_numbers, expected_range)
        
        assert len(gaps) == 0
    
    def test_analyze_question_number_gaps_empty_found(self):
        """Test gap analysis with no found numbers."""
        detector = MissingQuestionDetector()
        
        found_numbers = []
        expected_range = (1, 5)
        
        gaps = detector._analyze_question_number_gaps(found_numbers, expected_range)
        
        assert len(gaps) == 1
        assert gaps[0] == (1, 5)

    def test_find_question_hints_question_pattern(self):
        """Test finding hints with question number patterns."""
        detector = MissingQuestionDetector()
        
        text_chunk = """
        Some text here.
        QUESTÃO 92
        Este é o enunciado da questão sobre...
        A) Primeira alternativa
        B) Segunda alternativa
        More text continues...
        """
        
        hints = detector._find_question_hints(text_chunk, "Page 1")
        
        # Should find question number hint
        question_hints = [h for h in hints if h.detection_method == DetectionMethod.QUESTION_NUMBER_ANALYSIS]
        assert len(question_hints) == 1
        assert question_hints[0].estimated_number == 92
        assert question_hints[0].confidence == 0.9
    
    def test_find_question_hints_alternative_orphans(self):
        """Test finding hints with orphaned alternatives."""
        detector = MissingQuestionDetector()
        
        text_chunk = """
        Algum contexto sobre história do Brasil...
        A) Primeira opção sobre independência
        B) Segunda opção sobre período colonial  
        C) Terceira opção sobre república
        D) Quarta opção sobre império
        E) Quinta opção sobre atualidade
        Continua o texto...
        """
        
        hints = detector._find_question_hints(text_chunk, "Page 2")
        
        # Should find alternative orphan hints
        orphan_hints = [h for h in hints if h.detection_method == DetectionMethod.ALTERNATIVE_ORPHAN_DETECTION]
        assert len(orphan_hints) == 1
        assert orphan_hints[0].confidence == 0.6
        assert "A, B, C, D, E" in orphan_hints[0].raw_patterns[0]
    
    def test_find_question_hints_loose_numbers(self):
        """Test finding hints with loose numbers."""
        detector = MissingQuestionDetector()
        
        text_chunk = """
        Texto com número 95 solto no meio.
        Também tem 200 que não é questão.
        E tem 3 que pode ser questão.
        """
        
        hints = detector._find_question_hints(text_chunk, "Page 3")
        
        # Should find loose number hints in valid range
        loose_hints = [h for h in hints if h.detection_method == DetectionMethod.TEXT_CHUNK_ANALYSIS]
        loose_numbers = [h.estimated_number for h in loose_hints]
        
        assert 95 in loose_numbers
        assert 3 in loose_numbers
        assert 200 not in loose_numbers  # Outside typical range

    def test_create_missing_detection_prompt(self):
        """Test prompt creation for missing detection."""
        detector = MissingQuestionDetector()
        
        text_chunk = "Sample chunk text"
        found_numbers = [1, 2, 4]
        expected_range = (1, 5)
        metadata = {"year": 2024, "caderno": "CD1"}
        
        prompt = detector._create_missing_detection_prompt(
            text_chunk, found_numbers, expected_range, metadata
        )
        
        assert "Sample chunk text" in prompt
        assert "1, 2, 4" in prompt
        assert "2024" in prompt
        assert "CD1" in prompt
        assert "questões 1 a 5" in prompt
        assert "JSON" in prompt

    def test_parse_detection_response_valid(self):
        """Test parsing valid AI response."""
        detector = MissingQuestionDetector()
        
        ai_response = """
        Análise do texto:
        {
          "missing_questions": [
            {
              "estimated_number": 93,
              "question_text": "Questão sobre história do Brasil",
              "alternatives": ["Alt A", "Alt B", "Alt C", "Alt D", "Alt E"],
              "confidence": 0.8,
              "location_info": "meio do chunk",
              "reconstruction_method": "pattern_detection"
            }
          ],
          "analysis_notes": "Encontrada uma questão"
        }
        Final notes.
        """
        
        candidates = detector._parse_detection_response(ai_response, "Page 1")
        
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.question_number == 93
        assert candidate.question_text == "Questão sobre história do Brasil"
        assert len(candidate.alternatives) == 5
        assert candidate.confidence_score == 0.8
        assert "Page 1" in candidate.location_info
    
    def test_parse_detection_response_invalid_alternatives(self):
        """Test parsing response with invalid number of alternatives."""
        detector = MissingQuestionDetector()
        
        ai_response = """
        {
          "missing_questions": [
            {
              "estimated_number": 94,
              "question_text": "Questão incompleta",
              "alternatives": ["Alt A", "Alt B", "Alt C"],
              "confidence": 0.9
            }
          ]
        }
        """
        
        candidates = detector._parse_detection_response(ai_response, "Page 2")
        
        # Should not include candidates with != 5 alternatives
        assert len(candidates) == 0
    
    def test_parse_detection_response_malformed_json(self):
        """Test parsing malformed JSON response."""
        detector = MissingQuestionDetector()
        
        ai_response = "This is not valid JSON at all"
        
        candidates = detector._parse_detection_response(ai_response, "Page 3")
        
        assert len(candidates) == 0

    def test_chunk_might_contain_gap_true(self):
        """Test chunk gap detection - positive case."""
        detector = MissingQuestionDetector()
        
        chunk = "Texto com número 95 que está no gap"
        gap = (93, 97)
        
        result = detector._chunk_might_contain_gap(chunk, gap)
        
        assert result is True
    
    def test_chunk_might_contain_gap_false(self):
        """Test chunk gap detection - negative case."""
        detector = MissingQuestionDetector()
        
        chunk = "Texto com número 80 que não está no gap"
        gap = (93, 97)
        
        result = detector._chunk_might_contain_gap(chunk, gap)
        
        assert result is False

    def test_deduplicate_candidates_by_number(self):
        """Test candidate deduplication by question number."""
        detector = MissingQuestionDetector()
        
        candidates = [
            MissingQuestionCandidate(
                question_number=95, question_text="Primeira versão",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.6,
                location_info="Loc1", reconstruction_method="method1", warnings=[]
            ),
            MissingQuestionCandidate(
                question_number=95, question_text="Segunda versão",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.8,
                location_info="Loc2", reconstruction_method="method2", warnings=[]
            )
        ]
        
        unique = detector._deduplicate_candidates(candidates)
        
        # Should keep only the higher confidence one
        assert len(unique) == 1
        assert unique[0].confidence_score == 0.8
        assert unique[0].question_text == "Segunda versão"
    
    def test_deduplicate_candidates_by_similarity(self):
        """Test candidate deduplication by text similarity."""
        detector = MissingQuestionDetector()
        
        candidates = [
            MissingQuestionCandidate(
                question_number=None, question_text="Este é um texto sobre história do Brasil e suas implicações políticas sociais",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.7,
                location_info="Loc1", reconstruction_method="method1", warnings=[]
            ),
            MissingQuestionCandidate(
                question_number=None, question_text="Este é um texto sobre história do Brasil e suas implicações políticas diferentes",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.5,
                location_info="Loc2", reconstruction_method="method2", warnings=[]
            )
        ]
        
        unique = detector._deduplicate_candidates(candidates)
        
        # Should keep only one (higher confidence) - texts are similar (>0.8 threshold)
        assert len(unique) == 1
        assert unique[0].confidence_score == 0.7

    def test_are_similar_texts(self):
        """Test text similarity detection."""
        detector = MissingQuestionDetector()
        
        text1 = "Este é um texto sobre história do Brasil"
        text2 = "Este é um texto sobre história do Brasil e política"
        text3 = "Completamente diferente sobre matemática e física"
        
        # Similar texts
        assert detector._are_similar_texts(text1, text2, threshold=0.6) is True
        
        # Different texts
        assert detector._are_similar_texts(text1, text3, threshold=0.6) is False
        
        # Empty texts
        assert detector._are_similar_texts("", text1) is False
        assert detector._are_similar_texts(text1, "") is False


class TestMissingQuestionIntegrator:
    """Test suite for MissingQuestionIntegrator."""
    
    def test_convert_candidates_to_questions_high_confidence(self):
        """Test converting high-confidence candidates."""
        detector = Mock()
        integrator = MissingQuestionIntegrator(detector)
        
        candidates = [
            MissingQuestionCandidate(
                question_number=95, question_text="Questão sobre história",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.8,
                location_info="Page 1", reconstruction_method="ai", warnings=[]
            ),
            MissingQuestionCandidate(
                question_number=96, question_text="Questão sobre geografia",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.5,
                location_info="Page 2", reconstruction_method="ai", warnings=[]
            )
        ]
        
        metadata = {"year": 2024}
        
        questions = integrator.convert_candidates_to_questions(candidates, metadata)
        
        # Should only include high-confidence candidate (>= 0.6)
        assert len(questions) == 1
        assert questions[0]["number"] == 95
        assert questions[0]["confidence_score"] == 0.8
        assert questions[0]["source"] == "ai_missing_detection"

    def test_convert_candidates_to_questions_no_number(self):
        """Test converting candidates without question number."""
        detector = Mock()
        integrator = MissingQuestionIntegrator(detector)
        
        candidates = [
            MissingQuestionCandidate(
                question_number=None, question_text="Questão sem número",
                alternatives=["A", "B", "C", "D", "E"], confidence_score=0.7,
                location_info="Page 1", reconstruction_method="ai", warnings=[]
            )
        ]
        
        metadata = {"year": 2024}
        
        questions = integrator.convert_candidates_to_questions(candidates, metadata)
        
        assert len(questions) == 1
        assert questions[0]["number"] == 0  # Default for missing number
        assert questions[0]["text"] == "Questão sem número"

    @pytest.mark.asyncio
    async def test_enhance_extraction_basic_flow(self):
        """Test basic enhancement flow."""
        # Mock detector
        detector = Mock()
        detector.detect_missing_questions = AsyncMock()
        
        # Mock detection result
        mock_result = DetectionResult(
            missing_candidates=[
                MissingQuestionCandidate(
                    question_number=95, question_text="Questão perdida",
                    alternatives=["A", "B", "C", "D", "E"], confidence_score=0.8,
                    location_info="Page 1", reconstruction_method="ai", warnings=[]
                )
            ],
            gaps_found=[(95, 95)],
            detection_summary={"total_candidates_found": 1},
            processed_chunks=5,
            raw_ai_responses=["response1"]
        )
        
        detector.detect_missing_questions.return_value = mock_result
        
        integrator = MissingQuestionIntegrator(detector)
        
        traditional_questions = [
            {"number": 93, "text": "Questão 93", "alternatives": ["A", "B", "C", "D", "E"]},
            {"number": 94, "text": "Questão 94", "alternatives": ["A", "B", "C", "D", "E"]}
        ]
        
        result = await integrator.enhance_extraction_with_missing_detection(
            "test.pdf", traditional_questions, 3
        )
        
        # Verify result structure
        assert result["traditional_count"] == 2
        assert result["missing_detected"] == 1
        assert result["total_count"] == 3
        assert result["expected_count"] == 3
        assert result["extraction_rate"] == 1.0  # 3/3 = 100%
        
        # Verify detector was called with correct parameters
        detector.detect_missing_questions.assert_called_once()
        call_args = detector.detect_missing_questions.call_args[0][0]
        assert call_args.pdf_path == "test.pdf"
        assert call_args.found_question_numbers == [93, 94]
        assert call_args.expected_range == (93, 95)  # min + count - 1

    @pytest.mark.asyncio
    async def test_enhance_extraction_no_traditional_questions(self):
        """Test enhancement with no traditional questions found."""
        detector = Mock()
        detector.detect_missing_questions = AsyncMock()
        
        # Mock detection result with 2 candidates
        mock_result = DetectionResult(
            missing_candidates=[
                MissingQuestionCandidate(
                    question_number=1, question_text="Primeira questão",
                    alternatives=["A", "B", "C", "D", "E"], confidence_score=0.7,
                    location_info="Page 1", reconstruction_method="ai", warnings=[]
                ),
                MissingQuestionCandidate(
                    question_number=2, question_text="Segunda questão", 
                    alternatives=["A", "B", "C", "D", "E"], confidence_score=0.8,
                    location_info="Page 1", reconstruction_method="ai", warnings=[]
                )
            ],
            gaps_found=[(1, 5)],
            detection_summary={"total_candidates_found": 2},
            processed_chunks=3,
            raw_ai_responses=["response1", "response2"]
        )
        
        detector.detect_missing_questions.return_value = mock_result
        
        integrator = MissingQuestionIntegrator(detector)
        
        traditional_questions = []
        
        result = await integrator.enhance_extraction_with_missing_detection(
            "test.pdf", traditional_questions, 5
        )
        
        # Verify result when no traditional questions exist
        assert result["traditional_count"] == 0
        assert result["missing_detected"] == 2
        assert result["total_count"] == 2
        assert result["expected_count"] == 5
        assert result["extraction_rate"] == 0.4  # 2/5 = 40%
        
        # Verify expected range defaults to (1, count)
        call_args = detector.detect_missing_questions.call_args[0][0]
        assert call_args.expected_range == (1, 5)