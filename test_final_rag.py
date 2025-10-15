#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('src')

from rag_features.enhanced_rag_system import EnhancedEnemRAG

async def final_test():
    print('TESTE FINAL - Sistema RAG + ML Completo')
    print('=' * 50)
    
    # Inicializar sistema
    rag = EnhancedEnemRAG()
    await rag.initialize()
    print('Sistema inicializado')
    
    # Questoes exemplo
    questions = [{
        'id': 'enem_2023_001',
        'text': 'A energia solar fotovoltaica converte luz solar em eletricidade atraves de paineis solares.',
        'subject': 'fisica', 
        'year': 2023
    }]
    
    # Indexar
    success = await rag.add_questions_with_ml_features(questions)
    print(f'Questoes indexadas: {success}')
    
    # Buscar com ML
    results = await rag.search_with_ml_insights('energia renovavel solar', limit=1)
    
    print('\nResultados da busca:')
    for i, result in enumerate(results, 1):
        print(f'  {i}. Similaridade: {result["similarity"]:.3f}')
        print(f'     Dificuldade: {result.get("predicted_difficulty", "N/A")}')
        print(f'     Materia: {result["metadata"].get("subject", "N/A")}')
    
    print('TESTE FINAL CONCLUIDO COM SUCESSO!')

if __name__ == "__main__":
    asyncio.run(final_test())