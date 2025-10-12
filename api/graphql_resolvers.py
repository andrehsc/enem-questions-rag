#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphQL Resolvers para ENEM Questions RAG API
BLUE PHASE: Refatorado com princípios SOLID, DRY, DIP
"""

import strawberry
from typing import Optional

from graphql_types import (
    QuestionType, PaginatedQuestionsType, StatisticsType,
    QuestionFiltersInput, PaginationInput
)
from graphql_services import (
    GraphQLQuestionService, GraphQLStatisticsService,
    QuestionServiceInterface, StatisticsServiceInterface
)


class GraphQLResolverContext:
    """
    Context para injeção de dependências nos resolvers
    Aplica Dependency Inversion Principle (DIP)
    """
    
    def __init__(
        self,
        question_service: QuestionServiceInterface = None,
        statistics_service: StatisticsServiceInterface = None
    ):
        # Dependency Injection com defaults
        self.question_service = question_service or GraphQLQuestionService()
        self.statistics_service = statistics_service or GraphQLStatisticsService()


# Instância global do contexto (pode ser injetada nos testes)
_resolver_context = GraphQLResolverContext()


@strawberry.type
class Query:
    """
    Root Query GraphQL - BLUE PHASE Refatorado
    Responsabilidade única: coordenar chamadas para serviços especializados
    """
    
    @strawberry.field
    def question(self, id: str) -> Optional[QuestionType]:
        """
        Resolver para questão única por ID
        AC2: Schema supports queries for questions with flexible field selection
        
        BLUE PHASE: Delegado para serviço especializado
        """
        return _resolver_context.question_service.get_question_by_id(id)
    
    @strawberry.field
    def questions(
        self, 
        filters: Optional[QuestionFiltersInput] = None,
        pagination: Optional[PaginationInput] = None
    ) -> PaginatedQuestionsType:
        """
        Resolver para lista de questões com paginação
        AC4: Schema supports filtering (year, subject, search) and pagination
        
        BLUE PHASE: Delegado para serviço especializado
        """
        return _resolver_context.question_service.get_questions_paginated(filters, pagination)
    
    @strawberry.field
    def statistics(self) -> StatisticsType:
        """
        Resolver para estatísticas globais
        AC5: Schema supports statistics queries (total questions, distribution by year/subject)
        
        BLUE PHASE: Delegado para serviço especializado
        """
        return _resolver_context.statistics_service.get_global_statistics()


def set_resolver_context(context: GraphQLResolverContext) -> None:
    """
    Setter para injeção de contexto nos testes
    Permite mockagem das dependências
    """
    global _resolver_context
    _resolver_context = context


# Schema GraphQL
schema = strawberry.Schema(query=Query)