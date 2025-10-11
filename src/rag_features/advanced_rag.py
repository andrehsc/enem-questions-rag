#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema RAG avançado para ENEM - Integração completa
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import numpy as np
from dataclasses import dataclass

from .semantic_search import EnemSemanticSearch
from .question_generator import EnemQuestionGenerator

logger = logging.getLogger(__name__)

@dataclass
class RAGContext:
    """Contexto para operações RAG"""
    query: str
    retrieved_questions: List[Dict[str, Any]]
    similarity_scores: List[float]
    metadata: Dict[str, Any]
    timestamp: str

# Instância global
advanced_rag = None

class AdvancedEnemRAG:
    """Sistema RAG avançado para questões ENEM"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.semantic_search = EnemSemanticSearch()
        self.question_generator = EnemQuestionGenerator(api_key=openai_api_key)
        self.context_cache = {}
        
    async def initialize(self):
        """Inicializa todos os componentes"""
        await self.semantic_search.initialize_collection()
        logger.info("Sistema RAG avançado inicializado")
    
    async def intelligent_search(
        self,
        query: str,
        search_type: str = "hybrid",
        n_results: int = 10,
        min_similarity: float = 0.7
    ) -> RAGContext:
        """Busca inteligente combinando diferentes estratégias"""
        context = RAGContext(
            query=query,
            retrieved_questions=[],
            similarity_scores=[],
            metadata={"search_type": search_type},
            timestamp=datetime.now().isoformat()
        )
        
        if search_type in ["semantic", "hybrid"]:
            semantic_results = await self.semantic_search.semantic_search(
                query=query,
                n_results=n_results
            )
            
            filtered_results = [
                r for r in semantic_results 
                if r["similarity_score"] >= min_similarity
            ]
            
            context.retrieved_questions.extend(filtered_results)
            context.similarity_scores.extend([r["similarity_score"] for r in filtered_results])
        
        return context
    
    async def generate_contextual_question(
        self,
        context: RAGContext,
        question_type: str = "multiple_choice",
        difficulty: str = "médio"
    ) -> Dict[str, Any]:
        """Gera questão baseada no contexto recuperado"""
        if not context.retrieved_questions:
            return {"error": "Nenhuma questão encontrada no contexto"}
        
        topic = f"Tema relacionado a: {context.query}"
        style_reference = context.retrieved_questions[0]
        
        generated_question = await self.question_generator.generate_question(
            topic=topic,
            question_type=question_type,
            difficulty=difficulty,
            style_reference=style_reference
        )
        
        if "error" not in generated_question:
            generated_question["rag_context"] = {
                "source_query": context.query,
                "reference_questions": len(context.retrieved_questions)
            }
        
        return generated_question
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema RAG"""
        semantic_stats = self.semantic_search.get_collection_stats()
        
        return {
            "semantic_search": semantic_stats,
            "cached_contexts": len(self.context_cache),
            "available_generators": self.question_generator.get_available_templates(),
            "system_health": "operational",
            "last_updated": datetime.now().isoformat()
        }

# Instância global atualizada
advanced_rag = AdvancedEnemRAG()
