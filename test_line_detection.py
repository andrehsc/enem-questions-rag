#!/usr/bin/env python3
"""
Teste da Nova Estratégia de Detecção Baseada em Linhas Horizontais
================================================================

Testa a implementação da delimitação inteligente:
1. Detecção de linhas horizontais ao lado das questões
2. Delimitação entre cabeçalhos consecutivos
3. Posicionamento preciso baseado na estrutura visual
"""

import os
import sys
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def test_line_based_detection():
    """Testa a nova detecção baseada em linhas"""
    
    try:
        from ocr_prototype.ocr_ollama_extractor import OCROllamaExtractor
        
        # Arquivo de teste
        pdf_path = "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
        
        if not os.path.exists(pdf_path):
            logger.error(f"Arquivo não encontrado: {pdf_path}")
            return False
        
        # Inicializar extrator
        logger.info("Inicializando extrator com detecção baseada em linhas...")
        extractor = OCROllamaExtractor()
        
        # Processar apenas primeira página para teste detalhado
        logger.info("Testando nova estratégia de delimitação...")
        
        questions = extractor.extract_questions_from_pdf(
            pdf_path,
            save_images=True,
            output_dir="reports/line_detection_test",
            max_pages=2  # Teste rápido
        )
        
        if questions:
            logger.info(f"SUCESSO: {len(questions)} questões extraídas com nova estratégia")
            
            for q in questions:
                logger.info(f"Q{q.number}: {len(q.text)} chars, alt: {len(q.alternatives)}")
            
            return True
        else:
            logger.warning("Nenhuma questão extraída")
            return False
            
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testando Nova Estratégia: Detecção Baseada em Linhas")
    print("=" * 60)
    
    success = test_line_based_detection()
    
    if success:
        print("\n[OK] Teste da detecção por linhas concluído!")
    else:
        print("\n[ERRO] Teste falhou!")
        sys.exit(1)
