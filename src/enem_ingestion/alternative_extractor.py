#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Alternative Extractor for ENEM Questions
================================================
Implements multiple strategies for robust alternative extraction using Strategy Pattern.

This addresses the ~95% failure rate in alternative parsing by providing
multiple algorithms with confidence scoring and fallback mechanisms.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionStrategy(Enum):
    """Strategy types for alternative extraction."""
    STANDARD_PATTERN = "standard_pattern"
    MULTILINE_PATTERN = "multiline_pattern"
    COLUMN_AWARE = "column_aware"
    CONTEXTUAL = "contextual"
    MATHEMATICAL = "mathematical"


@dataclass
class ExtractedAlternatives:
    """Result from alternative extraction."""
    alternatives: List[str]
    confidence: float
    strategy_used: ExtractionStrategy
    issues_found: List[str]
    raw_matches: Dict[str, str]  # Letter -> text mapping


class AlternativeExtractionStrategy(ABC):
    """Abstract base class for alternative extraction strategies."""
    
    @abstractmethod
    def extract(self, text: str) -> ExtractedAlternatives:
        """Extract alternatives from text."""
        pass
    
    @abstractmethod
    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        """Calculate confidence score for extracted alternatives."""
        pass


class StandardPatternStrategy(AlternativeExtractionStrategy):
    """Standard pattern extraction using regex for typical ENEM layouts."""
    
    def __init__(self):
        self.patterns = [
            # Pattern 1: Letter at start of line with whitespace
            r'(?:^|\n)\s*([A-E])\s+([^\n]{3,200}?)(?=\n\s*[A-E]\s|\n\n|QUESTÃO|LC\s*-|$)',
            # Pattern 2: Letter with parentheses  
            r'([A-E])\)\s*([^\n]{3,200}?)(?=\n\s*[A-E]\)|\n\n|QUESTÃO|LC\s*-|$)',
            # Pattern 3: Letter with space, limited capture
            r'(?:^|\n)\s*([A-E])\s+([^A-E\n]{3,100}?)(?=\s*\n|$)'
        ]
    
    def extract(self, text: str) -> ExtractedAlternatives:
        """Extract using standard regex patterns."""
        alternatives_dict = {}
        best_pattern = None
        
        # Try each pattern and use the one that finds most alternatives
        for i, pattern in enumerate(self.patterns):
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            if len(matches) > len(alternatives_dict):
                alternatives_dict.clear()
                for letter, alt_text in matches:
                    if letter not in alternatives_dict:
                        clean_text = self._clean_alternative_text(alt_text)
                        # More strict validation - avoid random letters in text
                        if (len(clean_text.strip()) >= 3 and 
                            not self._is_likely_false_positive(letter, clean_text)):
                            alternatives_dict[letter] = f"{letter}) {clean_text}"
                best_pattern = i
        
        # Calculate confidence
        confidence = self.get_confidence(alternatives_dict, text)
        
        # Convert to ordered list
        final_alternatives = []
        for letter in 'ABCDE':
            if letter in alternatives_dict:
                final_alternatives.append(alternatives_dict[letter])
        
        issues = self._identify_issues(alternatives_dict, text)
        
        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.STANDARD_PATTERN,
            issues_found=issues,
            raw_matches=alternatives_dict
        )
    
    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        """Calculate confidence based on completeness and quality."""
        if not alternatives:
            return 0.0
        
        # Base score from completeness
        completeness = len(alternatives) / 5.0
        
        # Quality indicators
        quality_score = 0.0
        for alt_text in alternatives.values():
            text_length = len(alt_text.split())
            if 3 <= text_length <= 50:  # Reasonable length
                quality_score += 0.2
        
        quality_score = min(1.0, quality_score)
        
        # Final confidence (weighted average)
        confidence = (completeness * 0.7) + (quality_score * 0.3)
        
        return confidence
    
    def _clean_alternative_text(self, text: str) -> str:
        """Clean alternative text from artifacts."""
        # Remove common artifacts
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[.]{2,}$', '', text)  # Remove trailing dots
        text = re.sub(r'^[.\s]+', '', text)  # Remove leading dots/spaces
        text = re.sub(r'(ENEM2024|4202MENE|\d{2}::\d{2}::\d{2})', '', text)  # Remove PDF artifacts
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace again after removals
        return text.strip()
    
    def _identify_issues(self, alternatives: Dict[str, str], text: str) -> List[str]:
        """Identify potential issues with extraction."""
        issues = []
        
        if len(alternatives) < 5:
            issues.append(f"Only found {len(alternatives)} of 5 alternatives")
        
        # Check for very short alternatives (might be incomplete)
        short_alts = [k for k, v in alternatives.items() if len(v.split()) < 3]
        if short_alts:
            issues.append(f"Short alternatives detected: {short_alts}")
        
        return issues
    
    def _is_likely_false_positive(self, letter: str, text: str) -> bool:
        """Check if this is likely a false positive match."""
        # If text is very long, it probably captured too much
        if len(text) > 200:
            return True
        
        # If text contains multiple sentences without clear alternative structure
        sentences = text.count('.')
        if sentences > 2:
            return True
            
        # If text looks like descriptive paragraph rather than alternative
        descriptive_words = ['este', 'esta', 'não há', 'pode ser', 'sobre o tema']
        if any(word in text.lower() for word in descriptive_words):
            return True
            
        return False


