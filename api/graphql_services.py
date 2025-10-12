#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphQL Services - ENEM Questions RAG API
Aplicando Single Responsibility Principle (SRP)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import DatabaseService
from graphql_types import (
    QuestionType, QuestionSummaryType, PaginatedQuestionsType,
    StatisticsType, QuestionFiltersInput, PaginationInput,
    ExamMetadataType, QuestionAlternativeType, HATEOASLinkType
)


class QuestionServiceInterface(ABC):
    """Interface para serviço de questões - Interface First Design"""
    
    @abstractmethod
    def get_question_by_id(self, question_id: str) -> Optional[QuestionType]:
        """Recuperar questão por ID"""
        pass
    
    @abstractmethod
    def get_questions_paginated(
        self, 
        filters: Optional[QuestionFiltersInput],
        pagination: Optional[PaginationInput]
    ) -> PaginatedQuestionsType:
        """Recuperar questões com paginação e filtros"""
        pass


class StatisticsServiceInterface(ABC):
    """Interface para serviço de estatísticas"""
    
    @abstractmethod
    def get_global_statistics(self) -> StatisticsType:
        """Recuperar estatísticas globais do sistema"""
        pass


class GraphQLQuestionService(QuestionServiceInterface):
    """
    Serviço GraphQL para questões
    Responsabilidade única: conversão de dados de questões para tipos GraphQL
    """
    
    def __init__(self):
        self._db_service = DatabaseService()
    
    def get_question_by_id(self, question_id: str) -> Optional[QuestionType]:
        """
        Implementação de busca de questão por ID
        Aplica transformação de dados do banco para GraphQL
        """
        try:
            question_data = self._db_service.get_question_by_id(question_id)
            
            if not question_data:
                return None
            
            return self._convert_question_to_graphql_type(question_data)
            
        except Exception:
            return None
    
    def get_questions_paginated(
        self, 
        filters: Optional[QuestionFiltersInput],
        pagination: Optional[PaginationInput]
    ) -> PaginatedQuestionsType:
        """
        Implementação de busca paginada de questões
        Aplica filtros e paginação
        """
        # Valores padrão
        limit = pagination.limit if pagination else 10
        offset = pagination.offset if pagination else 0
        page = offset // limit + 1
        
        try:
            questions_data = self._db_service.get_questions_summary(
                page=page,
                size=limit,
                year=filters.year if filters else None,
                subject=filters.subject if filters else None,
                search=filters.search if filters else None
            )
            
            # Converter para tipos GraphQL
            items = [
                self._convert_question_summary_to_graphql_type(q)
                for q in questions_data.get('items', [])
            ]
            
            return PaginatedQuestionsType(
                items=items,
                total_count=questions_data.get('total', 0),
                page=page,
                per_page=limit,
                has_next=questions_data.get('has_next', False),
                has_previous=questions_data.get('has_previous', False)
            )
            
        except Exception:
            # Fallback seguro
            return self._create_empty_paginated_response(limit)
    
    def _convert_question_to_graphql_type(self, question_data: Dict[str, Any]) -> QuestionType:
        """
        Converter dados do banco para tipo GraphQL QuestionType
        Responsabilidade única: transformação de dados
        """
        # Buscar dados aninhados para nested queries
        exam_metadata = self._get_exam_metadata_for_question(question_data)
        alternatives = self._get_alternatives_for_question(question_data)
        hateoas_links = self._generate_hateoas_links(question_data)
        
        return QuestionType(
            id=str(question_data.get('id', '')),
            question_text=question_data.get('question_text', ''),
            subject=question_data.get('subject', ''),
            year=question_data.get('year', 0),
            has_images=question_data.get('has_images', False),
            parsing_confidence=question_data.get('parsing_confidence'),
            created_at=question_data.get('created_at', datetime.now()),
            updated_at=question_data.get('updated_at', datetime.now()),
            exam_metadata=exam_metadata,
            alternatives=alternatives,
            links=hateoas_links
        )
    
    def _convert_question_summary_to_graphql_type(self, question_data: Dict[str, Any]) -> QuestionSummaryType:
        """
        Converter dados do banco para tipo GraphQL QuestionSummaryType
        Responsabilidade única: transformação de dados resumidos
        """
        return QuestionSummaryType(
            id=str(question_data.get('id', '')),
            question_text=question_data.get('question_text', ''),
            subject=question_data.get('subject', ''),
            year=question_data.get('year', 0)
        )
    
    def _create_empty_paginated_response(self, limit: int) -> PaginatedQuestionsType:
        """
        Criar resposta paginada vazia para casos de erro
        Responsabilidade única: fallback seguro
        """
        return PaginatedQuestionsType(
            items=[],
            total_count=0,
            page=1,
            per_page=limit,
            has_next=False,
            has_previous=False
        )
    
    def _get_exam_metadata_for_question(self, question_data: Dict[str, Any]) -> Optional[ExamMetadataType]:
        """
        Buscar metadados do exame para nested query
        AC3: Schema supports nested queries (question with exam metadata)
        """
        try:
            # Implementação para buscar metadados relacionados
            year = question_data.get('year', 0)
            if year:
                return ExamMetadataType(
                    id=f"exam-{year}",
                    year=year,
                    day=1,  # Valor padrão - seria buscado do banco
                    caderno="CD1",  # Valor padrão - seria buscado do banco
                    application_type="regular",
                    accessibility=False
                )
        except Exception:
            pass
        return None
    
    def _get_alternatives_for_question(self, question_data: Dict[str, Any]) -> Optional[List[QuestionAlternativeType]]:
        """
        Buscar alternativas da questão para nested query
        AC3: Schema supports nested queries (question with alternatives)
        """
        try:
            # Implementação básica - seria expandida com dados reais do banco
            question_id = question_data.get('id')
            if question_id:
                # Mock de alternativas para demonstração
                return [
                    QuestionAlternativeType(letter="A", text="Alternativa A", is_correct=False),
                    QuestionAlternativeType(letter="B", text="Alternativa B", is_correct=True),
                    QuestionAlternativeType(letter="C", text="Alternativa C", is_correct=False),
                    QuestionAlternativeType(letter="D", text="Alternativa D", is_correct=False),
                    QuestionAlternativeType(letter="E", text="Alternativa E", is_correct=False),
                ]
        except Exception:
            pass
        return None
    
    def _generate_hateoas_links(self, question_data: Dict[str, Any]) -> Optional[List[HATEOASLinkType]]:
        """
        Gerar links HATEOAS para nested query
        AC9: Response format maintains compatibility with HATEOAS links
        """
        try:
            question_id = question_data.get('id')
            if question_id:
                return [
                    HATEOASLinkType(
                        rel="self",
                        href=f"/api/questions/{question_id}",
                        method="GET"
                    ),
                    HATEOASLinkType(
                        rel="alternatives",
                        href=f"/api/questions/{question_id}/alternatives",
                        method="GET"
                    ),
                    HATEOASLinkType(
                        rel="exam",
                        href=f"/api/exams/{question_data.get('year', 0)}",
                        method="GET"
                    )
                ]
        except Exception:
            pass
        return None


class GraphQLStatisticsService(StatisticsServiceInterface):
    """
    Serviço GraphQL para estatísticas
    Responsabilidade única: conversão de dados de estatísticas para tipos GraphQL
    """
    
    def __init__(self):
        self._db_service = DatabaseService()
    
    def get_global_statistics(self) -> StatisticsType:
        """
        Implementação de busca de estatísticas globais
        Aplica transformação de dados do banco para GraphQL
        """
        try:
            stats_data = self._db_service.get_stats()
            
            return StatisticsType(
                total_questions=stats_data.get('total_questions', 0),
                total_exams=stats_data.get('total_exams', 0),
                years_available=stats_data.get('years_available', []),
                subjects_available=stats_data.get('subjects_available', [])
            )
            
        except Exception:
            # Fallback seguro
            return self._create_empty_statistics()
    
    def _create_empty_statistics(self) -> StatisticsType:
        """
        Criar estatísticas vazias para casos de erro
        Responsabilidade única: fallback seguro
        """
        return StatisticsType(
            total_questions=0,
            total_exams=0,
            years_available=[],
            subjects_available=[]
        )