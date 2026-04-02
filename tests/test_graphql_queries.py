#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes TDD para GraphQL API - ENEM Questions RAG
Seguindo padrão Red-Green-Blue obrigatório
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, Mock
from datetime import datetime

# Adicionar path para API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from main import app


class TestGraphQLEndpoint:
    """Testes para endpoint GraphQL básico"""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste FastAPI"""
        return TestClient(app)
    
    def test_graphql_endpoint_exists_returns_graphql_response(self, client):
        """
        RED PHASE: Teste que endpoint /graphql existe e retorna resposta GraphQL
        AC1: GraphQL endpoint is available at `/graphql`
        """
        # Arrange
        graphql_query = {
            "query": """
                query {
                    __schema {
                        types {
                            name
                        }
                    }
                }
            """
        }
        
        # Act
        response = client.post("/graphql", json=graphql_query)
        
        # Assert
        assert response.status_code == 200
        assert "data" in response.json()
        assert "__schema" in response.json()["data"]
    
    def test_graphql_playground_accessible_returns_html_interface(self, client):
        """
        RED PHASE: Teste que GraphQL Playground está acessível
        AC6: GraphQL Playground or GraphiQL interface is available for testing
        """
        # Act
        response = client.get("/graphql")
        
        # Assert
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "GraphQL" in response.text


class TestGraphQLQuestionTypes:
    """Testes para tipos GraphQL de Question"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('database.DatabaseService.get_question_by_id')
    def test_question_type_query_single_question_returns_question_data(self, mock_get_question, client):
        """
        GREEN PHASE: Teste query de questão única com mock
        AC2: Schema supports queries for questions with flexible field selection
        """
        # Arrange - Mock database response (estrutura esperada pelo GraphQL service)
        mock_get_question.return_value = {
            'question': {
                'id': 'test-uuid-123',
                'statement': 'Questão teste para GraphQL',
                'subject': 'Matemática',
                'year': 2023
            }
        }
        
        graphql_query = {
            "query": """
                query {
                    question(id: "test-uuid-123") {
                        id
                        questionText
                        subject
                        year
                    }
                }
            """
        }
        
        # Act
        response = client.post("/graphql", json=graphql_query)
        
        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert "question" in data
        assert data["question"]["id"] == "test-uuid-123"
        assert data["question"]["subject"] == "Matemática"
        assert data["question"]["year"] == 2023
    
    @patch('database.DatabaseService.get_questions_summary')
    def test_questions_list_query_with_pagination_returns_paginated_results(self, mock_get_questions, client):
        """
        GREEN PHASE: Teste query de lista de questões com paginação
        AC4: Schema supports filtering (year, subject, search) and pagination
        """
        # Arrange - Mock database response
        mock_get_questions.return_value = {
            'items': [
                {
                    'id': 'uuid-1',
                    'question_text': 'Questão 1',
                    'subject': 'Matemática', 
                    'year': 2023
                }
            ],
            'total': 1,
            'has_next': False,
            'has_previous': False
        }
        
        graphql_query = {
            "query": """
                query {
                    questions(pagination: {limit: 10, offset: 0}) {
                        items {
                            id
                            questionText
                            subject
                        }
                        totalCount
                    }
                }
            """
        }
        
        # Act
        response = client.post("/graphql", json=graphql_query)
        
        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert "questions" in data
        assert "items" in data["questions"]
        assert "totalCount" in data["questions"]


class TestGraphQLStatistics:
    """Testes para queries de estatísticas GraphQL"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_statistics_query_returns_global_stats(self, client):
        """
        RED PHASE: Teste query de estatísticas globais
        AC5: Schema supports statistics queries (total questions, distribution by year/subject)
        """
        # Arrange
        graphql_query = {
            "query": """
                query {
                    statistics {
                        totalQuestions
                        totalExams
                        yearsAvailable
                        subjectsAvailable
                    }
                }
            """
        }
        
        # Act
        response = client.post("/graphql", json=graphql_query)
        
        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert "statistics" in data
        assert "totalQuestions" in data["statistics"]


class TestGraphQLNestedQueries:
    """Testes para queries aninhadas GraphQL"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('graphql_services.DatabaseService.get_question_by_id')
    def test_nested_question_with_metadata_returns_related_data(self, mock_get_question, client):
        """
        ENHANCED: Teste query aninhada completa com metadados e alternativas
        AC3: Schema supports nested queries (question with exam metadata and alternatives)
        """
        # Arrange - Mock database response (estrutura esperada pelo GraphQL service)
        mock_get_question.return_value = {
            'question': {
                'id': 'test-uuid-nested',
                'statement': 'Questão com metadados completos',
                'subject': 'História',
                'year': 2023
            },
            'caderno': 'CD1',
            'day': 1,
            'alternatives': [
                {'letter': 'A', 'text': 'Alternativa A'},
                {'letter': 'B', 'text': 'Alternativa B'},
                {'letter': 'C', 'text': 'Alternativa C'},
                {'letter': 'D', 'text': 'Alternativa D'},
                {'letter': 'E', 'text': 'Alternativa E'}
            ],
            'answer_key': {'correct_answer': 'B'}
        }
        
        graphql_query = {
            "query": """
                query {
                    question(id: "test-uuid-nested") {
                        id
                        questionText
                        subject
                        year
                        examMetadata {
                            id
                            year
                            day
                            caderno
                            applicationType
                            accessibility
                        }
                        alternatives {
                            letter
                            text
                            isCorrect
                        }
                        links {
                            rel
                            href
                            method
                        }
                    }
                }
            """
        }
        
        # Act
        response = client.post("/graphql", json=graphql_query)

        # Assert - ENHANCED: validação completa de nested queries
        assert response.status_code == 200
        data = response.json()["data"]
        question = data["question"]        # Validar campos básicos
        assert question["id"] == "test-uuid-nested"
        assert question["subject"] == "História"
        assert question["year"] == 2023
        
        # Validar nested exam metadata
        assert "examMetadata" in question
        exam_metadata = question["examMetadata"]
        assert exam_metadata["year"] == 2023
        assert exam_metadata["day"] == 1
        assert exam_metadata["caderno"] == "CD1"
        
        # Validar nested alternatives
        assert "alternatives" in question
        alternatives = question["alternatives"]
        assert len(alternatives) == 5
        assert alternatives[0]["letter"] == "A"
        assert alternatives[1]["isCorrect"] == True  # B é a correta
        
        # Validar HATEOAS links
        assert "links" in question
        links = question["links"]
        assert len(links) == 3
        assert any(link["rel"] == "self" for link in links)
        assert any(link["rel"] == "alternatives" for link in links)
        assert any(link["rel"] == "exam" for link in links)