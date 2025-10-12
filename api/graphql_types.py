#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphQL Types para ENEM Questions RAG API
Interface First Design - Definição de contratos GraphQL
"""

import strawberry
from typing import List, Optional
from datetime import datetime
import uuid


@strawberry.type
class HATEOASLinkType:
    """Tipo GraphQL para links HATEOAS"""
    rel: str
    href: str
    method: str


@strawberry.type
class QuestionAlternativeType:
    """Tipo GraphQL para alternativas das questões"""
    letter: str
    text: str
    is_correct: Optional[bool] = None


@strawberry.type
class ExamMetadataType:
    """Tipo GraphQL para metadados do exame"""
    id: str
    year: int
    day: int
    caderno: str
    application_type: str
    accessibility: bool


@strawberry.interface
class QuestionBaseInterface:
    """Interface base para questões - aplicando DRY"""
    id: str
    question_text: str
    subject: str
    year: int


@strawberry.type
class QuestionSummaryType:
    """Tipo GraphQL para resumo de questões com dados completos opcionais"""
    id: str
    question_text: str
    subject: str
    year: int
    has_images: Optional[bool] = None
    exam_metadata: Optional[ExamMetadataType] = None
    alternatives: Optional[List[QuestionAlternativeType]] = None


@strawberry.type
class QuestionType:
    """Tipo GraphQL principal para questões ENEM - herda campos base"""
    id: str
    question_text: str
    subject: str
    year: int
    has_images: bool
    parsing_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    exam_metadata: Optional[ExamMetadataType] = None
    alternatives: Optional[List[QuestionAlternativeType]] = None
    links: Optional[List[HATEOASLinkType]] = None


@strawberry.type
class PaginatedQuestionsType:
    """Tipo GraphQL para resultados paginados de questões"""
    items: List[QuestionSummaryType]
    total_count: int
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


@strawberry.type
class StatisticsType:
    """Tipo GraphQL para estatísticas do sistema"""
    total_questions: int
    total_exams: int
    years_available: List[int]
    subjects_available: List[str]


@strawberry.input
class QuestionFiltersInput:
    """
    Input GraphQL para filtros de questões ENEM
    
    Campos:
    - year: Filtrar por ano específico (ex: 2023)
    - subject: Filtrar por matéria (ex: "Matemática")
    - search: Busca textual no conteúdo da questão
    - has_images: Filtrar questões com/sem imagens
    - pdf_filename: Filtrar por arquivo PDF específico (ex: "2020_PV_impresso_D2_CD5.pdf")
    - caderno: Filtrar por caderno específico (ex: "CD5")
    - day: Filtrar por dia da prova (1 ou 2)
    """
    year: Optional[int] = None
    subject: Optional[str] = None
    search: Optional[str] = None
    has_images: Optional[bool] = None
    pdf_filename: Optional[str] = None
    caderno: Optional[str] = None
    day: Optional[int] = None


@strawberry.input
class PaginationInput:
    """
    Input GraphQL para paginação de resultados
    
    Campos:
    - limit: Número máximo de itens por página (padrão: 10)
    - offset: Número de itens para pular (padrão: 0)
    """
    limit: Optional[int] = 10
    offset: Optional[int] = 0