class MultilinePatternStrategy(AlternativeExtractionStrategy):
    """Strategy for alternatives that span multiple lines."""
    
    def extract(self, text: str) -> ExtractedAlternatives:
        """Extract alternatives that may span multiple lines."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        alternatives_dict = {}
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for line starting with letter
            match = re.match(r'^([A-E])\s*[).-]?\s*(.+)', line)
            if match:
                letter = match.group(1)
                alt_text = match.group(2)
                
                # Look for continuation lines
                i += 1
                continuation_count = 0
                while i < len(lines) and continuation_count < 3:  # Limit continuations
                    next_line = lines[i].strip()
                    
                    # Stop if we hit another alternative or section marker
                    if re.match(r'^[A-E]\s*[).-]', next_line):
                        break
                    if re.match(r'^(QUESTÃO|LC\s*-|Página|\*\d+)', next_line):
                        break
                    
                    # Add continuation if it's substantial text and looks like continuation
                    if (len(next_line) > 3 and 
                        not re.match(r'^\d+$', next_line) and
                        not next_line.isupper() and  # Avoid headers
                        len(next_line.split()) > 1):  # More than single word
                        alt_text += ' ' + next_line
                        continuation_count += 1
                    i += 1
                
                # Clean and store
                clean_text = self._clean_alternative_text(alt_text)
                if len(clean_text.strip()) >= 3:
                    alternatives_dict[letter] = f"{letter}) {clean_text}"
            else:
                i += 1
        
        # Calculate confidence
        confidence = self.get_confidence(alternatives_dict, text)
        
        # Convert to ordered list
        final_alternatives = []
        for letter in 'ABCDE':
            if letter in alternatives_dict:
                final_alternatives.append(alternatives_dict[letter])
        
        issues = self._identify_issues(alternatives_dict)
        
        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.MULTILINE_PATTERN,
            issues_found=issues,
            raw_matches=alternatives_dict
        )
    
    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        """Calculate confidence for multiline extraction."""
        if not alternatives:
            return 0.0
        
        completeness = len(alternatives) / 5.0
        
        # Bonus for finding all alternatives
        if len(alternatives) == 5:
            completeness += 0.1
        
        return min(1.0, completeness)
    
    def _clean_alternative_text(self, text: str) -> str:
        """Clean multiline alternative text."""
        # Normalize whitespace and remove artifacts
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[.]{2,}$', '', text)
        text = re.sub(r'(ENEM2024|4202MENE|\d{2}::\d{2}::\d{2})', '', text)  # Remove PDF artifacts
        text = re.sub(r'\s+', ' ', text)  # Normalize again
        return text.strip()
    
    def _identify_issues(self, alternatives: Dict[str, str]) -> List[str]:
        """Identify issues with multiline extraction."""
        issues = []
        if len(alternatives) < 5:
            issues.append(f"Multiline strategy found {len(alternatives)}/5 alternatives")
        return issues


class MathematicalStrategy(AlternativeExtractionStrategy):
    """Strategy optimized for mathematical questions with short answers."""
    
    def extract(self, text: str) -> ExtractedAlternatives:
        """Extract alternatives that might be mathematical expressions."""
        alternatives_dict = {}
        
        # Pattern for mathematical alternatives (more permissive)
        patterns = [
            # Simple pattern: letter + space + content until next line or letter
            r'(?:^|\n)\s*([A-E])\s+([^\n\r]{1,50}?)(?=\s*\n|$)',
            # Very short answers (for math) - letter followed by short content
            r'([A-E])\s+(\S+(?:\s+\S+){0,2})(?=\s*[A-E]\s|\n|$)'
        ]
        
        for pattern in patterns:
            if len(alternatives_dict) >= 5:
                break
                
            matches = re.findall(pattern, text, re.DOTALL)
            for letter, alt_text in matches:
                if letter not in alternatives_dict:
                    clean_text = self._clean_mathematical_text(alt_text)
                    # More permissive for math - accept even single characters
                    if len(clean_text) >= 1 and not re.match(r'^(ENEM|QUESTÃO)', clean_text):
                        alternatives_dict[letter] = f"{letter}) {clean_text}"
        
        confidence = self.get_confidence(alternatives_dict, text)
        
        final_alternatives = []
        for letter in 'ABCDE':
            if letter in alternatives_dict:
                final_alternatives.append(alternatives_dict[letter])
        
        issues = []
        if len(alternatives_dict) < 5:
            issues.append(f"Mathematical strategy found {len(alternatives_dict)}/5 alternatives")
        
        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.MATHEMATICAL,
            issues_found=issues,
            raw_matches=alternatives_dict
        )
    
    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        """Calculate confidence for mathematical extraction."""
        if not alternatives:
            return 0.0
        
        # Mathematical questions often have shorter alternatives
        completeness = len(alternatives) / 5.0
        
        # Check if alternatives look mathematical
        math_indicators = 0
        for alt_text in alternatives.values():
            if re.search(r'[\d.,π√∞±≤≥²³°%]', alt_text):
                math_indicators += 1
        
        if math_indicators > 0:
            math_bonus = math_indicators / len(alternatives) * 0.2
            completeness += math_bonus
        
        return min(1.0, completeness)
    
    def _clean_mathematical_text(self, text: str) -> str:
        """Clean mathematical alternative text."""
        # Remove PDF artifacts
        text = re.sub(r'(ENEM2024|4202MENE|\d{2}::\d{2}::\d{2})', '', text)
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text.strip()


class EnhancedAlternativeExtractor:
    """
    Enhanced alternative extractor using multiple strategies.
    
    Addresses the 95.9% failure rate in partial alternative extraction
    by implementing multiple extraction algorithms with confidence scoring.
    """
    
    def __init__(self):
        self.strategies = [
            StandardPatternStrategy(),
            MultilinePatternStrategy(),
            MathematicalStrategy()
        ]
        
    def extract_alternatives(self, question_text: str) -> ExtractedAlternatives:
        """
        Extract alternatives using the best available strategy.
        
        Args:
            question_text: Raw question text from PDF
            
        Returns:
            ExtractedAlternatives with best result found
        """
        best_result = ExtractedAlternatives(
            alternatives=[],
            confidence=0.0,
            strategy_used=ExtractionStrategy.STANDARD_PATTERN,
            issues_found=["No alternatives found"],
            raw_matches={}
        )
        
        logger.debug(f"Attempting extraction with {len(self.strategies)} strategies")
        
        # Try each strategy
        for strategy in self.strategies:
            try:
                result = strategy.extract(question_text)
                
                logger.debug(f"Strategy {result.strategy_used.value}: "
                           f"{len(result.alternatives)} alts, confidence {result.confidence:.2f}")
                
                # Use this result if it's better
                if result.confidence > best_result.confidence:
                    best_result = result
                
                # Early exit if we found perfect result
                if len(result.alternatives) == 5 and result.confidence > 0.9:
                    logger.debug(f"Perfect result found with {result.strategy_used.value}")
                    break
                    
            except Exception as e:
                logger.warning(f"Strategy {strategy.__class__.__name__} failed: {e}")
                continue
        
        logger.debug(f"Best result: {len(best_result.alternatives)} alternatives, "
                    f"confidence {best_result.confidence:.2f} "
                    f"using {best_result.strategy_used.value}")
        
        return best_result
    
    def extract_alternatives_legacy_compatible(self, question_text: str) -> List[str]:
        """
        Legacy-compatible method that returns list of alternatives.
        
        This maintains backward compatibility with existing parser code.
        """
        result = self.extract_alternatives(question_text)
        return result.alternatives


# Factory function for easy integration
def create_enhanced_extractor() -> EnhancedAlternativeExtractor:
    """Create and return enhanced alternative extractor."""
    return EnhancedAlternativeExtractor()
