"""
Script detalhado para testar o parser de quest√µes do ENEM.
"""

import os
import sys
sys.path.append('.')

from src.enem_ingestion.parser import EnemPDFParser
import pdfplumber


def analyze_question_parsing():
    """Analisa o parsing de quest√µes em detalhes."""
    parser = EnemPDFParser()
    
    # Encontrar um caderno
    data_dir = 'data/downloads'
    caderno_path = None
    
    for year_dir in os.listdir(data_dir):
        year_path = os.path.join(data_dir, year_dir)
        if os.path.isdir(year_path):
            for file in os.listdir(year_path):
                if '_PV_' in file and 'CD1' in file and file.endswith('.pdf'):
                    caderno_path = os.path.join(year_path, file)
                    break
            if caderno_path:
                break
    
    if not caderno_path:
        print("‚ùå Nenhum caderno CD1 encontrado!")
        return
    
    print(f"Ì≥ñ Analisando: {caderno_path}")
    
    # Extrair texto bruto para an√°lise
    with pdfplumber.open(caderno_path) as pdf:
        print(f"Ì≥Ñ Total de p√°ginas: {len(pdf.pages)}")
        
        # Analisar primeira p√°gina com quest√µes (p√°gina 3-4 geralmente)
        for page_num in range(min(10, len(pdf.pages))):
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            if text and 'QUEST√ÉO' in text:
                print(f"\nÌ¥ç P√°gina {page_num + 1} cont√©m quest√µes:")
                
                # Encontrar padr√µes de quest√µes
                import re
                question_matches = re.findall(r'QUEST√ÉO\s+(\d+)', text)
                if question_matches:
                    print(f"  Ì≥ù Quest√µes encontradas: {question_matches}")
                    
                    # Mostrar trecho de texto para uma quest√£o
                    first_question_match = re.search(r'QUEST√ÉO\s+(\d+)(.*?)(?=QUEST√ÉO\s+\d+|$)', text, re.DOTALL)
                    if first_question_match:
                        q_num = first_question_match.group(1)
                        q_text = first_question_match.group(2)[:500]
                        print(f"\n  Ì≥ã Quest√£o {q_num} (primeiros 500 chars):")
                        print(f"  {q_text}")
                        
                        # Procurar alternativas
                        alt_matches = re.findall(r'([A-E])\)\s*(.{1,100})', q_text)
                        if alt_matches:
                            print(f"  Ì¥§ Alternativas encontradas: {len(alt_matches)}")
                            for alt_letter, alt_text in alt_matches[:3]:
                                print(f"    {alt_letter}) {alt_text.strip()[:50]}...")
                        else:
                            print("  ‚ö†Ô∏è  Nenhuma alternativa encontrada no trecho")
                    
                break
    
    # Testar o parser
    print(f"\nÌ¥ß Testando parser:")
    questions = parser.parse_questions(caderno_path)
    print(f"Ì≥ä Total de quest√µes extra√≠das: {len(questions)}")
    
    if questions:
        # Mostrar detalhes das primeiras quest√µes
        for i, q in enumerate(questions[:3]):
            print(f"\nÌ≥å Quest√£o {q.number}:")
            print(f"  Ì≥ö Mat√©ria: {q.subject.value if q.subject else 'N/A'}")
            print(f"  Ì≥ù Texto: {q.text[:200]}...")
            print(f"  Ì¥§ Alternativas: {len(q.alternatives)}")
            if q.alternatives:
                for alt in q.alternatives[:2]:
                    print(f"    {alt[:80]}...")
            else:
                print("    ‚ö†Ô∏è  Nenhuma alternativa extra√≠da")


if __name__ == "__main__":
    analyze_question_parsing()
