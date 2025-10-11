#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from process_answer_keys import AnswerKeyProcessor

processor = AnswerKeyProcessor()
gabarito_files = processor.find_gabarito_files()

print(f'Processando {len(gabarito_files)} arquivos de gabarito...')

total_inserted = 0
successful_files = 0

for i, file_path in enumerate(gabarito_files, 1):
    print(f'[{i}/{len(gabarito_files)}] {file_path.name}')
    try:
        result = processor.process_answer_key_file(file_path)
        total_inserted += result
        if result > 0:
            successful_files += 1
        print(f'  OK: {result} respostas inseridas')
    except Exception as e:
        print(f'  ERRO: {str(e)}')

print(f'\nResumo final:')
print(f'  Total de respostas inseridas: {total_inserted}')
print(f'  Arquivos processados com sucesso: {successful_files}/{len(gabarito_files)}')
