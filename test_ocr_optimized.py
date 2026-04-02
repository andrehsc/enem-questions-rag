#!/usr/bin/env python3
"""
Teste do sistema OCR+Ollama otimizado com remo√ß√£o autom√°tica da primeira p√°gina
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "ocr_prototype"))

from ocr_ollama_extractor import OCRollamaExtractor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    print("Ì∫Ä TESTE DO SISTEMA OCR+OLLAMA OTIMIZADO")
    print("=" * 50)
    
    # PDF de teste
    pdf_path = "data/downloads/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"‚ùå PDF n√£o encontrado: {pdf_path}")
        return
    
    print(f"Ì≥Å PDF: {pdf_path}")
    print(f"Ì≥ä Testando com primeira p√°gina automaticamente ignorada")
    print()
    
    # Inicializar extrator
    extractor = OCRollamaExtractor()
    
    try:
        # Processar apenas 3 p√°ginas (que agora ser√£o p√°ginas 2, 3, 4 do PDF original)
        print("Ì¥Ñ Processando PDF com sistema otimizado...")
        print("Ì≤° Primeira p√°gina (metadata) ser√° automaticamente ignorada")
        
        result = extractor.extract_questions_from_pdf(
            pdf_path=pdf_path,
            max_pages=3,  # Processar√° p√°ginas 2, 3, 4 do PDF original
            save_images=True,
            generate_detailed_report=True
        )
        
        print("\n‚úÖ PROCESSAMENTO CONCLU√çDO!")
        print(f"Ì≥ä Quest√µes detectadas: {len(result[\"questions\"])}")
        print(f"ÔøΩÔøΩ P√°ginas processadas: {result[\"pages_processed\"]} (p√°ginas 2-4 do PDF original)")
        print(f"Ì≥ù Relat√≥rio detalhado: {result.get(\"detailed_report_path\", \"N√£o gerado\")}")
        print(f"Ì∂ºÔ∏è Imagens extra√≠das: {result.get(\"images_saved\", 0)}")
        
        # Mostrar resumo das quest√µes
        if result[\"questions\"]:
            print(f"\nÌæØ RESUMO DAS QUEST√ïES DETECTADAS:")
            for i, q in enumerate(result[\"questions\"], 1):
                print(f"  {i}. Q{q.get(\"number\", \"?\")}")
        
        print(f"\nÌ≥Å Verifique os arquivos em: reports/")
        
    except Exception as e:
        print(f"‚ùå Erro durante processamento: {e}")
        logger.exception("Erro detalhado:")

if __name__ == "__main__":
    main()
