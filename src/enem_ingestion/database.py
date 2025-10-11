"""Database models and connection management for ENEM questions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    create_engine,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
import uuid

from .config import settings

Base = declarative_base()


class ExamYear(Base):
    """Tabela para armazenar anos de provas do ENEM."""

    __tablename__ = "exam_years"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, unique=True, nullable=False, index=True)
    application_type = Column(String(50))  # Regular, PPL, Digital, etc.
    download_url = Column(String(500))
    file_path = Column(String(500))
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = relationship("Question", back_populates="exam_year")


class Subject(Base):
    """Tabela para disciplinas/áreas do conhecimento."""

    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # Matemática, Linguagens, etc.
    code = Column(String(10), unique=True)  # MT, LC, CN, CH
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    questions = relationship("Question", back_populates="subject")


class Question(Base):
    """Tabela principal para questões do ENEM."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Foreign keys
    exam_year_id = Column(Integer, ForeignKey("exam_years.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    
    # Question data
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    context_text = Column(Text)  # Texto de apoio/contexto
    image_paths = Column(Text)  # JSON array of image paths
    
    # Metadata
    difficulty_level = Column(String(20))  # Estimado: Fácil, Médio, Difícil
    topics = Column(Text)  # JSON array of topics/tags
    
    # For RAG/Semantic Kernel future integration
    embedding_vector = Column(Text)  # JSON array of floats for embeddings
    indexed_for_search = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exam_year = relationship("ExamYear", back_populates="questions")
    subject = relationship("Subject", back_populates="questions")
    alternatives = relationship("Alternative", back_populates="question", cascade="all, delete-orphan")
    answer_key = relationship("AnswerKey", back_populates="question", uselist=False)

    # Indexes
    __table_args__ = (
        Index("idx_question_year_subject", "exam_year_id", "subject_id"),
        Index("idx_question_number_year", "question_number", "exam_year_id"),
    )


class Alternative(Base):
    """Tabela para alternativas das questões."""

    __tablename__ = "alternatives"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    
    letter = Column(String(1), nullable=False)  # A, B, C, D, E
    text = Column(Text, nullable=False)
    image_paths = Column(Text)  # JSON array of image paths
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    question = relationship("Question", back_populates="alternatives")

    # Indexes
    __table_args__ = (
        Index("idx_alternative_question", "question_id", "letter"),
    )


class AnswerKey(Base):
    """Tabela para gabaritos das questões."""

    __tablename__ = "answer_keys"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    
    correct_alternative = Column(String(1), nullable=False)  # A, B, C, D, E
    explanation = Column(Text)  # Explicação da resposta (se disponível)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    question = relationship("Question", back_populates="answer_key")


class ProcessingLog(Base):
    """Log de processamento para auditoria."""

    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True)
    operation = Column(String(50), nullable=False)  # download, parse, insert
    exam_year = Column(Integer)
    status = Column(String(20), nullable=False)  # success, error, warning
    message = Column(Text)
    details = Column(Text)  # JSON com detalhes técnicos
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_log_operation_status", "operation", "status"),
        Index("idx_log_created_at", "created_at"),
    )


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def drop_tables(self):
        """Drop all tables (for testing purposes)."""
        Base.metadata.drop_all(bind=self.engine)