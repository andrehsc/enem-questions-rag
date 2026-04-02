#!/usr/bin/env python3
"""
Teste Completo de Extração com Imagens
====================================

Extrai mais questões e gera todas as imagens possíveis
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent / "src"))

def test_complete_extraction():
    try:
        from ocr_prototype.ocr_ollama_extractor import OCROllamaExtractor
        
        pdf_path = "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
        
        if not os.path.exists(pdf_path):
            logger.error(f"Arquivo não encontrado: {pdf_path}")
            return False
        
        logger.info("Inicializando extrator para extração completa...")
        extractor = OCROllamaExtractor()
        
        # Processar 5 páginas para obter mais questões
        logger.info("Processando 5 páginas para extração completa de imagens...")
        
        questions = extractor.extract_questions_from_pdf(
            pdf_path,
            save_images=True,
            output_dir="reports/complete_extraction",
            max_pages=5  # 5 páginas para mais questões
        )
        
        if questions:
            logger.info(f"SUCESSO: {len(questions)} questões extraídas")
            
            # Listar imagens geradas
            images_dir = Path("reports/complete_extraction/extracted_images")
            if images_dir.exists():
                images = list(images_dir.glob("*.png"))
                logger.info(f"Imagens geradas: {len(images)}")
                for img in sorted(images):
                    logger.info(f"  - {img.name}")
            
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
    print("Teste Completo de Extração com Imagens")
    print("=" * 50)
    
    success = test_complete_extraction()
    
    if success:
        print("\n[OK] Extração completa concluída!")
        print("Verifique as imagens em reports/complete_extraction/extracted_images/")
    else:
        print("\n[ERRO] Teste falhou!")
        sys.exit(1)
