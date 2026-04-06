#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Alternative Extractor for ENEM Questions (Epic 8, Story 8.2).

Implements multiple strategies for robust alternative extraction using Strategy Pattern.
Includes cascade detection/fix, strategy merging, and doubled-letter support.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionStrategy(Enum):
    """Strategy types for alternative extraction."""
    STANDARD_PATTERN = "standard_pattern"
    MULTILINE_PATTERN = "multiline_pattern"
    MATHEMATICAL = "mathematical"
    DOUBLED_LETTER = "doubled_letter"


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
        pass

    @abstractmethod
    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        pass


# ------------------------------------------------------------------ #
# Strategies
# ------------------------------------------------------------------ #

class StandardPatternStrategy(AlternativeExtractionStrategy):
    """Standard pattern extraction using regex for typical ENEM layouts."""

    def __init__(self):
        self.patterns = [
            # Letter at start of line with whitespace
            r'(?:^|\n)\s*([A-E])\s+([^\n]{3,500}?)(?=\n\s*[A-E]\s|\n\n|QUESTÃO|LC\s*-|$)',
            # Letter with parentheses
            r'([A-E])\)\s*([^\n]{3,500}?)(?=\n\s*[A-E]\)|\n\n|QUESTÃO|LC\s*-|$)',
            # Letter with space, limited capture
            r'(?:^|\n)\s*([A-E])\s+([^A-E\n]{3,500}?)(?=\s*\n|$)',
            # Markdown list `- A texto` format
            r'(?:^|\n)\s*-\s+([A-E])\s+([^\n]{3,500}?)(?=\n\s*-\s+[A-E]\s|\n\n|QUESTÃO|$)',
            # Single-line `- A texto - B texto` format
            r'-\s+([A-E])\s+(.+?)(?=\s+-\s+[A-E]\s|$)',
        ]

    def extract(self, text: str) -> ExtractedAlternatives:
        alternatives_dict: Dict[str, str] = {}
        best_pattern = None

        for i, pattern in enumerate(self.patterns):
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            if len(matches) > len(alternatives_dict):
                alternatives_dict.clear()
                for letter, alt_text in matches:
                    if letter not in alternatives_dict:
                        clean_text = _clean_alternative_text(alt_text)
                        if (len(clean_text.strip()) >= 3 and
                                not self._is_likely_false_positive(clean_text)):
                            alternatives_dict[letter] = clean_text
                best_pattern = i

        confidence = self.get_confidence(alternatives_dict, text)
        final_alternatives = _dict_to_list(alternatives_dict)
        issues = []
        if len(alternatives_dict) < 5:
            issues.append(f"Only found {len(alternatives_dict)} of 5 alternatives")

        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.STANDARD_PATTERN,
            issues_found=issues,
            raw_matches=alternatives_dict,
        )

    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        if not alternatives:
            return 0.0
        completeness = len(alternatives) / 5.0
        quality_score = 0.0
        for alt_text in alternatives.values():
            wc = len(alt_text.split())
            if 3 <= wc <= 50:
                quality_score += 0.2
        quality_score = min(1.0, quality_score)
        return (completeness * 0.7) + (quality_score * 0.3)

    @staticmethod
    def _is_likely_false_positive(text: str) -> bool:
        """Structural heuristic — no longer rejects common PT-BR words."""
        if len(text) > 500:
            return True
        if text.count('.') > 5:
            return True
        # Reject if it looks like question bleed
        if re.search(r'QUEST[ÃA]O', text, re.IGNORECASE):
            return True
        return False


