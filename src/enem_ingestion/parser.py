"""
Parser module for ENEM exam PDFs.

This module handles parsing of ENEM exam PDFs to extract questions,
alternatives, answer keys, and metadata.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import pdfplumber

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
        
        return QuestionMetadata(
            year=year,
            day=day or 1,
            caderno=caderno or "CD1",
            application_type=application_type,
            accessibility=accessibility
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
                    
                    # Extract alternatives with improved logic
                    alternatives = self._extract_alternatives(question_text)
                    
                    # For now, accept questions with at least 3 alternatives (while debugging)
                    if len(alternatives) < 3:
                        logger.warning(f"Question {q_num}: Found only {len(alternatives)} alternatives. Skipping question.")
                        continue
                    elif len(alternatives) != 5:
                        logger.warning(f"Question {q_num}: Expected 5 alternatives, found {len(alternatives)}")
                        # Show what we found for debugging
                        logger.debug(f"Question {q_num} alternatives: {[alt[:30] + '...' for alt in alternatives]}")
                    
                    # Pad with empty alternatives if needed (temporary for debugging)
                    while len(alternatives) < 5:
                        missing_letter = ['A', 'B', 'C', 'D', 'E'][len(alternatives)]
                        alternatives.append(f"{missing_letter}) [Alternative not found]")
                    
                    # Validate alternatives are in correct order (A, B, C, D, E)
                    expected_order = ['A', 'B', 'C', 'D', 'E']
                    actual_order = [alt[0] for alt in alternatives]
                    if actual_order != expected_order:
                        logger.warning(f"Question {q_num}: Alternatives not in alphabetical order: {actual_order}")
                        # Sort alternatives to ensure correct order
                        alternatives = sorted(alternatives, key=lambda x: x[0])
                    
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
        
        ENEM PDFs typically have 2 columns. This method reads:
        1. Left column from top to bottom
        2. Right column from top to bottom
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Text extracted in column order
        """
        try:
            # Get page dimensions
            page_width = page.width
            page_height = page.height
            
            # Define column boundaries (approximate)
            left_column = page.crop((0, 0, page_width * 0.5, page_height))
            right_column = page.crop((page_width * 0.5, 0, page_width, page_height))
            
            # Extract text from each column
            left_text = left_column.extract_text() or ""
            right_text = right_column.extract_text() or ""
            
            # Combine column texts
            combined_text = left_text
            if right_text.strip():
                combined_text += "\n" + right_text
                
            return combined_text
            
        except Exception as e:
            logger.warning(f"Failed to extract text by columns, falling back to default: {e}")
            # Fallback to default extraction
            return page.extract_text() or ""
    
    def _extract_alternatives(self, question_text: str) -> List[str]:
        """
        Extract alternatives from ENEM question text.
        
        ENEM PDFs have a unique format where alternatives appear as single letters
        followed by text, often without clear separators.
        
        Args:
            question_text: Raw question text
            
        Returns:
            List of exactly 5 formatted alternatives [A, B, C, D, E]
        """
        alternatives_dict = {}
        
        # Strategy 1: Search for pattern where single letter appears at start of line or after space
        # This handles ENEM's format where alternatives are like "A criticar o tipo" or "B rever o desempenho"
        
        # Split text into words and look for single letters followed by text
        words = question_text.split()
        
        for i, word in enumerate(words):
            # Look for isolated single letters A-E
            if word in 'ABCDE' and i + 1 < len(words):
                letter = word
                
                # Collect text for this alternative until we hit another letter or end
                alt_words = []
                j = i + 1
                
                while j < len(words):
                    next_word = words[j]
                    
                    # Stop if we hit another alternative letter, question marker, or page marker
                    if (next_word in 'ABCDE' and 
                        j + 1 < len(words) and 
                        len(words[j + 1]) > 2 and
                        not words[j + 1].startswith(('http', 'www', '2020', '201', '202'))):
                        break
                    
                    if re.match(r'^(QUESTÃO|LC\s*-|Página|\*\d+)', next_word):
                        break
                        
                    alt_words.append(next_word)
                    j += 1
                
                # Create alternative if we have enough text
                if len(alt_words) >= 3:  # At least 3 words
                    alt_text = ' '.join(alt_words).strip()
                    # Clean up common artifacts
                    alt_text = re.sub(r'\s+', ' ', alt_text)
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
                        if len(text.split()) >= 3:
                            alternatives_dict[letter] = f"{letter}) {text}"
        
        # Build final list in alphabetical order, ensuring no duplicates
        final_alternatives = []
        used_letters = set()
        
        for letter in 'ABCDE':
            if letter in alternatives_dict and letter not in used_letters:
                final_alternatives.append(alternatives_dict[letter])
                used_letters.add(letter)
            else:
                logger.debug(f"Missing alternative {letter} in question")
        
        # Remove any duplicates that might have slipped through
        seen_letters = set()
        clean_alternatives = []
        for alt in final_alternatives:
            letter = alt[0] if alt else ''
            if letter not in seen_letters:
                clean_alternatives.append(alt)
                seen_letters.add(letter)
        
        # Log results for debugging
        if len(clean_alternatives) > 0:
            logger.debug(f"Found {len(clean_alternatives)} alternatives: {[alt.split(')')[0] + ')' for alt in clean_alternatives]}")
        
        return clean_alternatives

    def _clean_question_text(self, text: str) -> str:
        """
        Clean and normalize question text.
        
        Args:
            text: Raw question text
            
        Returns:
            Cleaned question text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page markers and footers
        text = re.sub(r'LC\s*-\s*\d+°?\s*dia\s*\|\s*Caderno\s*\d+.*?Página\s*\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\*\d+[A-Z]+\d+\*', '', text)  # Remove codes like *010275AM8*
        
        # Remove excessive line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up common PDF artifacts
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
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
