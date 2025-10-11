"""Tests for database models and operations."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from enem_ingestion.database import Base, DatabaseManager, ExamYear, Subject, Question


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_database_manager_creation():
    """Test DatabaseManager initialization."""
    db_manager = DatabaseManager("sqlite:///:memory:")
    assert db_manager.database_url == "sqlite:///:memory:"
    assert db_manager.engine is not None
    assert db_manager.SessionLocal is not None


def test_exam_year_model(test_db):
    """Test ExamYear model."""
    exam_year = ExamYear(year=2024, application_type="Regular")
    test_db.add(exam_year)
    test_db.commit()
    
    retrieved = test_db.query(ExamYear).filter_by(year=2024).first()
    assert retrieved is not None
    assert retrieved.year == 2024
    assert retrieved.application_type == "Regular"


def test_subject_model(test_db):
    """Test Subject model."""
    subject = Subject(name="Matemática", code="MT")
    test_db.add(subject)
    test_db.commit()
    
    retrieved = test_db.query(Subject).filter_by(code="MT").first()
    assert retrieved is not None
    assert retrieved.name == "Matemática"
    assert retrieved.code == "MT"


def test_question_model_relationships(test_db):
    """Test Question model with relationships."""
    # Create related objects
    exam_year = ExamYear(year=2024, application_type="Regular")
    subject = Subject(name="Matemática", code="MT")
    test_db.add(exam_year)
    test_db.add(subject)
    test_db.flush()  # Get IDs
    
    # Create question
    question = Question(
        exam_year_id=exam_year.id,
        subject_id=subject.id,
        question_number=1,
        question_text="Qual é o resultado de 2 + 2?",
    )
    test_db.add(question)
    test_db.commit()
    
    # Test relationships
    retrieved = test_db.query(Question).first()
    assert retrieved is not None
    assert retrieved.exam_year.year == 2024
    assert retrieved.subject.name == "Matemática"