class MultilinePatternStrategy(AlternativeExtractionStrategy):
    """Strategy for alternatives that span multiple lines."""

    def extract(self, text: str) -> ExtractedAlternatives:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        alternatives_dict: Dict[str, str] = {}

        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.match(r'^(?:-\s+)?([A-E])\s*[).\-]?\s*(.+)', line)
            if match and match.group(2).strip():
                letter = match.group(1)
                alt_text = match.group(2)

                i += 1
                continuation_count = 0
                while i < len(lines) and continuation_count < 3:
                    next_line = lines[i].strip()
                    if re.match(r'^(?:-\s+)?[A-E]\s*[).\-]', next_line):
                        break
                    if re.match(r'^(QUESTÃO|LC\s*-|Página|\*\d+)', next_line):
                        break
                    if (len(next_line) > 3 and
                            not re.match(r'^\d+$', next_line) and
                            not next_line.isupper() and
                            len(next_line.split()) > 1):
                        alt_text += ' ' + next_line
                        continuation_count += 1
                    i += 1

                clean_text = _clean_alternative_text(alt_text)
                if len(clean_text.strip()) >= 3:
                    alternatives_dict[letter] = clean_text
            else:
                i += 1

        confidence = self.get_confidence(alternatives_dict, text)
        final_alternatives = _dict_to_list(alternatives_dict)
        issues = []
        if len(alternatives_dict) < 5:
            issues.append(f"Multiline strategy found {len(alternatives_dict)}/5 alternatives")

        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.MULTILINE_PATTERN,
            issues_found=issues,
            raw_matches=alternatives_dict,
        )

    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        if not alternatives:
            return 0.0
        completeness = len(alternatives) / 5.0
        if len(alternatives) == 5:
            completeness += 0.1
        return min(1.0, completeness)


class MathematicalStrategy(AlternativeExtractionStrategy):
    """Strategy optimized for mathematical questions with short answers."""

    def extract(self, text: str) -> ExtractedAlternatives:
        alternatives_dict: Dict[str, str] = {}

        patterns = [
            r'(?:^|\n)\s*([A-E])\s+([^\n\r]{1,50}?)(?=\s*\n|$)',
            r'([A-E])\s+(\S+(?:\s+\S+){0,2})(?=\s*[A-E]\s|\n|$)',
        ]

        for pattern in patterns:
            if len(alternatives_dict) >= 5:
                break
            matches = re.findall(pattern, text, re.DOTALL)
            for letter, alt_text in matches:
                if letter not in alternatives_dict:
                    clean_text = _clean_alternative_text(alt_text)
                    if len(clean_text) >= 1 and not re.match(r'^(ENEM|QUESTÃO)', clean_text):
                        alternatives_dict[letter] = clean_text

        confidence = self.get_confidence(alternatives_dict, text)
        final_alternatives = _dict_to_list(alternatives_dict)
        issues = []
        if len(alternatives_dict) < 5:
            issues.append(f"Mathematical strategy found {len(alternatives_dict)}/5 alternatives")

        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.MATHEMATICAL,
            issues_found=issues,
            raw_matches=alternatives_dict,
        )

    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        if not alternatives:
            return 0.0
        completeness = len(alternatives) / 5.0
        math_indicators = 0
        for alt_text in alternatives.values():
            if re.search(r'[\d.,π√∞±≤≥²³°%]', alt_text):
                math_indicators += 1
        if math_indicators > 0:
            math_bonus = math_indicators / len(alternatives) * 0.2
            completeness += math_bonus
        return min(1.0, completeness)


class DoubledLetterStrategy(AlternativeExtractionStrategy):
    """Strategy for 2022-2023 format with doubled letters (AA, BB, CC, DD, EE)."""

    def extract(self, text: str) -> ExtractedAlternatives:
        alternatives_dict: Dict[str, str] = {}

        patterns = [
            # Compact: "AA resposta1"
            (re.compile(
                r'(?:^|\n)\s*(AA|BB|CC|DD|EE)\s*[).\-]?\s*(.+?)(?=\n\s*(?:AA|BB|CC|DD|EE)\s|\n\n|$)',
                re.DOTALL | re.MULTILINE,
            ), True),
            # Spaced: "A A resposta1"
            (re.compile(
                r'(?:^|\n)\s*([A-E])\s+\1\s*[).\-]?\s*(.+?)(?=\n\s*[A-E]\s+[A-E]\s|\n\n|$)',
                re.DOTALL | re.MULTILINE,
            ), False),
        ]

        for pat, is_doubled in patterns:
            matches = pat.findall(text)
            if not matches:
                continue
            for raw_letter, alt_text in matches:
                letter = raw_letter[0] if is_doubled else raw_letter
                if letter not in alternatives_dict:
                    clean_text = _clean_alternative_text(alt_text)
                    if len(clean_text.strip()) >= 1:
                        alternatives_dict[letter] = clean_text
            if len(alternatives_dict) >= 3:
                break

        confidence = self.get_confidence(alternatives_dict, text)
        final_alternatives = _dict_to_list(alternatives_dict)
        issues = []
        if len(alternatives_dict) < 5:
            issues.append(f"DoubledLetter strategy found {len(alternatives_dict)}/5 alternatives")

        return ExtractedAlternatives(
            alternatives=final_alternatives,
            confidence=confidence,
            strategy_used=ExtractionStrategy.DOUBLED_LETTER,
            issues_found=issues,
            raw_matches=alternatives_dict,
        )

    def get_confidence(self, alternatives: Dict[str, str], text: str) -> float:
        if not alternatives:
            return 0.0
        completeness = len(alternatives) / 5.0
        if len(alternatives) == 5:
            completeness += 0.1
        return min(1.0, completeness)


