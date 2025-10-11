#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para processamento de gabaritos com tratamento de encoding
"""

import sys
from pathlib import Path
sys.path.append('scripts')

try:
    from process_answer_keys import AnswerKeyProcessor
    
    processor = AnswerKeyProcessor()
    
    # Buscar arquivos de gabarito
    gabarito_files = processor.find_gabarito_files()
    print(f'Encontrados {len(gabarito_files)} arquivos de gabarito')
    
    # Processar apenas alguns para teste
    for i, file_path in enumerate(gabarito_files[:3]):
        print(f'[{i+1}/3] Testando: {file_path.name}')
        try:
            result = processor.process_answer_key_file(file_path)
            print(f'  OK: {result} respostas processadas')
        except Exception as e:
            print(f'  ERRO: {str(e)}')
            
except Exception as e:
    print(f'Erro na importacao: {e}')
    import traceback
    traceback.print_exc()
