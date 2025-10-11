#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para analisar estrutura dos PDFs do ENEM."""

import sys
from pathlib import Path
import pdfplumber

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings


def analyze_pdf_structure(pdf_path):
    """Analyze structure of a single PDF."""
    print(f"\n=== ANÁLISE: {pdf_path.name} ===")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total de páginas: {len(pdf.pages)}")
            
            # Analyze first few pages
            for i, page in enumerate(pdf.pages[:3]):
                print(f"\n--- PÁGINA {i+1} ---")
                text = page.extract_text()
                
                if text:
                    lines = text.split('\n')
                    print(f"Linhas de texto: {len(lines)}")
                    print("Primeiras 10 linhas:")
                    for j, line in enumerate(lines[:10]):
                        print(f"  {j+1}: {line.strip()}")
                    
                    # Look for question patterns
                    question_patterns = []
                    for line_num, line in enumerate(lines):
                        # Pattern for numbered questions
                        if line.strip() and (
                            line.strip().startswith(tuple(str(i) for i in range(1, 100))) or
                            'QUESTÃO' in line.upper() or
                            line.strip().startswith(('A)', 'B)', 'C)', 'D)', 'E)'))
                        ):
                            question_patterns.append(f"Linha {line_num+1}: {line.strip()}")
                    
                    if question_patterns:
                        print(f"\nPadrões de questão encontrados:")
                        for pattern in question_patterns[:5]:
                            print(f"  {pattern}")
                else:
                    print("  [Sem texto extraível]")
                    
    except Exception as e:
        print(f"Erro ao analisar {pdf_path}: {e}")


def main():
    """Analyze structure of different PDF types."""
    print("ANÁLISE DA ESTRUTURA DOS PDFs DO ENEM")
    print("=" * 60)
    
    downloads_dir = Path("data/downloads")
    
    # Sample different types of files
    sample_files = []
    
    # Regular exam questions (caderno)
    for year in [2024, 2023]:
        caderno_files = list((downloads_dir / str(year)).glob("*PV_impresso_D1_CD1.pdf"))
        if caderno_files:
            sample_files.append(("Caderno Regular", caderno_files[0]))
    
    # Answer keys (gabarito)
    for year in [2024, 2023]:
        gabarito_files = list((downloads_dir / str(year)).glob("*GB_impresso_D1_CD1.pdf"))
        if gabarito_files:
            sample_files.append(("Gabarito", gabarito_files[0]))
    
    # Special types (if available)
    special_files = list((downloads_dir / "2024").glob("*CD10.pdf"))
    if special_files:
        sample_files.append(("Libras", special_files[0]))
    
    ppl_files = list((downloads_dir / "2024").glob("*PPL*.pdf"))
    if ppl_files:
        sample_files.append(("PPL", ppl_files[0]))
    
    print(f"Analisando {len(sample_files)} tipos de arquivo...")
    
    for file_type, file_path in sample_files:
        print(f"\n{'='*20} {file_type.upper()} {'='*20}")
        analyze_pdf_structure(file_path)
    
    print(f"\n{'='*60}")
    print("ANÁLISE CONCLUÍDA")


if __name__ == "__main__":
    main()
