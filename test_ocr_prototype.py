#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Protótipo OCR + Ollama
Demonstra a extração inteligente de questões ENEM usando análise de imagens.
"""

import sys
from pathlib import Path
from src.ocr_prototype.ocr_ollama_extractor import OCROllamaExtractor

def test_ocr_prototype():
    """Teste principal do protótipo"""
    print("🔬 PROTÓTIPO OCR + OLLAMA - TESTE DE EXTRAÇÃO")
    print("=" * 80)
    
    # Inicializar extrator
    extractor = OCROllamaExtractor()
    
    # Verificar disponibilidade de componentes
    print("📋 VERIFICAÇÃO DE COMPONENTES:")
    print(f"   ✅ Ollama disponível: {extractor.ollama.is_available()}")
    print(f"   ✅ Modelo preferido: {extractor.preferred_model}")
    print(f"   ✅ EasyOCR: {'Disponível' if extractor.easyocr_reader else 'Indisponível'}")
    print()
    
    # Arquivo de teste (o que analisamos manualmente)
    test_file = "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
    
    if not Path(test_file).exists():
        print(f"❌ Arquivo de teste não encontrado: {test_file}")
        print("   Certifique-se de que o arquivo está disponível para teste.")
        return False
    
    print(f"📄 TESTANDO COM: {test_file}")
    print("   (Sabemos que contém 16 questões Q91-Q106 pela análise manual)")
    print()
    
    try:
        # Executar comparação
        print("🔄 Executando extração OCR + Ollama...")
        results = extractor.compare_with_traditional(test_file)
        
        print("📊 RESULTADOS DA COMPARAÇÃO:")
        print("=" * 50)
        print(f"📈 OCR Method: {results['ocr_method']['count']} questões extraídas")
        print(f"📉 Traditional: {results['traditional_method']['count']} questões extraídas") 
        print(f"🎯 Vantagem OCR: {results['comparison']['ocr_advantage']} questões")
        print(f"🎖️  Esperado: 16 questões (Q91-Q106)")
        print()
        
        # Análise detalhada das questões OCR
        ocr_questions = results['ocr_method']['questions']
        
        if ocr_questions:
            print("🔍 ANÁLISE DETALHADA (OCR):")
            print("-" * 40)
            
            for i, q in enumerate(ocr_questions[:5]):  # Primeiras 5
                print(f"Questão {q.number}:")
                print(f"   Método: {q.extraction_method}")
                print(f"   Confiança: {q.confidence:.2f}")
                print(f"   Página: {q.page_num + 1}")
                print(f"   Alternativas: {len(q.alternatives)} encontradas")
                print(f"   Preview: {q.text[:100]}...")
                print()
            
            if len(ocr_questions) > 5:
                print(f"   ... e mais {len(ocr_questions) - 5} questões")
            
            # Estatísticas
            methods = [q.extraction_method for q in ocr_questions]
            confidence_avg = sum(q.confidence for q in ocr_questions) / len(ocr_questions)
            
            print("📈 ESTATÍSTICAS:")
            print(f"   Confiança média: {confidence_avg:.2f}")
            print(f"   Métodos utilizados: {set(methods)}")
            
            # Validação contra análise manual
            expected_range = list(range(91, 107))  # Q91-Q106
            extracted_numbers = [q.number for q in ocr_questions if q.number > 0]
            
            print("\n✅ VALIDAÇÃO CONTRA ANÁLISE MANUAL:")
            print(f"   Esperado: Q91-Q106 (16 questões)")
            print(f"   Extraído: {sorted(extracted_numbers)}")
            
            missing = set(expected_range) - set(extracted_numbers)
            extra = set(extracted_numbers) - set(expected_range)
            
            if missing:
                print(f"   ⚠️  Questões perdidas: {sorted(missing)}")
            if extra:
                print(f"   ℹ️  Questões extras: {sorted(extra)}")
            
            accuracy = len(set(extracted_numbers) & set(expected_range)) / len(expected_range)
            print(f"   🎯 Precisão: {accuracy:.1%}")
            
        else:
            print("❌ Nenhuma questão extraída via OCR")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gpu_performance():
    """Testa performance com e sem GPU"""
    print("🚀 TESTE DE PERFORMANCE GPU vs CPU")
    print("="*50)
    
    # Verificar se GPU está disponível
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
            print(f"   VRAM disponível: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            print(f"   VRAM em uso: {torch.cuda.memory_allocated(0) / 1024**3:.1f} GB")
        else:
            print("❌ GPU CUDA não disponível")
    except ImportError:
        print("❌ PyTorch não instalado")
    
    print()
    
def setup_environment():
    """Configura ambiente para teste"""
    print("🔧 CONFIGURAÇÃO DO AMBIENTE")
    print("-" * 30)
    
    # Verificar dependências
    missing_deps = []
    
    try:
        import cv2
        print("✅ OpenCV disponível")
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import pytesseract
        print("✅ Tesseract disponível")
    except ImportError:
        missing_deps.append("pytesseract")
    
    try:
        import easyocr
        print("✅ EasyOCR disponível")
    except ImportError:
        missing_deps.append("easyocr")
    
    if missing_deps:
        print(f"\n❌ DEPENDÊNCIAS FALTANDO: {missing_deps}")
        print("   Execute: pip install " + " ".join(missing_deps))
        return False
    
    print("✅ Todas as dependências básicas disponíveis")
    return True

def main():
    """Função principal"""
    print("🚀 INICIANDO TESTE DO PROTÓTIPO OCR + OLLAMA")
    print("=" * 80)
    
    # Verificar ambiente
    if not setup_environment():
        print("❌ Ambiente não configurado corretamente")
        return 1
    
    print()
    
    # Executar teste
    success = test_ocr_prototype()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("📊 Revise os resultados acima para avaliar a performance")
    else:
        print("❌ TESTE FALHOU")
        print("🔧 Verifique logs de erro e dependências")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())