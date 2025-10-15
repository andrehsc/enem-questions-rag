#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema RAG Aprimorado com ML para questões ENEM
Integra busca semântica + predição de dificuldade + classificação
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from semantic_search import create_semantic_search, SemanticSearchInterface
from ml_models.difficulty_predictor import EnemDifficultyPredictor
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedEnemRAG:
    """Sistema RAG aprimorado com capacidades de ML"""
    
    def __init__(self):
        self.semantic_search = None
        self.difficulty_predictor = None
        self._initialized = False
    
    async def initialize(self):
        """Inicializa todos os componentes"""
        if self._initialized:
            return
        
        try:
            logger.info("Inicializando Enhanced ENEM RAG System...")
            
            # Inicializar busca semântica
            self.semantic_search = create_semantic_search()
            await self.semantic_search.initialize()
            
            # Inicializar preditor de dificuldade
            self.difficulty_predictor = EnemDifficultyPredictor()
            
            self._initialized = True
            logger.info("Enhanced RAG System inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Enhanced RAG: {e}")
            raise
    
    async def search_with_ml_insights(self, 
                                    query: str, 
                                    limit: int = 5,
                                    predict_difficulty: bool = True,
                                    subject_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca questões com insights de ML
        
        Args:
            query: Consulta de busca
            limit: Número máximo de resultados
            predict_difficulty: Se deve predizer dificuldade
            subject_filter: Filtro por matéria
        
        Returns:
            Lista de questões com insights ML
        """
        if not self._initialized:
            await self.initialize()
        
        # Busca semântica base
        if subject_filter:
            results = await self.semantic_search.search_by_subject(query, subject_filter, limit)
        else:
            results = await self.semantic_search.search_questions(query, limit)
        
        # Enriquecer com ML insights
        enhanced_results = []
        for result in results:
            enhanced_result = result.copy()
            
            if predict_difficulty:
                try:
                    # Predizer dificuldade (mockado por enquanto)
                    predicted_difficulty = self._mock_predict_difficulty(result['text'])
                    enhanced_result['predicted_difficulty'] = predicted_difficulty
                    enhanced_result['difficulty_confidence'] = 0.75  # Mock confidence
                except Exception as e:
                    logger.warning(f"Erro na predição de dificuldade: {e}")
                    enhanced_result['predicted_difficulty'] = 'medio'
                    enhanced_result['difficulty_confidence'] = 0.0
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _mock_predict_difficulty(self, text: str) -> str:
        """Mock para predição de dificuldade até modelo ser treinado"""
        text_length = len(text.split())
        
        if text_length < 50:
            return 'facil'
        elif text_length > 100:
            return 'dificil' 
        else:
            return 'medio'
    
    async def add_questions_with_ml_features(self, questions: List[Dict[str, Any]]) -> bool:
        """Adiciona questões ao índice com features ML"""
        if not self._initialized:
            await self.initialize()
        
        # Enriquecer questões com features ML
        enriched_questions = []
        for question in questions:
            enriched = question.copy()
            
            # Adicionar predição de dificuldade se não existir
            if 'difficulty' not in enriched:
                enriched['difficulty'] = self._mock_predict_difficulty(enriched.get('text', ''))
            
            enriched_questions.append(enriched)
        
        # Indexar com busca semântica
        return await self.semantic_search.add_questions_to_index(enriched_questions)

# Função de teste
async def test_enhanced_rag():
    """Testa o sistema RAG aprimorado"""
    print("=== TESTE SISTEMA RAG APRIMORADO ===")
    
    rag = EnhancedEnemRAG()
    await rag.initialize()
    
    # Questões de exemplo
    sample_questions = [
        {
            "id": "enem_2023_phys_001",
            "text": "Uma partícula carregada move-se em um campo magnético uniforme. Considerando que a força magnética é sempre perpendicular à velocidade, qual será a trajetória da partícula?",
            "subject": "fisica",
            "year": 2023
        },
        {
            "id": "enem_2023_bio_001", 
            "text": "O que é fotossíntese?",
            "subject": "biologia",
            "year": 2023
        }
    ]
    
    # Indexar questões
    print("📚 Indexando questões com ML features...")
    await rag.add_questions_with_ml_features(sample_questions)
    
    # Buscar com insights ML
    queries = [
        "campo magnético",
        "processos biológicos"
    ]
    
    for query in queries:
        print(f"\n🔍 Busca ML: '{query}'")
        results = await rag.search_with_ml_insights(query, limit=2)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. [{result['id']}] Similaridade: {result['similarity']:.3f}")
            print(f"     Dificuldade Predita: {result.get('predicted_difficulty', 'N/A')}")
            print(f"     Confiança: {result.get('difficulty_confidence', 0):.2f}")
            print(f"     Matéria: {result['metadata'].get('subject', 'N/A')}")
    
    print("\n✅ Teste Enhanced RAG concluído!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_rag())