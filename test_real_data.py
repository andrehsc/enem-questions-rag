#!/usr/bin/env python3
import sys
sys.path.append('src')
from pathlib import Path
from enem_ingestion.parser import EnemPDFParser
import time

# Test with the most problematic file
pdf_path = Path('data/downloads/2023/2023_PV_impresso_D1_CD1.pdf')

if pdf_path.exists():
    print('TESTE COM DADOS REAIS - Enhanced Alternative Extractor')
    print('=' * 60)
    print(f'Arquivo: {pdf_path.name}')
    print(f'Problema conhecido: ~744 erros de alternativas no ultimo run')
    print()
    
    parser = EnemPDFParser()
    
    print('Iniciando extracao...')
    start_time = time.time()
    
    try:
        questions = parser.parse_questions(str(pdf_path))
        processing_time = time.time() - start_time
        
        print(f'Extracao concluida em {processing_time:.2f}s')
        print(f'Total de questoes extraidas: {len(questions)}')
        
        # Analyze alternatives quality
        valid_questions = 0
        partial_questions = 0
        invalid_questions = 0
        
        alternative_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
        
        sample_size = min(50, len(questions))
        
        for i in range(sample_size):
            if i < len(questions):
                q = questions[i]
                # Handle Question object attributes
                if hasattr(q, 'alternatives'):
                    alts = q.alternatives
                else:
                    alts = []
                alt_count = len(alts) if alts else 0
                
                alternative_counts[alt_count] = alternative_counts.get(alt_count, 0) + 1
                
                if alt_count >= 5:
                    valid_questions += 1
                elif alt_count >= 1:
                    partial_questions += 1
                else:
                    invalid_questions += 1
                    
                # Show first few problematic cases
                if alt_count < 5 and i < 10:
                    print(f'  Q{i+1}: {alt_count}/5 alternativas')
        
        print()
        print('ANALISE DE QUALIDADE (primeiras 50 questoes):')
        print(f'Questoes validas (5 alt): {valid_questions}/{sample_size} ({valid_questions/sample_size*100:.1f}%)')
        print(f'Questoes parciais (1-4 alt): {partial_questions}/{sample_size} ({partial_questions/sample_size*100:.1f}%)')
        print(f'Questoes invalidas (0 alt): {invalid_questions}/{sample_size} ({invalid_questions/sample_size*100:.1f}%)')
        
        print()
        print('Distribuicao de alternativas:')
        for count in [5, 4, 3, 2, 1, 0]:
            if count in alternative_counts:
                percentage = alternative_counts[count] / sample_size * 100
                print(f'  {count} alternativas: {alternative_counts[count]} questoes ({percentage:.1f}%)')
        
        # Calculate success rate
        success_rate = valid_questions / sample_size * 100 if sample_size > 0 else 0
        print()
        print(f'TAXA DE SUCESSO GERAL: {success_rate:.1f}%')
        
        if success_rate > 80:
            print('EXCELENTE: Enhanced extractor funcionando muito bem!')
        elif success_rate > 60:
            print('BOM: Melhoria significativa observada!')
        else:
            print('MODERADO: Algumas melhorias, mas ainda ha espaco para otimizacao')
            
    except Exception as e:
        print(f'Erro na extracao: {e}')
        import traceback
        traceback.print_exc()

else:
    print(f'Arquivo nao encontrado: {pdf_path}')
    print('Arquivos disponiveis:')
    base_dir = Path('data/downloads/2023')
    if base_dir.exists():
        for f in base_dir.glob('*PV*.pdf'):
            print(f'  {f.name}')
