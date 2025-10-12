#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para extração de imagens
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

# Import direto do módulo atual
sys.path.append(str(Path(__file__).parent))
from full_ingestion_report import FullIngestionProcessor

if __name__ == "__main__":
    # Configurações de teste
    parallel = False         # Usar processamento sequencial para debug
    max_workers = 1          # Um worker apenas
    batch_size = 2           # Lotes pequenos
    clear_db = True          # Limpar base primeiro
    process_questions = True
    process_answers = False   # Não processar gabaritos no teste
    extract_images = True     # ✅ ATIVAR extração de imagens
    
    processor = FullIngestionProcessor(extract_images=extract_images)
    
    print(f"TESTE DE EXTRAÇÃO DE IMAGENS")
    print(f"Clear DB: {clear_db}")
    print(f"Extrair imagens: {extract_images}")
    print()
    
    # Encontrar apenas alguns arquivos para teste
    question_files = processor.find_question_files()
    test_files = question_files[:2]  # Apenas 2 arquivos para teste
    
    print(f"Testando com {len(test_files)} arquivos:")
    for f in test_files:
        print(f"  - {f.name}")
    print()
    
    if clear_db:
        processor.clear_database()
    
    # Processar arquivos de teste
    print("PROCESSANDO ARQUIVOS DE TESTE...")
    print("="*50)
    
    if parallel:
        question_results = processor.process_question_files_batched(
            test_files, 
            batch_size=batch_size, 
            max_workers=max_workers
        )
    else:
        question_results = processor.process_question_files(test_files)
    
    # Relatório de teste
    print("\n" + "="*50)
    print("RELATÓRIO DE TESTE")
    print("="*50)
    print(f"Questões processadas: {question_results['success']}")
    print(f"Questões falharam: {question_results['failed']}")
    
    if question_results['failed_files']:
        print(f"\nArquivos com problema:")
        for file in question_results['failed_files']:
            print(f"  - {file}")
    
    # Verificar dados finais incluindo imagens
    processor.verify_final_data()
