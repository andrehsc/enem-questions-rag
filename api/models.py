#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos Pydantic para API ENEM Questions
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ExamMetadata(BaseModel):
    """Metadados do exame"""
    id: UUID
    year: int
    day: int
    caderno: str
    application_type: str
    accessibility: Optional[str] = None
    file_type: str
    pdf_filename: str
    pdf_path: str
    file_size: Optional[int] = None
    pages_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class QuestionAlternative(BaseModel):
    """Alternativa de uma questão"""
    id: int
    letter: str
    text: str
    order: int

class AnswerKey(BaseModel):
    """Gabarito de uma questão"""
    id: int
    correct_answer: str
    subject: str
    language_option: Optional[str] = None

class Question(BaseModel):
    """Questão completa com alternativas e gabarito"""
    id: int
    exam_year: int
    exam_type: str
    number: int
    statement: str
    alternatives: List[QuestionAlternative]
    answer_key: Optional[AnswerKey] = None
    metadata: ExamMetadata

class QuestionSummary(BaseModel):
    """Resumo de uma questão para listagem"""
    id: int
    exam_year: int
    exam_type: str
    number: int
    subject: Optional[str]
    correct_answer: Optional[str]
    statement_preview: str

class PaginatedResponse(BaseModel):
    """Resposta paginada"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

class StatsResponse(BaseModel):
    """Estatísticas da base de dados"""
    total_questions: int
    total_alternatives: int
    total_answer_keys: int
    questions_by_year: Dict[int, int]
    questions_by_subject: Dict[str, int]
    answer_distribution: Dict[str, int]

class HealthResponse(BaseModel):
    """Resposta de health check"""
    status: str
    timestamp: datetime
    database_connected: bool
    total_questions: int
