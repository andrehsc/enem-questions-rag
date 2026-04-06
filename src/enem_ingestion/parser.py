"""
Parser module for ENEM exam PDFs.

This module handles parsing of ENEM exam PDFs to extract questions,
alternatives, answer keys, and metadata with integrated text normalization
for encoding issues (mojibake correction).
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import pdfplumber

from .text_normalizer import normalize_enem_text
from .text_sanitizer import sanitize_enem_text

logger = logging.getLogger(__name__)


class ExamType(Enum):
    """Types of ENEM exam files."""
    CADERNO_QUESTOES = "caderno_questoes"  # Question booklet
    GABARITO = "gabarito"  # Answer key


class Subject(Enum):
    """ENEM exam subjects."""
    LINGUAGENS = "linguagens"  # Languages, Codes and Technologies
    CIENCIAS_HUMANAS = "ciencias_humanas"  # Human Sciences
    CIENCIAS_NATUREZA = "ciencias_natureza"  # Natural Sciences  
    MATEMATICA = "matematica"  # Mathematics


class LanguageOption(Enum):
    """Language options for foreign language questions."""
    INGLES = "ingles"  # English
    ESPANHOL = "espanhol"  # Spanish


@dataclass
class QuestionMetadata:
    """Metadata for a question."""
    year: int
    day: int
    caderno: str  # CD1, CD2, etc.
    application_type: str  # regular, reaplicacao_PPL, etc.
    accessibility: Optional[str] = None  # libras, braille_ledor, PPL, etc.
    language: Optional[str] = None  # portuguese, spanish, english, etc.
    exam_type: Optional[str] = None  # ENEM, PPL, etc.


@dataclass  
class AnswerKey:
    """Answer key for a question."""
    question_number: int
    correct_answer: str  # A, B, C, D, E
    language_option: Optional[LanguageOption] = None
    subject: Optional[Subject] = None


@dataclass
class Question:
    """Parsed question data."""
    number: int
    text: str
    alternatives: List[str]  # A, B, C, D, E alternatives
    metadata: QuestionMetadata
    subject: Optional[Subject] = None
    context: Optional[str] = None  # Supporting text/images


class EnemPDFParser:
    """Parser for ENEM exam PDFs."""

    def __init__(self):
        """Initialize the parser."""
        self.question_pattern = re.compile(r'QUESTÃO\s+(\d+)', re.IGNORECASE)
        # Métricas dos guardrails para coleta
        self._last_guardrails_metrics = {
            'total_analyzed': 0,
            'direct_success': 0,
            'recovery_applied': 0,
            'critical_zone_detected': 0,
            'validation_failures': 0
        }
        # Pattern for alternatives - handles both formats: "A) text" and "A text"
        self.alternative_pattern = re.compile(r'\b([A-E])\s*\)?\s*([^A-E\n]{10,200}?)(?=\s*[A-E]\s|\n\n|\nQuestão|\nLC\s*-|$)', re.MULTILINE)
        
    def parse_filename(self, filename: str) -> QuestionMetadata:
        """
        Parse metadata from filename.
        
        Examples:
        - 2024_PV_impresso_D1_CD1.pdf
        - 2024_GB_reaplicacao_PPL_D1_CD1.pdf
        - 2024_PV_impresso_D1_CD10_ampliada.pdf
        - 2024_GB_D1_CD1.pdf (simplified format)
        
        Args:
            filename: PDF filename
            
        Returns:
            QuestionMetadata object
        """
        # Remove .pdf extension
        name = Path(filename).stem
        parts = name.split('_')
        
        # Handle simplified format for tests (minimum 4 parts: year_type_day_caderno)
        if len(parts) < 4:
            raise ValueError(f"Invalid filename format: {filename}")
        
        year = int(parts[0])
        file_type = parts[1]  # PV or GB
        
        # Find day and caderno
        day = None
        caderno = None
        application_type = "regular"
        accessibility = None
        language = "portuguese"  # Default language
        exam_type = "ENEM"  # Default exam type
        
        for i, part in enumerate(parts):
            if part.startswith('D') and len(part) == 2:
                day = int(part[1])
            elif part.startswith('CD'):
                caderno = part
            elif part == 'reaplicacao':
                application_type = "reaplicacao_PPL"
            elif part == 'PPL':
                if application_type != "reaplicacao_PPL":
                    accessibility = "PPL"
                exam_type = "PPL"
            elif part == 'impresso':
                exam_type = "ENEM"
            elif part == 'digital':
                exam_type = "ENEM_DIGITAL"
            elif 'espanhol' in part.lower():
                language = "spanish"
            elif 'ingles' in part.lower():
                language = "english"
        
        # Detect accessibility types from caderno number
        if caderno:
            cd_num = int(caderno[2:])
            if cd_num == 9 or cd_num == 11:
                if "braile" in name or "ledor" in name:
                    accessibility = "braille_ledor"
                elif accessibility != "PPL":
                    accessibility = "braille_ledor"
            elif cd_num == 10 or cd_num == 12:
                accessibility = "libras"
        
        # Determine language from filename context
        if 'braile_e_ledor' in name:
            accessibility = "braille_ledor"
        
        return QuestionMetadata(
            year=year,
            day=day or 1,
            caderno=caderno or "CD1",
            application_type=application_type,
            accessibility=accessibility,
            language=language,
            exam_type=exam_type
        )
    
    def parse_answer_key(self, pdf_path: Union[str, Path]) -> List[AnswerKey]:
        """
        Parse answer key from gabarito PDF.
        
        Args:
            pdf_path: Path to gabarito PDF
            
        Returns:
            List of AnswerKey objects
        """
        answers = []
        metadata = self.parse_filename(Path(pdf_path).name)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    logger.warning(f"No pages found in {pdf_path}")
                    return answers
                
                # Gabaritos are typically single page
                page = pdf.pages[0]
                text = page.extract_text()
                
                if not text:
                    logger.warning(f"No text extracted from {pdf_path}")
                    return answers
                
                lines = text.split('\n')
                
                # Look for answer pattern: "1 C C 46 C"
                answer_pattern = re.compile(r'^(\d+)\s+([A-E])\s*([A-E])?\s*(\d+)?\s*([A-E])?')
                
                for line in lines:
                    line = line.strip()
                    match = answer_pattern.match(line)
                    
                    if match:
                        q_num1 = int(match.group(1))
                        ans1_ing = match.group(2)  # English answer
                        ans1_esp = match.group(3)  # Spanish answer (if exists)
                        q_num2 = match.group(4)   # Second question number
                        ans2 = match.group(5)     # Second answer
                        
                        # First question (Languages - English)
                        if ans1_ing:
                            answers.append(AnswerKey(
                                question_number=q_num1,
                                correct_answer=ans1_ing,
                                language_option=LanguageOption.INGLES,
                                subject=Subject.LINGUAGENS if q_num1 <= 45 else Subject.CIENCIAS_HUMANAS
                            ))
                        
                        # First question (Languages - Spanish)  
                        if ans1_esp:
                            answers.append(AnswerKey(
                                question_number=q_num1,
                                correct_answer=ans1_esp,
                                language_option=LanguageOption.ESPANHOL,
                                subject=Subject.LINGUAGENS if q_num1 <= 45 else Subject.CIENCIAS_HUMANAS
                            ))
                        
                        # Second question (Human Sciences)
                        if q_num2 and ans2:
                            answers.append(AnswerKey(
                                question_number=int(q_num2),
                                correct_answer=ans2,
                                subject=Subject.CIENCIAS_HUMANAS
                            ))
                
                logger.info(f"Parsed {len(answers)} answers from {pdf_path}")
                return answers
                
        except Exception as e:
            logger.error(f"Error parsing answer key {pdf_path}: {e}")
            return answers
    
    def parse_questions(self, pdf_path: Union[str, Path]) -> List[Question]:
        """
        Parse questions from caderno PDF with column-aware text extraction.
        
        Args:
            pdf_path: Path to caderno PDF
            
        Returns:
            List of Question objects
        """
        questions = []
        metadata = self.parse_filename(Path(pdf_path).name)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    logger.warning(f"No pages found in {pdf_path}")
                    return questions
                
                full_text = ""
                for page in pdf.pages:
                    page_text = self._extract_text_by_columns(page)
                    if page_text:
                        full_text += page_text + "\n"
                
                # Find all questions
                question_matches = list(self.question_pattern.finditer(full_text))
                
                for i, match in enumerate(question_matches):
                    q_num = int(match.group(1))
                    q_start = match.end()
                    
                    # Find end of question (start of next question or end of text)
                    if i + 1 < len(question_matches):
                        q_end = question_matches[i + 1].start()
                    else:
                        q_end = len(full_text)
                    
                    question_text = full_text[q_start:q_end].strip()
                    
                    # Clean up the question text
                    question_text = self._clean_question_text(question_text)
                    
                    # Extract alternatives with improved logic and guardrails context
                    alternatives = self._extract_alternatives_with_context(question_text, q_num, metadata.day)
                    
                    # For now, accept questions with at least 3 alternatives (while debugging)
                    if len(alternatives) < 3:
                        logger.warning(f"Question {q_num}: Found only {len(alternatives)} alternatives. Skipping question.")
                        continue
                    elif len(alternatives) != 5:
                        logger.warning(f"Question {q_num}: Expected 5 alternatives, found {len(alternatives)}")
                        # Show what we found for debugging
                        logger.debug(f"Question {q_num} alternatives: {[alt[:30] + '...' for alt in alternatives]}")
                    
                    # Remove duplicates and fix ordering
                    clean_alternatives = []
                    letters_used = set()
                    
                    # First pass: collect unique alternatives in order
                    for letter in ['A', 'B', 'C', 'D', 'E']:
                        for alt in alternatives:
                            if alt.startswith(f"{letter})") and letter not in letters_used:
                                clean_alternatives.append(alt)
                                letters_used.add(letter)
                                break
                    
                    # No longer pad with placeholders (Story 8.2)
                    # Missing alternatives will be caught by the confidence scorer
                    
                    # Sort to ensure correct order
                    alternatives = sorted(clean_alternatives, key=lambda x: x[0])
                    
                    if len(set([alt[0] for alt in alternatives])) != 5:
                        logger.warning(f"Question {q_num}: Still has duplicate letters after cleanup")
                    
                    # Determine subject based on question number and day
                    subject = self._determine_subject(q_num, metadata.day)
                    
                    questions.append(Question(
                        number=q_num,
                        text=question_text,
                        alternatives=alternatives,
                        metadata=metadata,
                        subject=subject
                    ))
                
                logger.info(f"Parsed {len(questions)} questions from {pdf_path}")
                return questions
                
        except Exception as e:
            logger.error(f"Error parsing questions {pdf_path}: {e}")
            return questions
    
    def _extract_text_by_columns(self, page) -> str:
        """
        Extract text from a page respecting column layout.
        
        Enhanced version for 2024 format with better column detection
        and text extraction methods.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Text extracted in column order
        """
        try:
            # Get page dimensions
            page_width = page.width
            page_height = page.height
            
            # First, check for 2022-2023 format with central separator pollution
            full_text_sample = self._extract_text_robust(page)[:2000]  # Sample to check
            has_separator_pollution = (
                ('2202 MENE' in full_text_sample) or  # 2022 format separator
                ('enem2022' in full_text_sample.lower()) or
                ('enem 2022' in full_text_sample.lower()) or
                ('2023 MENE' in full_text_sample) or
                ('enem2023' in full_text_sample.lower())
            )
            
            if has_separator_pollution:
                logger.debug("Detected 2022-2023 format with central separator - using enhanced extraction")
                
                # Use wider margins to avoid separator contamination
                margin = page_width * 0.08  # 8% margin from center
                left_column = page.crop((0, 0, page_width * 0.5 - margin, page_height))
                right_column = page.crop((page_width * 0.5 + margin, 0, page_width, page_height))
                
                left_text = self._extract_text_robust(left_column)
                right_text = self._extract_text_robust(right_column)
                
                # Clean separator pollution
                left_text = self._clean_separator_pollution(left_text)
                right_text = self._clean_separator_pollution(right_text)
                
                combined_text = left_text + "\n\n" + right_text
            else:
                # Standard column extraction
                left_column = page.crop((0, 0, page_width * 0.5, page_height))
                right_column = page.crop((page_width * 0.5, 0, page_width, page_height))
                
                left_text = self._extract_text_robust(left_column)
                right_text = self._extract_text_robust(right_column)
                
                combined_text = left_text + "\n" + right_text
            
            # If extraction seems poor (too short or too repetitive), try alternative method
            if len(combined_text.strip()) < 100 or self._is_text_too_repetitive(combined_text):
                logger.debug("Column extraction poor, trying full page extraction")
                combined_text = self._extract_text_robust(page)
            
            return combined_text
            
        except Exception as e:
            logger.warning(f"Column extraction failed: {e}, falling back to full page")
            return self._extract_text_robust(page)

    def _extract_text_robust(self, page_or_crop) -> str:
        """
        Robust text extraction with multiple fallback methods.
        
        Args:
            page_or_crop: pdfplumber page or cropped page object
            
        Returns:
            str: Extracted text
        """
        try:
            # Method 1: Standard extraction
            text = page_or_crop.extract_text() or ""
            
            # Method 2: If text is too short, try with different layout settings
            if len(text.strip()) < 50:
                text = page_or_crop.extract_text(layout=True) or ""
            
            # Method 3: If still poor, try character-level extraction
            if len(text.strip()) < 50:
                chars = page_or_crop.chars
                if chars:
                    text = ' '.join([char['text'] for char in chars])
                    
            return text
            
        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
            return ""

    def _is_text_too_repetitive(self, text: str) -> bool:
        """
        Check if text has too much repetition (indicates extraction problems).
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if text appears too repetitive
        """
        if not text or len(text) < 100:
            return True
            
        # Check for repetitive patterns
        words = text.split()
        if len(words) < 10:
            return True
            
        # Count unique words vs total words
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words)
        
        # If less than 30% unique words, it's probably repetitive/garbled
        return repetition_ratio < 0.3
    
    def _extract_alternatives_with_context(self, question_text: str, question_number: int, day: int) -> List[str]:
        """
        Extract alternatives with structural guardrails context.
        
        Args:
            question_text: Raw question text
            question_number: Actual question number (1-180)
            day: Exam day (1 or 2)
            
        Returns:
            List of exactly 5 formatted alternatives [A, B, C, D, E]
        """
        # Try enhanced extractor with structural guardrails
        try:
            from .alternative_extractor import create_enhanced_extractor
            from .enem_structure_spec import EnemStructuralGuardrailsController
            
            enhanced_extractor = create_enhanced_extractor()
            enhanced_result = enhanced_extractor.extract_alternatives(question_text)
            
            # Apply Winston's structural guardrails with real context
            try:
                guardrails_controller = EnemStructuralGuardrailsController()
                
                # Convert enhanced result to guardrails format
                guardrails_input = {
                    'question': question_text[:200] + '...' if len(question_text) > 200 else question_text,
                    'alternatives': [
                        {'text': alt} for alt in enhanced_result.alternatives
                    ]
                }
                
                # Apply guardrails validation and enhancement with real context
                guardrails_result = guardrails_controller.process_question_with_guardrails(
                    question_text, 
                    question_number, 
                    day, 
                    guardrails_input
                )
                
                # Process guardrails result
                if guardrails_result['status'] == 'SUCCESS':
                    validated_alternatives = [
                        alt['text'] for alt in guardrails_result['data']['alternatives']
                    ]
                    
                    confidence = guardrails_result['confidence']
                    risk_level = guardrails_result['guardrails_applied']['risk_level']
                    
                    # Collect metrics
                    self._last_guardrails_metrics['total_analyzed'] += 1
                    self._last_guardrails_metrics['direct_success'] += 1
                    if day == 2 and 91 <= question_number <= 110:
                        self._last_guardrails_metrics['critical_zone_detected'] += 1
                    
                    logger.info(f"🛡️ Q{question_number} Guardrails SUCCESS: {len(validated_alternatives)} alternatives "
                               f"(confidence: {confidence:.2f}, risk: {risk_level})")
                    
                    # Use validated result if sufficient
                    if len(validated_alternatives) >= 4 and confidence > 0.6:
                        final_alternatives = validated_alternatives[:]

                        return final_alternatives[:5]
                
                elif guardrails_result['status'] == 'VALIDATION_FAILED':
                    # Apply recovery strategy
                    recovery = guardrails_result['recovery_strategy']
                    risk_level = guardrails_result['guardrails_applied']['risk_level']
                    
                    # Collect metrics
                    self._last_guardrails_metrics['total_analyzed'] += 1
                    self._last_guardrails_metrics['recovery_applied'] += 1
                    self._last_guardrails_metrics['validation_failures'] += 1
                    if day == 2 and 91 <= question_number <= 110:
                        self._last_guardrails_metrics['critical_zone_detected'] += 1
                    
                    logger.warning(f"⚡ Q{question_number} Guardrails RECOVERY: risk={risk_level}, "
                                 f"strategy={recovery['action']}")
                    
                    # Check if it's critical zone (91-110) for special handling
                    if day == 2 and 91 <= question_number <= 110:
                        logger.warning(f"🔥 Q{question_number} in CRITICAL ZONE - applying enhanced recovery")
                    
                    # For now, continue with enhanced result but log the issue
                    pass
                    
            except Exception as guardrails_error:
                logger.warning(f"Q{question_number} Guardrails processing failed: {guardrails_error}")
            
            # Use enhanced result if guardrails didn't improve it or failed
            if len(enhanced_result.alternatives) >= 4 and enhanced_result.confidence > 0.5:
                logger.debug(f"Q{question_number} Enhanced extractor success: {len(enhanced_result.alternatives)} alternatives "
                           f"(confidence: {enhanced_result.confidence:.2f}, strategy: {enhanced_result.strategy_used.value})")
                
                # Return what we have — no placeholder padding (Story 8.2)
                final_alternatives = enhanced_result.alternatives[:]

                return final_alternatives[:5]
            
            # Log what happened with enhanced extractor
            logger.debug(f"Q{question_number} Enhanced extractor insufficient: {len(enhanced_result.alternatives)} alternatives "
                        f"(confidence: {enhanced_result.confidence:.2f}), falling back to legacy")
                        
        except Exception as e:
            logger.warning(f"Q{question_number} Enhanced extractor failed: {e}, falling back to legacy algorithm")
        
        # Fallback to original method without context
        return self._extract_alternatives(question_text)

    def _extract_alternatives(self, question_text: str) -> List[str]:
        """
        Extract alternatives from ENEM question text (legacy method without guardrails).
        
        Enhanced version using multiple extraction strategies with fallback to legacy algorithm.
        
        Args:
            question_text: Raw question text
            
        Returns:
            List of exactly 5 formatted alternatives [A, B, C, D, E]
        """
        # Try enhanced extractor first (Strategy Pattern approach)
        try:
            from .alternative_extractor import create_enhanced_extractor
            
            enhanced_extractor = create_enhanced_extractor()
            result = enhanced_extractor.extract_alternatives(question_text)
            
            # Use enhanced result if it found enough alternatives
            if len(result.alternatives) >= 4 and result.confidence > 0.5:
                logger.debug(f"Enhanced extractor success: {len(result.alternatives)} alternatives "
                           f"(confidence: {result.confidence:.2f}, strategy: {result.strategy_used.value})")
                
                # Pad to 5 alternatives if needed (for compatibility)
                final_alternatives = result.alternatives[:]
                while len(final_alternatives) < 5:
                    final_alternatives.append(f"{chr(65 + len(final_alternatives))}) [Alternative not found]")
                    
                return final_alternatives[:5]
            
            # Log what happened with enhanced extractor
            logger.debug(f"Enhanced extractor insufficient: {len(result.alternatives)} alternatives "
                        f"(confidence: {result.confidence:.2f}), falling back to legacy")
                        
        except Exception as e:
            logger.warning(f"Enhanced extractor failed: {e}, falling back to legacy algorithm")
        
        # Fallback to legacy algorithm (existing code)
        alternatives_dict = {}
        
        # Pre-clean the text to remove artifacts before processing
        clean_text = self._pre_clean_alternatives_text(question_text)
        
        # Detect likely year from artifacts in text (for format-specific strategies)
        likely_year = self._detect_year_from_text(clean_text)
        
        # Strategy 1: Search for pattern where single letter appears at start of line or after space
        # This handles ENEM's format where alternatives are like "A criticar o tipo" or "B rever o desempenho"
        
        # Split text into words and look for single letters followed by text
        words = clean_text.split()
        
        for i, word in enumerate(words):
            # Look for isolated single letters A-E
            if word in 'ABCDE' and i + 1 < len(words):
                letter = word
                
                # Skip if this letter was already found (avoid duplicates)
                if letter in alternatives_dict:
                    continue
                
                # Collect text for this alternative until we hit another letter or end
                alt_words = []
                j = i + 1
                
                while j < len(words):
                    next_word = words[j]
                    
                    # Stop if we hit another alternative letter, question marker, or page marker
                    if (next_word in 'ABCDE' and 
                        j + 1 < len(words) and 
                        len(words[j + 1]) > 2 and
                        not words[j + 1].startswith(('http', 'www', '2020', '201', '202', 'ENEM', 'REDAÇÃO'))):
                        break
                    
                    if re.match(r'^(QUESTÃO|LC\s*-|Página|\*\d+|ENEM2024|4202MENE)', next_word):
                        break
                    
                    # Skip repetitive patterns common in 2024
                    if re.match(r'^(ENEM2024|4202MENE|\d{2}::\d{2}::\d{2})', next_word):
                        break
                        
                    alt_words.append(next_word)
                    j += 1
                
                # Create alternative if we have enough text
                if len(alt_words) >= 1:  # Even more permissive for math/science questions
                    alt_text = ' '.join(alt_words).strip()
                    # Enhanced cleanup for 2024 artifacts
                    alt_text = self._clean_alternative_text(alt_text)
                    # More permissive validation - accept single meaningful words
                    if len(alt_text.strip()) >= 3:  # At least 3 characters
                        alternatives_dict[letter] = f"{letter}) {alt_text}"
        
        # Strategy 2: Line-based approach for cases where Strategy 1 misses some
        if len(alternatives_dict) < 5:
            lines = [line.strip() for line in question_text.split('\n') if line.strip()]
            
            for i, line in enumerate(lines):
                # Look for lines that start with a single letter
                match = re.match(r'^([A-E])\s+(.+)', line)
                if match and match.group(1) not in alternatives_dict:
                    letter = match.group(1)
                    text = match.group(2)
                    
                    # Look for continuation in next lines
                    continuation = []
                    for j in range(i + 1, min(i + 4, len(lines))):
                        next_line = lines[j]
                        if re.match(r'^[A-E]\s+', next_line):  # Next alternative
                            break
                        if re.match(r'^(QUESTÃO|LC\s*-|Página)', next_line):
                            break
                        if len(next_line) > 10:  # Substantial text
                            continuation.append(next_line)
                    
                    if continuation:
                        text += ' ' + ' '.join(continuation)
                    
                    # Clean and store
                    text = re.sub(r'\s+', ' ', text.strip())
                    if len(text.split()) >= 3:
                        alternatives_dict[letter] = f"{letter}) {text}"
        
        # Strategy 3: Pattern matching for embedded alternatives
        if len(alternatives_dict) < 5:
            # Look for patterns like "...text A option text B option text..."
            for letter in 'ABCDE':
                if letter not in alternatives_dict:
                    # Find letter followed by lowercase word (typical alternative start)
                    pattern = f'{letter}\\s+([a-z][^A-E]*?)(?=[A-E]\\s+[a-z]|QUESTÃO|LC\\s*-|$)'
                    match = re.search(pattern, question_text)
                    if match:
                        text = match.group(1).strip()
                        # Clean up and validate
                        text = re.sub(r'\s+', ' ', text)
                        text = re.sub(r'[.]*$', '', text)  # Remove trailing dots
                        if len(text.split()) >= 2:  # More permissive
                            alternatives_dict[letter] = f"{letter}) {text}"

        # Strategy 4: Special handling for math/science questions (numbers, formulas)
        if len(alternatives_dict) < 5:
            # Look for alternatives that might be just numbers or short formulas
            for letter in 'ABCDE':
                if letter not in alternatives_dict:
                    # More flexible pattern that captures math expressions, numbers, single words
                    pattern = f'{letter}\\s+([^A-E\\n]{{1,50}}?)(?=\\s*[A-E]\\s|\\n\\n|QUESTÃO|LC\\s*-|$)'
                    matches = re.findall(pattern, question_text, re.DOTALL)
                    if matches:
                        for match in matches:
                            text = match.strip()
                            # Clean and validate
                            text = self._clean_alternative_text(text)
                            # Accept even short answers for math (like "2π", "0,5", etc.)
                            if len(text.strip()) >= 1 and text.strip() not in alternatives_dict.values():
                                alternatives_dict[letter] = f"{letter}) {text}"
                                break
        
        # Strategy 5: Enhanced 2022-2023 specific extraction (PRIORITY for these years)
        if likely_year in [2022, 2023]:
            # For 2022-2023, try specific strategies first and use them if successful
            temp_alternatives = self._extract_alternatives_2022_2023(question_text, {})
            if len(temp_alternatives) >= 4:  # If 2022-2023 strategy finds most alternatives
                logger.debug(f"Using 2022-2023 specific extraction: {len(temp_alternatives)} alternatives found")
                alternatives_dict.update(temp_alternatives)
            elif len(alternatives_dict) < 5:  # Fallback if not enough found
                alternatives_dict = self._extract_alternatives_2022_2023(question_text, alternatives_dict)
        
        # Build final list in alphabetical order, ensuring no duplicates
        final_alternatives = []
        
        for letter in 'ABCDE':
            if letter in alternatives_dict:
                alt_text = alternatives_dict[letter]
                # Final cleanup and validation - more lenient for 2022-2023
                min_length = 10 if likely_year in [2022, 2023] else 3
                if alt_text and len(alt_text.strip()) > min_length:
                    final_alternatives.append(alt_text)
            else:
                logger.debug(f"Missing alternative {letter} in question")
        
        # Remove any problematic duplicates by content similarity
        clean_alternatives = []
        seen_contents = set()
        
        for alt in final_alternatives:
            if alt and len(alt) > 3:
                alt_content = alt[3:].strip().lower()  # Remove "X) " prefix for comparison
                if alt_content not in seen_contents and len(alt_content) > 0:
                    clean_alternatives.append(alt)
                    seen_contents.add(alt_content)
                else:
                    logger.debug(f"Skipping duplicate/empty alternative: {alt[:50]}...")
        
        # Log results for debugging
        if len(clean_alternatives) > 0:
            logger.debug(f"Found {len(clean_alternatives)} alternatives: {[alt.split(')')[0] + ')' for alt in clean_alternatives]}")
        
        return clean_alternatives

    def _detect_year_from_text(self, text: str) -> int:
        """Detect likely year from text artifacts and format patterns."""
        # Check for explicit year markers first
        if 'ENEM2024' in text or '4202MENE' in text:
            return 2024
        elif any(marker in text for marker in ['2023', 'ENEM 2023']):
            return 2023
        elif any(marker in text for marker in ['2022', 'ENEM 2022']):
            return 2022
        elif any(marker in text for marker in ['2021', 'ENEM 2021']):
            return 2021
        elif any(marker in text for marker in ['2020', 'ENEM 2020']):
            return 2020
        
        # Check for format patterns specific to 2022-2023
        import re
        # Pattern 1: Compact double letters (AA, BB, CC)
        compact_double_pattern = r'([A-E])\1\s+'
        compact_matches = re.findall(compact_double_pattern, text)
        
        # Pattern 2: Spaced double letters (A A, B B, C C)  
        spaced_double_pattern = r'([A-E])\s+\1\s+'
        spaced_matches = re.findall(spaced_double_pattern, text)
        
        if len(compact_matches) >= 3 or len(spaced_matches) >= 3:
            return 2022  # This pattern is characteristic of 2022-2023
        
        return 2024  # Default to most recent format

    def _extract_alternatives_2022_2023(self, question_text: str, existing_alternatives: dict) -> dict:
        """
        Enhanced extraction specifically for 2022-2023 format challenges.
        These years have different layouts and require more flexible parsing.
        """
        alternatives_dict = existing_alternatives.copy()
        
        # Strategy 5A: Double letter format specific to 2022-2023 (AA, BB, CC, DD, EE)
        # This pattern handles intercalated text by stopping at punctuation
        double_letter_compact_pattern = r'([A-E])\1\s+([^.!?]+[.!?]?)'
        matches = re.findall(double_letter_compact_pattern, question_text, re.MULTILINE)
        for letter, text in matches:
            if letter not in alternatives_dict:
                clean_text = self._clean_alternative_text(text.strip())
                # Remove trailing punctuation if it's followed by uppercase (likely next sentence)
                clean_text = re.sub(r'[.!?]\s*$', '', clean_text)
                # Ensure minimum quality
                if len(clean_text) >= 5 and not re.match(r'^[A-Z\s]*$', clean_text):
                    alternatives_dict[letter] = f"{letter}) {clean_text}"
        
        # Strategy 5B: Spaced double letter format (A A, B B, C C, etc.)
        double_letter_spaced_pattern = r'([A-E])\s+\1\s+([^A-E]{15,300}?)(?=\n[A-E]\s+[A-E]\s+|\nQUESTÃO|$)'
        matches = re.findall(double_letter_spaced_pattern, question_text, re.MULTILINE | re.DOTALL)
        for letter, text in matches:
            if letter not in alternatives_dict:
                clean_text = self._clean_alternative_text(text.strip())
                # Remove any trailing content after sentence-ending punctuation
                clean_text = re.sub(r'[.!?]\s*[A-Z].*$', '.', clean_text)
                if len(clean_text) >= 8:  # More reasonable threshold
                    alternatives_dict[letter] = f"{letter}) {clean_text}"
        
        # Strategy 5C: Look for alternatives with parentheses format: (A) text, (B) text
        parentheses_pattern = r'\(([A-E])\)\s*([^()]+?)(?=\([A-E]\)|$)'
        matches = re.findall(parentheses_pattern, question_text, re.DOTALL)
        for letter, text in matches:
            if letter not in alternatives_dict:
                clean_text = self._clean_alternative_text(text.strip())
                if len(clean_text) >= 3:
                    alternatives_dict[letter] = f"{letter}) {clean_text}"
        
        # Strategy 5D: Look for alternatives separated by newlines with letter at start
        lines = [line.strip() for line in question_text.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            match = re.match(r'^([A-E])[.)]\s*(.+)', line)
            if match and match.group(1) not in alternatives_dict:
                letter = match.group(1)
                text = match.group(2)
                
                # Collect continuation lines until next alternative or end
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_line = lines[j]
                    if re.match(r'^[A-E][.)]', next_line):
                        break
                    if len(next_line) > 3 and not re.match(r'^(QUESTÃO|Página)', next_line):
                        text += ' ' + next_line
                
                clean_text = self._clean_alternative_text(text.strip())
                if len(clean_text) >= 3:
                    alternatives_dict[letter] = f"{letter}) {clean_text}"
        
        # Strategy 5E: Relaxed single-letter detection for sparse layouts
        words = question_text.split()
        for i, word in enumerate(words):
            if word in 'ABCDE' and word not in alternatives_dict:
                if i + 1 < len(words):
                    # Be more permissive about what constitutes valid alternative text
                    alt_text = []
                    j = i + 1
                    while j < len(words) and len(alt_text) < 20:  # Limit to prevent runaway
                        if words[j] in 'ABCDE' and j + 1 < len(words):
                            # Check if this is likely another alternative
                            if (len(alt_text) > 0 and 
                                not words[j + 1].startswith(('http', 'www', 'QUESTÃO', 'Página'))):
                                break
                        alt_text.append(words[j])
                        j += 1
                    
                    if len(alt_text) >= 1:  # Very permissive for 2022-2023
                        text = ' '.join(alt_text).strip()
                        clean_text = self._clean_alternative_text(text)
                        if len(clean_text) >= 2:  # Allow shorter alternatives
                            alternatives_dict[word] = f"{word}) {clean_text}"
        
        return alternatives_dict

    def _clean_separator_pollution(self, text: str) -> str:
        """
        Clean separator pollution from 2022-2023 PDFs.
        
        These formats have repeated "enem2022"/"enem2023" or "2202 MENE"/"3202 MENE" 
        patterns in the center that interfere with text extraction.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text with separator pollution removed
        """
        if not text:
            return text
        
        # Remove common separator patterns
        patterns_to_remove = [
            r'2202\s*MENE\s*',  # 2022 format
            r'MENE\s*2202\s*',  # 2022 format variant
            r'3202\s*MENE\s*',  # 2023 format (if exists)
            r'MENE\s*3202\s*',  # 2023 format variant
            r'enem\s*2022\s*',  # Direct enem2022
            r'enem\s*2023\s*',  # Direct enem2023
            r'\*\d{6}[A-Z]{2}\d?\*',  # Barcode patterns like *010275AM2*
        ]
        
        cleaned_text = text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace created by cleaning
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)  # Max 2 consecutive newlines
        
        return cleaned_text.strip()

    def _clean_question_text(self, text: str) -> str:
        """
        Clean and normalize question text.
        
        Applies text normalization to fix encoding issues (mojibake)
        and then performs standard PDF artifact cleanup with enhanced
        cleaning for 2024 ENEM format issues.
        
        Args:
            text: Raw question text extracted from PDF
            
        Returns:
            str: Cleaned and normalized question text
        """
        if not text:
            return ""
        
        # Apply text normalization for encoding issues (mojibake correction)
        text = normalize_enem_text(text)

        # Apply content-level sanitization (Story 8.1)
        text = sanitize_enem_text(text)
        
        # ENHANCED CLEANING FOR 2024 FORMAT ISSUES
        # Remove repetitive ENEM2024 patterns (more comprehensive)
        text = re.sub(r'(ENEM2024)+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(4202MENE)+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ENEM20E4', '', text, flags=re.IGNORECASE)
        
        # Remove repetitive year patterns
        text = re.sub(r'(\d{4}){3,}', '', text)
        
        # Remove repetitive time patterns like 1177::5522::4488
        text = re.sub(r'(\d{2}::\d{2}::\d{2})+', '', text)
        
        # Remove repetitive coding patterns and subject headers at end
        text = re.sub(r'(CD\d+\s*)+', '', text)
        text = re.sub(r'(REDAÇÃO\s*1100//0099//\d{8}\s*\d{2}::\d{2}::\d{2})+', '', text)
        text = re.sub(r'\s+(LINGUAGENS,\s*CÓDIGOS|CIÊNCIAS\s*HUMANAS|MATEMÁTICA).*$', '', text, flags=re.IGNORECASE)
        
        # Remove trailing subject and technology patterns
        text = re.sub(r'\s+\d+\s+(LINGUAGENS|CÓDIGOS|TECNOLOGIAS|CIÊNCIAS|HUMANAS|NATUREZA|MATEMÁTICA).*$', '', text, flags=re.IGNORECASE)
        
        # Remove repetitive single letters/numbers at end
        text = re.sub(r'\s+[A-Z0-9]\s*$', '', text)
        text = re.sub(r'([A-Z0-9E]{8,})$', '', text)  # Remove long repetitive sequences at end
        
        # Remove trailing numbers that look like page/section markers
        text = re.sub(r'\s+\d{1,2}\s*$', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page markers and footers
        text = re.sub(r'LC\s*-\s*\d+°?\s*dia\s*\|\s*Caderno\s*\d+.*?Página\s*\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\*\d+[A-Z]+\d+\*', '', text)  # Remove codes like *010275AM8*
        
        # Remove excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up common PDF artifacts
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Final cleanup - remove trailing repetitive characters
        text = re.sub(r'([A-Z0-9])\1{5,}$', '', text)
        
        return text.strip()

    def _pre_clean_alternatives_text(self, text: str) -> str:
        """
        Pre-clean text before alternative extraction to remove 2024 artifacts.
        
        Args:
            text: Raw question text
            
        Returns:
            str: Pre-cleaned text ready for alternative extraction
        """
        # Remove repetitive ENEM2024 patterns that interfere with parsing
        text = re.sub(r'(ENEM2024){2,}', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'(4202MENE){2,}', ' ', text, flags=re.IGNORECASE)
        
        # Remove time patterns
        text = re.sub(r'\d{2}::\d{2}::\d{2}', ' ', text)
        
        # Remove coding artifacts
        text = re.sub(r'REDAÇÃO\s*1100//0099//\d{8}', ' ', text)
        text = re.sub(r'CÓDIGOS\s*E\s*SUAS\s*TECNOLOGIAS', ' ', text)
        
        # Normalize spacing
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _clean_alternative_text(self, text: str) -> str:
        """
        Clean individual alternative text removing 2024 specific artifacts.
        
        Args:
            text: Raw alternative text
            
        Returns:
            str: Cleaned alternative text
        """
        # Remove trailing artifacts common in 2024
        text = re.sub(r'(ENEM2024|4202MENE|ENEM20E4|REDAÇÃO).*$', '', text, flags=re.IGNORECASE)
        
        # Remove subject headers that appear in alternatives
        text = re.sub(r'(LINGUAGENS,\s*CÓDIGOS|CIÊNCIAS\s*HUMANAS|MATEMÁTICA).*$', '', text, flags=re.IGNORECASE)
        
        # Remove repetitive patterns at the end
        text = re.sub(r'([A-Z0-9])\1{3,}$', '', text)
        
        # Remove time codes
        text = re.sub(r'\d{2}::\d{2}::\d{2}.*$', '', text)
        
        # Remove numbers/codes at the end
        text = re.sub(r'\s+\d{8,}.*$', '', text)
        text = re.sub(r'\s+\d{1,2}\s*$', '', text)  # Remove trailing page numbers
        
        # Clean up spacing and punctuation
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*\.$', '.', text)  # Fix spacing before period
        
        # Remove incomplete words at the end (common artifacts)
        words = text.split()
        if words and len(words[-1]) <= 2 and words[-1].isupper():
            words = words[:-1]
            text = ' '.join(words)
        
        return text.strip()

    def _determine_subject(self, question_number: int, day: int) -> Subject:
        """Determine subject based on question number and day."""
        if day == 1:
            # Day 1: Languages (1-45) and Human Sciences (46-90)
            if 1 <= question_number <= 45:
                return Subject.LINGUAGENS
            elif 46 <= question_number <= 90:
                return Subject.CIENCIAS_HUMANAS
        elif day == 2:
            # Day 2: Natural Sciences (91-135) and Mathematics (136-180)
            if 91 <= question_number <= 135:
                return Subject.CIENCIAS_NATUREZA
            elif 136 <= question_number <= 180:
                return Subject.MATEMATICA
        
        # Default fallback
        return Subject.LINGUAGENS
    
    def parse_file(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Parse any ENEM PDF file (auto-detect type).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with parsed data
        """
        filename = Path(pdf_path).name
        
        if '_GB_' in filename:
            # Answer key
            return {
                'type': ExamType.GABARITO,
                'data': self.parse_answer_key(pdf_path),
                'metadata': self.parse_filename(filename)
            }
        elif '_PV_' in filename:
            # Question booklet
            return {
                'type': ExamType.CADERNO_QUESTOES,
                'data': self.parse_questions(pdf_path),
                'metadata': self.parse_filename(filename)
            }
        else:
            raise ValueError(f"Unknown file type: {filename}")

    def _estimate_question_number(self, question_text: str) -> int:
        """
        Estimate question number from context for guardrails integration.
        
        Args:
            question_text: Question text to analyze
            
        Returns:
            Estimated question number (1-180)
        """
        # Try to find explicit question number in text
        q_match = self.question_pattern.search(question_text)
        if q_match:
            return int(q_match.group(1))
        
        # Fallback: estimate based on content patterns
        # Mathematical content suggests Day 2 (questions 91-180)
        math_indicators = ['∫', '√', '∑', '∞', '≤', '≥', '≠', '±', 'função', 'equação']
        if any(indicator in question_text.lower() for indicator in math_indicators):
            return 95  # Default to critical zone
        
        # Language/literature suggests Day 1 (questions 1-90)
        lang_indicators = ['texto', 'literatura', 'poema', 'linguagem', 'autor']
        if any(indicator in question_text.lower() for indicator in lang_indicators):
            return 15  # Default to safe zone Day 1
        
        # Conservative default
        return 50
    
    def _estimate_day_from_question_number(self, question_number: int) -> int:
        """
        Estimate exam day from question number.
        
        Args:
            question_number: Question number (1-180)
            
        Returns:
            Day (1 or 2)
        """
        if question_number <= 90:
            return 1  # Day 1: Linguagens + Humanas + Redação
        else:
            return 2  # Day 2: Matemática + Natureza
