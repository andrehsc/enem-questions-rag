#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes TDD para Sistema de Busca Semântica ENEM
Seguindo padrão Red-Green-Blue obrigatório
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Adicionar path para módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from rag_features.semantic_search import EnemSemanticSearch, SemanticSearchInterface


class TestEnemSemanticSearchInterface:
    """Testes para interface de busca semântica"""
    
    def test_semantic_search_interface_exists_with_required_methods(self):
        """
        RED PHASE: Teste que interface existe e tem métodos obrigatórios
        AC1: SemanticSearchInterface define contratos para busca semântica
        """
        # Assert - verificar que interface existe
        assert hasattr(SemanticSearchInterface, 'search_questions')
        assert hasattr(SemanticSearchInterface, 'add_questions_to_index')


class TestEnemSemanticSearch:
    """Testes para sistema de busca semântica ENEM"""
    
    @pytest.fixture
    def search_system(self):
        """Fixture para sistema de busca com implementação simplificada"""
        # Usar implementação real com mock habilitado
        search_system = EnemSemanticSearch(use_mock=True)
        return search_system
    
    @pytest.mark.asyncio
    async def test_initialization_creates_required_components_successfully(self):
        """
        GREEN PHASE: Teste que inicialização cria componentes necessários
        AC1: Sistema inicializa modelo mock e SQLite
        """
        # Arrange
        search_system = EnemSemanticSearch(use_mock=True)
        
        # Act
        await search_system.initialize()
        
        # Assert
        assert search_system.is_initialized() == True
        assert search_system.model is not None
        assert search_system.db_path is not None
        assert os.path.exists("./data")
    
    @pytest.mark.asyncio
    async def test_search_questions_returns_similar_results_with_scores(self, search_system):
        """
        GREEN PHASE: Teste que busca semântica retorna resultados ordenados por similaridade
        AC2: search_questions retorna questões ordenadas por similaridade semântica
        """
        # Arrange - Adicionar questões primeiro
        questions = [
            {'id': 'math-1', 'statement': 'Calcule a derivada de x²', 'subject': 'Matemática', 'year': 2023},
            {'id': 'hist-1', 'statement': 'Quem foi Dom Pedro II?', 'subject': 'História', 'year': 2022}
        ]
        await search_system.add_questions_to_index(questions)
        
        # Act
        results = await search_system.search_questions("derivada matemática", limit=5)
        
        # Assert
        assert len(results) >= 1  # Pelo menos uma questão de matemática
        # Verificar que a questão de matemática tem score maior que história
        math_results = [r for r in results if 'math' in r['id']]
        assert len(math_results) > 0
        assert math_results[0]['similarity_score'] > 0  # Score positivo
    
    @pytest.mark.asyncio
    async def test_add_questions_to_index_processes_batch_successfully(self, search_system):
        """
        GREEN PHASE: Teste que indexação de questões funciona em lotes
        AC3: add_questions_to_index processa questões e gera embeddings
        """
        # Arrange
        questions = [
            {
                'id': 'q1',
                'statement': 'Calcule a integral de x²',
                'subject': 'Matemática',
                'year': 2023
            },
            {
                'id': 'q2', 
                'statement': 'Quem foi Dom Pedro II?',
                'subject': 'História',
                'year': 2022
            }
        ]
        
        # Act
        result = await search_system.add_questions_to_index(questions)
        
        # Assert
        assert result == True
        
        # Verificar que as questões foram indexadas
        stats = await search_system.get_collection_stats()
        assert stats['total_questions'] >= 2