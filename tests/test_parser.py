"""Tests for the ENEM PDF parser module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.enem_ingestion.parser import (
    EnemPDFParser, QuestionMetadata, AnswerKey, Question,
    ExamType, Subject, LanguageOption
)


class TestEnemPDFParser:
    """Test cases for EnemPDFParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = EnemPDFParser()

    def test_parse_filename_regular(self):
        """Test parsing regular filename."""
        filename = "2024_PV_impresso_D1_CD1.pdf"
        metadata = self.parser.parse_filename(filename)
        
        assert metadata.year == 2024
        assert metadata.day == 1
        assert metadata.caderno == "CD1"
        assert metadata.application_type == "regular"
        assert metadata.accessibility is None

    def test_parse_filename_ppl_reaplicacao(self):
        """Test parsing PPL reaplicacao filename."""
        filename = "2024_GB_reaplicacao_PPL_D1_CD1.pdf"
        metadata = self.parser.parse_filename(filename)
        
        assert metadata.year == 2024
        assert metadata.day == 1
        assert metadata.caderno == "CD1"
        assert metadata.application_type == "reaplicacao_PPL"
        assert metadata.accessibility is None

    def test_parse_filename_libras(self):
        """Test parsing Libras accessibility filename."""
        filename = "2024_PV_impresso_D1_CD10.pdf"
        metadata = self.parser.parse_filename(filename)
        
        assert metadata.year == 2024
        assert metadata.day == 1
        assert metadata.caderno == "CD10"
        assert metadata.application_type == "regular"
        assert metadata.accessibility == "libras"

    def test_parse_filename_braille(self):
        """Test parsing Braille accessibility filename.""" 
        filename = "2024_PV_impresso_D1_CD9_ampliada.pdf"
        metadata = self.parser.parse_filename(filename)
        
        assert metadata.year == 2024
        assert metadata.day == 1
        assert metadata.caderno == "CD9"
        assert metadata.application_type == "regular"
        assert metadata.accessibility == "braille_ledor"

    def test_parse_filename_invalid(self):
        """Test parsing invalid filename."""
        with pytest.raises(ValueError):
            self.parser.parse_filename("invalid.pdf")

    def test_determine_subject_day1(self):
        """Test subject determination for day 1."""
        # Languages (1-45)
        assert self.parser._determine_subject(1, 1) == Subject.LINGUAGENS
        assert self.parser._determine_subject(45, 1) == Subject.LINGUAGENS
        
        # Human Sciences (46-90)
        assert self.parser._determine_subject(46, 1) == Subject.CIENCIAS_HUMANAS
        assert self.parser._determine_subject(90, 1) == Subject.CIENCIAS_HUMANAS

    def test_determine_subject_day2(self):
        """Test subject determination for day 2."""
        # Natural Sciences (91-135)
        assert self.parser._determine_subject(91, 2) == Subject.CIENCIAS_NATUREZA
        assert self.parser._determine_subject(135, 2) == Subject.CIENCIAS_NATUREZA
        
        # Mathematics (136-180)
        assert self.parser._determine_subject(136, 2) == Subject.MATEMATICA
        assert self.parser._determine_subject(180, 2) == Subject.MATEMATICA

    @patch('pdfplumber.open')
    def test_parse_answer_key_success(self, mock_pdfplumber):
        """Test successful answer key parsing."""
        # Mock PDF content
        mock_page = Mock()
        mock_page.extract_text.return_value = """
GABARITO ENEM 2024
Dia 1 - Caderno 1

1 C C 46 B
2 A A 47 D
3 E E 48 A
"""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        answers = self.parser.parse_answer_key("2024_GB_D1_CD1.pdf")
        
        assert len(answers) >= 4  # At least 4 answers parsed
        
        # Check first answer (English)
        eng_answers = [a for a in answers if a.language_option == LanguageOption.INGLES]
        assert len(eng_answers) > 0
        assert eng_answers[0].question_number == 1
        assert eng_answers[0].correct_answer == "C"

    @patch('pdfplumber.open')
    def test_parse_answer_key_empty_pdf(self, mock_pdfplumber):
        """Test answer key parsing with empty PDF."""
        mock_pdf = Mock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        answers = self.parser.parse_answer_key("2024_GB_D1_CD1.pdf")
        assert len(answers) == 0

    @patch('pdfplumber.open')
    def test_parse_questions_success(self, mock_pdfplumber):
        """Test successful question parsing."""
        # Mock PDF content with questions
        mock_page = Mock()
        mock_page.extract_text.return_value = """
ENEM 2024 - Caderno 1

QUESTÃO 1
Esta é uma questão de linguagens.

A) Primeira alternativa
B) Segunda alternativa  
C) Terceira alternativa
D) Quarta alternativa
E) Quinta alternativa

QUESTÃO 2
Esta é outra questão.

A) Opção A
B) Opção B
C) Opção C
D) Opção D
E) Opção E
"""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        questions = self.parser.parse_questions("2024_PV_D1_CD1.pdf")
        
        assert len(questions) == 2
        
        # Check first question
        q1 = questions[0]
        assert q1.number == 1
        assert "Esta é uma questão de linguagens" in q1.text
        assert len(q1.alternatives) == 5
        assert q1.alternatives[0].startswith("A)")
        assert q1.subject == Subject.LINGUAGENS

    @patch('pdfplumber.open')
    def test_parse_questions_empty_pdf(self, mock_pdfplumber):
        """Test question parsing with empty PDF."""
        mock_pdf = Mock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        questions = self.parser.parse_questions("2024_PV_D1_CD1.pdf")
        assert len(questions) == 0

    def test_parse_file_gabarito(self):
        """Test auto-detection of gabarito file."""
        with patch.object(self.parser, 'parse_answer_key') as mock_parse:
            mock_parse.return_value = []
            
            result = self.parser.parse_file("2024_GB_D1_CD1.pdf")
            
            assert result['type'] == ExamType.GABARITO
            assert 'data' in result
            assert 'metadata' in result
            mock_parse.assert_called_once()

    def test_parse_file_caderno(self):
        """Test auto-detection of caderno file."""
        with patch.object(self.parser, 'parse_questions') as mock_parse:
            mock_parse.return_value = []
            
            result = self.parser.parse_file("2024_PV_D1_CD1.pdf")
            
            assert result['type'] == ExamType.CADERNO_QUESTOES
            assert 'data' in result
            assert 'metadata' in result
            mock_parse.assert_called_once()

    def test_parse_file_unknown_type(self):
        """Test parsing unknown file type."""
        with pytest.raises(ValueError):
            self.parser.parse_file("2024_XX_D1_CD1.pdf")

    def test_question_pattern_matching(self):
        """Test question pattern regex."""
        text = "QUESTÃO 1\nTexto da questão\nQUESTÃO 42\nOutra questão"
        matches = list(self.parser.question_pattern.finditer(text))
        
        assert len(matches) == 2
        assert matches[0].group(1) == "1"
        assert matches[1].group(1) == "42"

    def test_alternative_pattern_matching(self):
        """Test alternative pattern regex."""
        text = """A) Primeira alternativa
B) Segunda alternativa com
   múltiplas linhas
C) Terceira
D) Quarta alternativa
E) Quinta alternativa"""
        
        matches = self.parser.alternative_pattern.findall(text)
        
        assert len(matches) == 5
        assert matches[0][0] == "A"
        assert "Primeira alternativa" in matches[0][1]
