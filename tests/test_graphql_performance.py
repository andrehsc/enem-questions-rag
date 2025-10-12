#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Tests para GraphQL API - ENEM Questions RAG
Validação de requisitos de performance
"""

import pytest
import time
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch
from datetime import datetime

# Adicionar path para API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from main import app


class TestGraphQLPerformance:
    """Testes de performance para GraphQL queries"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('database.DatabaseService.get_question_by_id')
    def test_single_question_query_performance_under_100ms(self, mock_get_question, client):
        """
        Performance Test: Query única deve responder em <100ms
        Quality Gate: maxTestExecutionTime: 100ms (BMad requirement)
        """
        # Arrange - Mock database response
        mock_get_question.return_value = {
            'id': 'perf-test-uuid',
            'question_text': 'Performance test question',
            'subject': 'Matemática',
            'year': 2023,
            'has_images': False,
            'parsing_confidence': 0.95,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        graphql_query = {
            "query": """
                query {
                    question(id: "perf-test-uuid") {
                        id
                        questionText
                        subject
                        year
                        examMetadata {
                            year
                            day
                        }
                        alternatives {
                            letter
                            text
                        }
                        links {
                            rel
                            href
                        }
                    }
                }
            """
        }
        
        # Act - Measure response time
        start_time = time.time()
        response = client.post("/graphql", json=graphql_query)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert response.status_code == 200
        assert response_time_ms < 100, f"Response time {response_time_ms:.2f}ms exceeds 100ms limit"
        print(f"✅ Single question query: {response_time_ms:.2f}ms")
    
    @patch('database.DatabaseService.get_questions_summary')
    def test_paginated_query_performance_under_200ms(self, mock_get_questions, client):
        """
        Performance Test: Query paginada deve responder em <200ms
        Load Test: Simula resposta com múltiplos itens
        """
        # Arrange - Mock large dataset response
        mock_items = [
            {
                'id': f'perf-uuid-{i}',
                'question_text': f'Performance question {i}',
                'subject': 'Matemática' if i % 2 == 0 else 'Português',
                'year': 2023
            }
            for i in range(50)  # Simular 50 questões
        ]
        
        mock_get_questions.return_value = {
            'items': mock_items,
            'total': 1000,
            'has_next': True,
            'has_previous': False
        }
        
        graphql_query = {
            "query": """
                query {
                    questions(pagination: {limit: 50, offset: 0}) {
                        items {
                            id
                            questionText
                            subject
                            year
                        }
                        totalCount
                        hasNext
                        hasPrevious
                    }
                }
            """
        }
        
        # Act - Measure response time
        start_time = time.time()
        response = client.post("/graphql", json=graphql_query)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert response.status_code == 200
        assert response_time_ms < 200, f"Response time {response_time_ms:.2f}ms exceeds 200ms limit"
        assert len(response.json()["data"]["questions"]["items"]) == 50
        print(f"✅ Paginated query (50 items): {response_time_ms:.2f}ms")
    
    def test_schema_introspection_performance_under_150ms(self, client):
        """
        Performance Test: Schema introspection deve responder em <150ms
        GraphQL Playground dependency test
        """
        graphql_query = {
            "query": """
                query {
                    __schema {
                        types {
                            name
                            fields {
                                name
                                type {
                                    name
                                }
                            }
                        }
                    }
                }
            """
        }
        
        # Act - Measure response time
        start_time = time.time()
        response = client.post("/graphql", json=graphql_query)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert response.status_code == 200
        assert response_time_ms < 150, f"Schema introspection {response_time_ms:.2f}ms exceeds 150ms limit"
        
        schema_data = response.json()["data"]["__schema"]
        types_count = len(schema_data["types"])
        print(f"✅ Schema introspection ({types_count} types): {response_time_ms:.2f}ms")
    
    @patch('database.DatabaseService.get_stats')
    def test_statistics_query_performance_under_100ms(self, mock_get_stats, client):
        """
        Performance Test: Statistics query deve responder em <100ms
        Dashboard dependency test
        """
        # Arrange - Mock statistics response
        mock_get_stats.return_value = {
            'total_questions': 2532,
            'total_exams': 45,
            'years_available': list(range(2009, 2024)),
            'subjects_available': ['Matemática', 'Português', 'História', 'Geografia', 'Física', 'Química', 'Biologia']
        }
        
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
        
        # Act - Measure response time
        start_time = time.time()
        response = client.post("/graphql", json=graphql_query)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert response.status_code == 200
        assert response_time_ms < 100, f"Statistics query {response_time_ms:.2f}ms exceeds 100ms limit"
        
        stats = response.json()["data"]["statistics"]
        assert stats["totalQuestions"] == 2532
        assert len(stats["yearsAvailable"]) == 15
        print(f"✅ Statistics query: {response_time_ms:.2f}ms")
    
    def test_concurrent_requests_load_simulation(self, client):
        """
        Load Test: Simular múltiplas requisições concorrentes
        Stress test para verificar degradação de performance
        """
        import threading
        
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.post("/graphql", json={
                "query": "query { __schema { types { name } } }"
            })
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time_ms': (end_time - start_time) * 1000
            })
        
        # Simular 10 requisições concorrentes
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Aguardar todas as threads
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(results) == 10
        assert all(r['status_code'] == 200 for r in results)
        
        avg_response_time = sum(r['response_time_ms'] for r in results) / len(results)
        max_response_time = max(r['response_time_ms'] for r in results)
        
        assert avg_response_time < 200, f"Average response time {avg_response_time:.2f}ms too high"
        assert max_response_time < 500, f"Max response time {max_response_time:.2f}ms too high"
        
        print(f"✅ Concurrent load test (10 requests):")
        print(f"   Average: {avg_response_time:.2f}ms")
        print(f"   Maximum: {max_response_time:.2f}ms")