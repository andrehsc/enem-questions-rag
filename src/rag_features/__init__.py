#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo RAG Features - Sistema avançado de RAG para questões ENEM

Este módulo contém funcionalidades avançadas para:
- Busca semântica usando embeddings
- Geração de questões com LLM
- Sistema RAG integrado
- Análise e insights de dados
"""

from .semantic_search import EnemSemanticSearch, SemanticSearchInterface, PgVectorSearch, get_semantic_search
# from .question_generator import EnemQuestionGenerator, question_generator
# from .advanced_rag import AdvancedEnemRAG, advanced_rag, RAGContext
# from .analytics import EnemAnalytics, analytics

__version__ = "1.0.0"
__author__ = "ENEM RAG System"

# Interfaces principais do módulo
__all__ = [
    # Classes principais
    "EnemSemanticSearch",
    "EnemQuestionGenerator", 
    "AdvancedEnemRAG",
    "EnemAnalytics",
    "RAGContext",
    
    # Instâncias globais prontas para uso
    "semantic_search",
    "question_generator",
    "advanced_rag",
    "analytics"
]

# Configurações padrão do módulo
DEFAULT_CONFIG = {
    "embedding_model": "neuralmind/bert-base-portuguese-cased",
    "llm_model": "gpt-4-turbo-preview",
    "cache_ttl": 3600,  # 1 hora
    "max_search_results": 20,
    "min_similarity_threshold": 0.7,
    "default_language": "pt-BR"
}

def get_module_info():
    """Retorna informações sobre o módulo RAG Features"""
    return {
        "name": "ENEM RAG Features",
        "version": __version__,
        "components": {
            "semantic_search": "Busca semântica com embeddings",
            "question_generator": "Geração de questões com LLM",
            "advanced_rag": "Sistema RAG integrado",
            "analytics": "Análise e insights de dados"
        },
        "dependencies": [
            "sentence-transformers",
            "chromadb", 
            "openai",
            "pandas",
            "numpy",
            "scikit-learn"
        ],
        "features": [
            "Busca semântica em português",
            "Geração contextual de questões",
            "Clustering automático",
            "Análise de padrões",
            "Relatórios de insights",
            "Cache inteligente"
        ]
    }

def initialize_all_components(openai_api_key=None):
    """
    Inicializa todos os componentes do sistema RAG
    
    Args:
        openai_api_key: Chave da API OpenAI (opcional)
    
    Returns:
        dict: Status de inicialização dos componentes
    """
    import asyncio
    
    async def _initialize():
        status = {}
        
        try:
            # Inicializar busca semântica
            await semantic_search.initialize_collection()
            status["semantic_search"] = "initialized"
        except Exception as e:
            status["semantic_search"] = f"error: {str(e)}"
        
        try:
            # Inicializar RAG avançado
            if openai_api_key:
                advanced_rag.question_generator.api_key = openai_api_key
            await advanced_rag.initialize()
            status["advanced_rag"] = "initialized"
        except Exception as e:
            status["advanced_rag"] = f"error: {str(e)}"
        
        # Analytics não precisa de inicialização assíncrona
        status["analytics"] = "ready"
        
        return status
    
    return asyncio.run(_initialize())

def quick_start_guide():
    """Retorna guia rápido de uso do módulo"""
    return """
    === ENEM RAG Features - Guia Rápido ===
    
    1. Busca Semântica:
       from src.rag_features import semantic_search
       results = await semantic_search.semantic_search("física quântica")
    
    2. Geração de Questões:
       from src.rag_features import question_generator
       question = await question_generator.generate_question(
           topic="matemática", 
           difficulty="médio"
       )
    
    3. Sistema RAG Completo:
       from src.rag_features import advanced_rag
       await advanced_rag.initialize()
       context = await advanced_rag.intelligent_search("trigonometria")
       new_question = await advanced_rag.generate_contextual_question(context)
    
    4. Análise de Dados:
       from src.rag_features import analytics
       report = analytics.generate_insights_report(questions_list)
    
    5. Inicialização Completa:
       from src.rag_features import initialize_all_components
       status = initialize_all_components(openai_api_key="sua_chave")
    """
