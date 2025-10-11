"""Tests for database integration module."""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from src.enem_ingestion.db_integration import DatabaseIntegration
from src.enem_ingestion.parser import (
    QuestionMetadata, AnswerKey, Question, ExamType, Subject, LanguageOption
)


@pytest.fixture
def db_integration():
    """Create DatabaseIntegration instance for testing."""
    # Use test database URL if available, otherwise skip tests
    test_db_url = os.getenv('TEST_DATABASE_URL') or os.getenv('DATABASE_URL')
    if not test_db_url:
        pytest.skip("No database URL available for testing")
    
    return DatabaseIntegration(test_db_url)


@pytest.fixture
def sample_metadata():
    """Create sample question metadata."""
    return QuestionMetadata(
        year=2024,
        day=1,
        caderno="CD1",
        application_type="regular",
        accessibility=None
    )


@pytest.fixture
def sample_answer_keys():
    """Create sample answer keys."""
    return [
        AnswerKey(
            question_number=1,
            correct_answer="A",
            language_option=LanguageOption.INGLES,
            subject=Subject.LINGUAGENS
        ),
        AnswerKey(
            question_number=1,
            correct_answer="B",
            language_option=LanguageOption.ESPANHOL,
            subject=Subject.LINGUAGENS
        ),
        AnswerKey(
            question_number=46,
            correct_answer="C",
            subject=Subject.CIENCIAS_HUMANAS
        )
    ]


@pytest.fixture
def sample_questions():
    """Create sample questions."""
    return [
        Question(
            number=1,
            text="Esta é uma questão de linguagens sobre inglês.",
            alternatives=[
                "A) Primeira alternativa",
                "B) Segunda alternativa",
                "C) Terceira alternativa",
                "D) Quarta alternativa",
                "E) Quinta alternativa"
            ],
            metadata=QuestionMetadata(
                year=2024, day=1, caderno="CD1",
                application_type="regular", accessibility=None
            ),
            subject=Subject.LINGUAGENS
        ),
        Question(
            number=2,
            text="Esta é outra questão de linguagens.",
            alternatives=[
                "A) Opção A",
                "B) Opção B",
                "C) Opção C",
                "D) Opção D",
                "E) Opção E"
            ],
            metadata=QuestionMetadata(
                year=2024, day=1, caderno="CD1",
                application_type="regular", accessibility=None
            ),
            subject=Subject.LINGUAGENS
        )
    ]


class TestDatabaseIntegration:
    """Test cases for DatabaseIntegration."""

    def test_initialization_with_url(self):
        """Test initialization with connection URL."""
        db = DatabaseIntegration("postgresql://test:test@localhost/test")
        assert db.connection_url == "postgresql://test:test@localhost/test"
        assert db.parser is not None

    def test_initialization_without_url(self):
        """Test initialization without URL raises error when no env var."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL not found"):
                DatabaseIntegration()

    def test_initialization_with_env_var(self):
        """Test initialization with DATABASE_URL from environment."""
        test_url = "postgresql://env:env@localhost/env"
        with patch.dict(os.environ, {'DATABASE_URL': test_url}):
            db = DatabaseIntegration()
            assert db.connection_url == test_url

    def test_connection_available(self, db_integration):
        """Test that database connection works."""
        assert db_integration.test_connection()

    def test_insert_exam_metadata(self, db_integration, sample_metadata):
        """Test inserting exam metadata."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            metadata_id = db_integration.insert_exam_metadata(
                sample_metadata, tmp_path, ExamType.GABARITO
            )
            
            assert metadata_id is not None
            assert len(metadata_id) > 0
            
            # Test duplicate insertion
            metadata_id2 = db_integration.insert_exam_metadata(
                sample_metadata, tmp_path, ExamType.GABARITO
            )
            
            assert metadata_id == metadata_id2  # Should return same ID
            
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_insert_answer_keys(self, db_integration, sample_metadata, sample_answer_keys):
        """Test inserting answer keys."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            # First insert metadata
            metadata_id = db_integration.insert_exam_metadata(
                sample_metadata, tmp_path, ExamType.GABARITO
            )
            
            # Insert answer keys
            count = db_integration.insert_answer_keys(sample_answer_keys, metadata_id)
            
            assert count == len(sample_answer_keys)
            
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_insert_questions(self, db_integration, sample_metadata, sample_questions):
        """Test inserting questions and alternatives."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            # First insert metadata
            metadata_id = db_integration.insert_exam_metadata(
                sample_metadata, tmp_path, ExamType.CADERNO_QUESTOES
            )
            
            # Insert questions
            count = db_integration.insert_questions(sample_questions, metadata_id)
            
            assert count == len(sample_questions)
            
        finally:
            tmp_path.unlink(missing_ok=True)

    @patch('src.enem_ingestion.db_integration.EnemPDFParser')
    def test_process_pdf_file_gabarito(self, mock_parser_class, db_integration, 
                                     sample_metadata, sample_answer_keys):
        """Test processing a gabarito PDF file."""
        # Setup mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        db_integration.parser = mock_parser
        
        mock_parser.parse_file.return_value = {
            'type': ExamType.GABARITO,
            'data': sample_answer_keys,
            'metadata': sample_metadata
        }
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            result = db_integration.process_pdf_file(tmp_path)
            
            assert result['success'] is True
            assert result['file_type'] == 'gabarito'
            assert 'answer_keys_inserted' in result
            assert result['answer_keys_inserted'] == len(sample_answer_keys)
            
        finally:
            tmp_path.unlink(missing_ok=True)

    @patch('src.enem_ingestion.db_integration.EnemPDFParser')
    def test_process_pdf_file_caderno(self, mock_parser_class, db_integration,
                                    sample_metadata, sample_questions):
        """Test processing a caderno PDF file."""
        # Setup mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        db_integration.parser = mock_parser
        
        mock_parser.parse_file.return_value = {
            'type': ExamType.CADERNO_QUESTOES,
            'data': sample_questions,
            'metadata': sample_metadata
        }
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            result = db_integration.process_pdf_file(tmp_path)
            
            assert result['success'] is True
            assert result['file_type'] == 'caderno_questoes'
            assert 'questions_inserted' in result
            assert result['questions_inserted'] == len(sample_questions)
            
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_get_statistics(self, db_integration):
        """Test getting database statistics."""
        stats = db_integration.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_exams' in stats
        assert 'total_questions' in stats
        assert 'total_alternatives' in stats

    def test_search_questions_empty_db(self, db_integration):
        """Test searching questions in empty database."""
        results = db_integration.search_questions("matemática")
        
        assert isinstance(results, list)
        assert len(results) == 0

    @patch('src.enem_ingestion.db_integration.EnemPDFParser')
    def test_process_directory(self, mock_parser_class, db_integration):
        """Test processing a directory of PDF files."""
        # Setup mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        db_integration.parser = mock_parser
        
        mock_parser.parse_file.return_value = {
            'type': ExamType.GABARITO,
            'data': [],
            'metadata': QuestionMetadata(
                year=2024, day=1, caderno="CD1",
                application_type="regular", accessibility=None
            )
        }
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test PDF files
            (tmp_path / "test1.pdf").touch()
            (tmp_path / "test2.pdf").touch()
            
            result = db_integration.process_directory(tmp_path)
            
            assert result['total_files'] == 2
            assert result['processed_files'] == 2
            assert isinstance(result['file_results'], list)
            assert len(result['file_results']) == 2