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
            # Mapear filtros GraphQL para parâmetros do DatabaseService
            year = filters.year if filters else None
            subject = filters.subject if filters and filters.subject else None
            caderno = filters.caderno if filters and filters.caderno else None
            pdf_filename = filters.pdf_filename if filters and filters.pdf_filename else None
            day = filters.day if filters and filters.day else None
            search = filters.search if filters and filters.search else None
            has_images = filters.has_images if filters and filters.has_images is not None else None
            
            # O método retorna tupla (questions, total)
            questions_list, total_count = self._db_service.get_questions_summary(
                page=page,
                size=limit,
                year=year,
                subject=subject,
                caderno=caderno,
                pdf_filename=pdf_filename,
                day=day,
                search=search,
                has_images=has_images
            )
            
            # Converter para tipos GraphQL
            items = [
                self._convert_question_summary_to_graphql_type(dict(q))
                for q in questions_list
            ]
            
            # Calcular paginação
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_previous = page > 1
            
            return PaginatedQuestionsType(
                items=items,
                total_count=total_count,
                page=page,
                per_page=limit,
                has_next=has_next,
                has_previous=has_previous
            )
            
        except Exception as e:
            # Log do erro para debug
            print(f"GraphQL error in get_questions_paginated: {e}")
            # Fallback seguro
            return self._create_empty_paginated_response(limit)
    
    def _convert_question_to_graphql_type(self, question_data: Dict[str, Any]) -> QuestionType:
        """
        Converter dados do banco para tipo GraphQL QuestionType
        Responsabilidade única: transformação de dados
        """
        # Extrair dados da estrutura aninhada retornada por get_question_by_id
        question_info = question_data.get('question', {})
        
        # Buscar dados aninhados para nested queries
        exam_metadata = self._get_exam_metadata_for_question(question_data)
        alternatives = self._get_alternatives_for_question(question_data)
        hateoas_links = self._generate_hateoas_links(question_data)
        
        # Mapear campos do banco real para GraphQL
        return QuestionType(
            id=str(question_info.get('id', '')),
            question_text=question_info.get('statement', '') or question_info.get('question_text', ''),
            subject=self._clean_subject_name(question_info.get('subject', '')),
            year=question_info.get('year', 0),
            has_images=False,  # Campo não disponível no schema atual
            parsing_confidence=None,  # Campo não disponível no schema atual
            created_at=datetime.now(),  # Campo não disponível no schema atual
            updated_at=datetime.now(),  # Campo não disponível no schema atual
            exam_metadata=exam_metadata,
            alternatives=alternatives,
            links=hateoas_links
        )
    
    def _convert_question_summary_to_graphql_type(self, question_data: Dict[str, Any]) -> QuestionSummaryType:
        """
        Converter dados do banco para tipo GraphQL QuestionSummaryType
        Responsabilidade única: transformação de dados resumidos
        """
        # Metadados do exame se disponíveis
        exam_metadata = None
        if question_data.get('caderno') or question_data.get('day'):
            from graphql_types import ExamMetadataType
            exam_metadata = ExamMetadataType(
                id=f"exam-{question_data.get('year', 0)}",
                year=question_data.get('year', 0),
                day=question_data.get('day', 0),
                caderno=question_data.get('caderno', ''),
                application_type=question_data.get('application_type', 'regular'),
                accessibility=False  # Campo padrão
            )
        
        # Mapear campos do banco para GraphQL
        return QuestionSummaryType(
            id=str(question_data.get('id', '')),
            question_text=question_data.get('statement_preview', '') or question_data.get('question_text', ''),
            subject=self._clean_subject_name(question_data.get('subject', '')),
            year=question_data.get('year', 0),
            has_images=bool(question_data.get('has_images', False)),
            exam_metadata=exam_metadata,
            alternatives=None  # Não carregamos alternativas no summary por performance
        )
    
    def _clean_subject_name(self, subject: str) -> str:
        """Limpar nome da matéria para exibição"""
        if 'LINGUAGENS' in subject:
            return 'Linguagens'
        elif 'HUMANAS' in subject:
            return 'Ciências Humanas'
        elif 'NATUREZA' in subject:
            return 'Ciências da Natureza'
        elif 'MATEMATICA' in subject:
            return 'Matemática'
        else:
            return subject.replace('Subject.', '')
    
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
            # Usar dados reais do banco da estrutura aninhada
            question_info = question_data.get('question', {})
            year = question_info.get('year', 0)
            
            if year:
                return ExamMetadataType(
                    id=f"exam-{year}",
                    year=year,
                    day=question_info.get('day', 1),
                    caderno=question_info.get('caderno', 'AZUL'),
                    application_type=question_info.get('application_type', 'regular'),
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
            # Usar dados reais das alternativas da estrutura aninhada
            alternatives_data = question_data.get('alternatives', [])
            answer_key = question_data.get('answer_key', {})
            correct_answer = answer_key.get('correct_answer', '') if answer_key else ''
            
            if alternatives_data:
                alternatives = []
                for alt in alternatives_data:
                    alt_dict = dict(alt) if hasattr(alt, 'keys') else alt
                    is_correct = alt_dict.get('letter', '') == correct_answer
                    alternatives.append(QuestionAlternativeType(
                        letter=alt_dict.get('letter', ''),
                        text=alt_dict.get('text', ''),
                        is_correct=is_correct
                    ))
                return alternatives
        except Exception as e:
            print(f"Error getting alternatives: {e}")
            pass
        return None
    
    def _generate_hateoas_links(self, question_data: Dict[str, Any]) -> Optional[List[HATEOASLinkType]]:
        """
        Gerar links HATEOAS para nested query
        AC9: Response format maintains compatibility with HATEOAS links
        """
        try:
            question_info = question_data.get('question', {})
            question_id = question_info.get('id')
            if question_id:
                return [
                    HATEOASLinkType(
                        rel="self",
                        href=f"/questions/{question_id}",
                        method="GET"
                    ),
                    HATEOASLinkType(
                        rel="alternatives",
                        href=f"/questions/{question_id}/alternatives",
                        method="GET"
                    ),
                    HATEOASLinkType(
                        rel="exam",
                        href=f"/exams/{question_info.get('year', 0)}",
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
            
            # Mapear dados reais do banco
            years_available = list(stats_data.get('questions_by_year', {}).keys())
            subjects_available = list(stats_data.get('questions_by_subject', {}).keys())
            
            return StatisticsType(
                total_questions=stats_data.get('total_questions', 0),
                total_exams=len(years_available),  # Usar quantidade de anos como proxy
                years_available=years_available,
                subjects_available=subjects_available
            )
            
        except Exception as e:
            print(f"GraphQL error in get_global_statistics: {e}")
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