# ------------------------------------------------------------------ #
# Orchestrator
# ------------------------------------------------------------------ #

class EnhancedAlternativeExtractor:
    """Enhanced alternative extractor with cascade fix and strategy merging."""

    def __init__(self):
        self.strategies: List[AlternativeExtractionStrategy] = [
            StandardPatternStrategy(),
            MultilinePatternStrategy(),
            MathematicalStrategy(),
            DoubledLetterStrategy(),
        ]

    def extract_alternatives(self, question_text: str) -> ExtractedAlternatives:
        """Extract alternatives using the best available strategy.

        Pipeline:
            1. Try each strategy, keep best result
            2. If no single strategy found 5, try strategy merge
            3. If cascade detected, attempt differencing fix
        """
        best_result = ExtractedAlternatives(
            alternatives=[],
            confidence=0.0,
            strategy_used=ExtractionStrategy.STANDARD_PATTERN,
            issues_found=["No alternatives found"],
            raw_matches={},
        )
        all_results: List[ExtractedAlternatives] = []

        for strategy in self.strategies:
            try:
                result = strategy.extract(question_text)
                all_results.append(result)

                if result.confidence > best_result.confidence:
                    best_result = result

                if len(result.alternatives) == 5 and result.confidence > 0.9:
                    break
            except Exception as e:
                logger.warning("Strategy %s failed: %s", strategy.__class__.__name__, e)

        # If no single strategy found 5, try merging
        if len(best_result.raw_matches) < 5 and len(all_results) > 1:
            merged = self._merge_strategies(all_results)
            if len(merged) > len(best_result.raw_matches):
                confidence = min(
                    (r.confidence for r in all_results if r.raw_matches),
                    default=0.0,
                )
                best_result = ExtractedAlternatives(
                    alternatives=_dict_to_list(merged),
                    confidence=confidence,
                    strategy_used=best_result.strategy_used,
                    issues_found=["merged_strategies"],
                    raw_matches=merged,
                )

        # Cascade detection and fix
        if len(best_result.raw_matches) >= 3 and _detect_cascade(best_result.raw_matches):
            fixed = _fix_cascade(best_result.raw_matches)
            if fixed:
                best_result = ExtractedAlternatives(
                    alternatives=_dict_to_list(fixed),
                    confidence=best_result.confidence * 0.9,
                    strategy_used=best_result.strategy_used,
                    issues_found=["cascade_fixed"],
                    raw_matches=fixed,
                )

        # Split merged alternatives (Story 9.2)
        if best_result.raw_matches:
            split = _split_merged_alternatives(best_result.raw_matches)
            if split != best_result.raw_matches:
                best_result = ExtractedAlternatives(
                    alternatives=_dict_to_list(split),
                    confidence=best_result.confidence,
                    strategy_used=best_result.strategy_used,
                    issues_found=best_result.issues_found + ["merged_alternatives_split"],
                    raw_matches=split,
                )

        return best_result

    def extract_alternatives_legacy_compatible(self, question_text: str) -> List[str]:
        """Legacy-compatible method that returns list of alternatives."""
        result = self.extract_alternatives(question_text)
        return result.alternatives

    @staticmethod
    def _merge_strategies(results: List[ExtractedAlternatives]) -> Dict[str, str]:
        """Merge results from multiple strategies picking best per letter."""
        merged: Dict[str, str] = {}
        for letter in 'ABCDE':
            candidates = []
            for r in results:
                if letter in r.raw_matches:
                    candidates.append((r.raw_matches[letter], r.confidence))
            if candidates:
                merged[letter] = max(candidates, key=lambda x: x[1])[0]
        return merged


