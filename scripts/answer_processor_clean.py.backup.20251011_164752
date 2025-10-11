#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processador de gabaritos ENEM limpo, sem problemas de encoding.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys

# Adicionar src ao path
sys.path.append('src')
sys.path.append('.')

from src.enem_ingestion.parser import EnemPDFParser

class CleanAnswerKeyProcessor:
    """Processador limpo para gabaritos ENEM"""
    
    def __init__(self):
        self.connection_url = "postgresql://enem_user:enem_password_2024@localhost:5432/enem_questions_rag"
        self.parser = EnemPDFParser()
    
    def get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def process_answer_key_file(self, file_path):
        """Processar um arquivo de gabarito e retornar numero de respostas inseridas"""
        print(f"Processando gabarito: {file_path}")
        
        # Parse do arquivo
        answer_data = self.parser.parse_answer_key(file_path)
        
        if not answer_data:
            print(f"  Nenhum gabarito encontrado")
            return 0
        
        # Extrair informacoes do arquivo
        filename = file_path.name
        year = file_path.parts[-2]
        
        # Determinar exam_type e day baseado no filename
        exam_type = "impresso"  # Default
        day = None
        
        if "D1" in filename:
            day = 1
        elif "D2" in filename:
            day = 2
            
        # Encontrar metadata correspondente
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Buscar metadata correspondente baseado no filename
                caderno = None
                if "CD1" in filename:
                    caderno = "CD1"
                elif "CD2" in filename:
                    caderno = "CD2" 
                elif "CD3" in filename:
                    caderno = "CD3"
                elif "CD4" in filename:
                    caderno = "CD4"
                elif "CD5" in filename:
                    caderno = "CD5"
                elif "CD6" in filename:
                    caderno = "CD6"
                elif "CD7" in filename:
                    caderno = "CD7"
                elif "CD8" in filename:
                    caderno = "CD8"
                
                cur.execute("""
                    SELECT id FROM exam_metadata 
                    WHERE year = %s AND day = %s AND caderno = %s AND file_type = 'caderno_questoes'
                    LIMIT 1
                """, (year, day, caderno))
                
                metadata = cur.fetchone()
                if not metadata:
                    print(f"  Metadata nao encontrada para {year}, day {day}, caderno {caderno}")
                    return 0
                
                exam_metadata_id = metadata['id']
                
                # Inserir answer keys
                inserted_count = 0
                
                for answer_key in answer_data:
                    try:
                        language_option_str = answer_key.language_option.value if answer_key.language_option else None
                        subject_str = answer_key.subject.value if answer_key.subject else 'geral'
                        
                        cur.execute("""
                            INSERT INTO answer_keys (exam_metadata_id, question_number, correct_answer, subject, language_option)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (exam_metadata_id, question_number, language_option) DO NOTHING
                        """, (exam_metadata_id, answer_key.question_number, answer_key.correct_answer, subject_str, language_option_str))
                        
                        if cur.rowcount > 0:
                            inserted_count += 1
                            
                    except Exception as e:
                        print(f"  Erro inserindo gabarito {answer_key.question_number}: {e}")
                
                conn.commit()
                return inserted_count

if __name__ == "__main__":
    # Teste basico
    processor = CleanAnswerKeyProcessor()
    test_file = Path("data/downloads/2020/2020_GB_impresso_D1_CD2.pdf")
    if test_file.exists():
        result = processor.process_answer_key_file(test_file)
        print(f"Resultado: {result} gabaritos inseridos")