# ------------------------------------------------------------------ #
# Split merged alternatives (Story 9.2)
# ------------------------------------------------------------------ #

def _split_merged_alternatives(alternatives: Dict[str, str]) -> Dict[str, str]:
    """Split alternatives merged on the same line (e.g., "D texto1. E texto2.").

    Works in multiple passes to handle 3+ merged alts (C→D→E).
    Only splits when the next expected letter is missing from the dict.
    """
    result = dict(alternatives)
    letters = 'ABCDE'

    # Multiple passes to handle chained merges (e.g., C contains D and E)
    for _pass in range(3):
        changed = False
        for idx in range(3, -1, -1):  # D, C, B, A
            curr = letters[idx]
            next_l = letters[idx + 1] if idx + 1 < 5 else None
            if curr not in result or next_l is None:
                continue
            if next_l in result:
                continue  # next letter already exists

            text = result[curr]
            split_re = re.compile(
                rf'(.+?)\s+{next_l}\s+(\S.{{1,}})$'
            )
            m = split_re.match(text)
            if m:
                candidate_curr = m.group(1).strip()
                candidate_next = m.group(2).strip()
                first_word_after = candidate_next.split()[0] if candidate_next else ""
                if (len(first_word_after) > 8 and first_word_after[0].islower()
                        and not re.search(r'\d', first_word_after)):
                    continue
                if candidate_curr and candidate_next:
                    result[curr] = candidate_curr
                    result[next_l] = candidate_next
                    changed = True
        if not changed:
            break

    return result


# ------------------------------------------------------------------ #
# Cascade detection / fix
# ------------------------------------------------------------------ #

def _detect_cascade(alternatives: Dict[str, str]) -> bool:
    """Detect cascading alternatives where A ⊃ B ⊃ C."""
    texts = [alternatives.get(l, '') for l in 'ABCDE' if l in alternatives]
    if len(texts) < 3:
        return False

    containment_count = 0
    for i in range(len(texts) - 1):
        if texts[i + 1] and texts[i] and texts[i + 1] in texts[i]:
            containment_count += 1

    return containment_count >= 2


def _fix_cascade(alternatives: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Fix cascading alternatives using reverse differencing.

    Start from E (usually cleanest), subtract to get unique portions.
    """
    letters = [l for l in 'ABCDE' if l in alternatives]
    if len(letters) < 3:
        return None

    texts = {l: alternatives[l] for l in letters}

    # Work backwards: E is usually correct
    fixed: Dict[str, str] = {}
    fixed[letters[-1]] = texts[letters[-1]].strip()

    for i in range(len(letters) - 2, -1, -1):
        curr_letter = letters[i]
        next_letter = letters[i + 1]
        curr_text = texts[curr_letter]
        next_text = texts[next_letter]

        if next_text in curr_text:
            # Extract the unique portion before the next alternative's text
            idx = curr_text.index(next_text)
            unique = curr_text[:idx].strip()
            if unique:
                fixed[curr_letter] = unique
            else:
                # fall back to full text
                fixed[curr_letter] = curr_text.strip()
        else:
            fixed[curr_letter] = curr_text.strip()

    return fixed


# ------------------------------------------------------------------ #
# Shared helpers
# ------------------------------------------------------------------ #

def _clean_alternative_text(text: str) -> str:
    """Clean alternative text from artifacts."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[.]{2,}$', '', text)
    text = re.sub(r'^[.\s]+', '', text)
    text = re.sub(r'(ENEM2024|4202MENE|\d{2}::\d{2}::\d{2})', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _dict_to_list(alternatives: Dict[str, str]) -> List[str]:
    """Convert letter→text dict to ordered list (no letter prefix)."""
    return [alternatives[l] for l in 'ABCDE' if l in alternatives]


# Factory
def create_enhanced_extractor() -> EnhancedAlternativeExtractor:
    """Create and return enhanced alternative extractor."""
    return EnhancedAlternativeExtractor()
