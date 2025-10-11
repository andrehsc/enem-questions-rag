#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para processar arquivos de gabarito (GB) e carregar na tabela answer_keys.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys
import os

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from enem_ingestion.parser import EnemPDFParser

class AnswerKeyProcessor:
    """Processador de gabaritos ENEM"""
    
    def __init__(self):
        self.connection_url = "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
        self.parser = EnemPDFParser()
    
    def get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def find_gabarito_files(self, year=None):
        """Encontrar arquivos de gabarito"""
        base_path = Path("data/downloads")
        
        if year:
            pattern = f"{year}/*GB*.pdf"
        else:
            pattern = "*/*GB*.pdf"
        
        files = list(base_path.glob(pattern))
        return sorted(files)
    
    def get_matching_exam_metadata(self, gabarito_filename):
        """Encontrar exam_metadata correspondente ao gabarito"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Extrair informaÃ§Ãµes do nome do arquivo de gabarito
                # Ex: 2020_GB_impresso_D1_CD2.pdf -> 2020_PV_impresso_D1_CD2.pdf
                metadata = self.parser.parse_filename(gabarito_filename)
                
                # Buscar exam_metadata correspondente
                cur.execute("""
                    SELECT id, pdf_filename 
                    FROM exam_metadata 
                    WHERE year = %s AND day = %s AND caderno = %s
                """, (metadata.year, metadata.day, metadata.caderno))
                
                result = cur.fetchone()
                return result
    
    def process_answer_key_file(self, gabarito_path):
        """Processar um arquivo de gabarito"""
        print(f"Processando gabarito: {gabarito_path.name}")
        
        try:
            # Parse do gabarito
            answer_keys = self.parser.parse_answer_key(gabarito_path)
            if not answer_keys:
                print(f"  â ï¸  Nenhuma resposta encontrada em {gabarito_path.name}")
                return 0
            
            print(f"  í³ Encontradas {len(answer_keys)} respostas")
            
            # Encontrar exam_metadata correspondente
            exam_metadata = self.get_matching_exam_metadata(gabarito_path.name)
            if not exam_metadata:
                print(f"  â NÃ£o encontrado exam_metadata correspondente para {gabarito_path.name}")
                return 0
            
            exam_metadata_id = exam_metadata['id']
            print(f"  í´ Vinculado ao arquivo: {exam_metadata['pdf_filename']}")
            
            # Inserir respostas no banco
            inserted_count = 0
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for answer_key in answer_keys:
                        try:
                            # Verificar se jÃ¡ existe
                            cur.execute("""
                                SELECT id FROM answer_keys 
                                WHERE exam_metadata_id = %s 
                                AND question_number = %s
                                AND language_option = %s
                            """, (
                                exam_metadata_id, 
                                answer_key.question_number,
                                answer_key.language_option.value if answer_key.language_option else None
                            ))
                            
                            if cur.fetchone():
                                print(f"    â ï¸  Resposta Q{answer_key.question_number} jÃ¡ existe, pulando")
                                continue
                            
                            # Inserir nova resposta
                            cur.execute("""
                                INSERT INTO answer_keys (
                                    id, exam_metadata_id, question_number, 
                                    correct_answer, language_option, subject
                                )
                                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
                            """, (
                                exam_metadata_id,
                                answer_key.question_number,
                                answer_key.correct_answer,
                                answer_key.language_option.value if answer_key.language_option else None,
                                answer_key.subject.value if answer_key.subject else None
                            ))
                            
                            inserted_count += 1
                            
                        except Exception as e:
                            print(f"    â Erro ao inserir Q{answer_key.question_number}: {e}")
                            conn.rollback()
                            continue
                    
                    # Commit das inserÃ§Ãµes
                    conn.commit()
            
            print(f"  â {inserted_count} respostas inseridas com sucesso")
            return inserted_count
            
        except Exception as e:
            print(f"  â Erro ao processar {gabarito_path.name}: {e}")
            return 0
    
    def process_all_gabaritos(self, year=None, limit=None):
        """Processar todos os gabaritos"""
        files = self.find_gabarito_files(year)
        
        if limit:
            files = files[:limit]
        
        print(f"í³ Encontrados {len(files)} arquivos de gabarito")
        
        total_inserted = 0
        successful_files = 0
        
        for gabarito_file in files:
            inserted = self.process_answer_key_file(gabarito_file)
            if inserted > 0:
                successful_files += 1
                total_inserted += inserted
        
        print(f"\ní³ RESUMO:")
        print(f"   Arquivos processados: {len(files)}")
        print(f"   Arquivos com sucesso: {successful_files}")
        print(f"   Total de respostas inseridas: {total_inserted}")
        
        return total_inserted
    
    def verify_answer_keys(self):
        """Verificar gabaritos carregados"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("\ní´ VERIFICAÃÃO DOS GABARITOS:")
                
                # Total de gabaritos
                cur.execute("SELECT COUNT(*) as total FROM answer_keys")
                total = cur.fetchone()['total']
                print(f"   Total de respostas: {total}")
                
                # Por ano
                cur.execute("""
                    SELECT em.year, COUNT(*) as respostas
                    FROM answer_keys ak
                    JOIN exam_metadata em ON ak.exam_metadata_id = em.id
                    GROUP BY em.year
                    ORDER BY em.year
                """)
                print("   Por ano:")
                for row in cur.fetchall():
                    print(f"     {row['year']}: {row['respostas']} respostas")
                
                # Por matÃ©ria
                cur.execute("""
                    SELECT 
                        COALESCE(subject, 'NÃ£o especificada') as materia,
                        COUNT(*) as respostas
                    FROM answer_keys
                    GROUP BY subject
                    ORDER BY respostas DESC
                """)
                print("   Por matÃ©ria:")
                for row in cur.fetchall():
                    print(f"     {row['materia']}: {row['respostas']} respostas")
                
                # QuestÃµes com gabarito disponÃ­vel
                cur.execute("""
                    SELECT COUNT(DISTINCT q.id) as questoes_com_gabarito
                    FROM questions q
                    JOIN answer_keys ak ON ak.question_number = q.question_number
                        AND ak.exam_metadata_id = q.exam_metadata_id
                """)
                result = cur.fetchone()
                if result:
                    print(f"   QuestÃµes com gabarito: {result['questoes_com_gabarito']}")

if __name__ == "__main__":
    processor = AnswerKeyProcessor()
    
    print("í¾¯ PROCESSADOR DE GABARITOS ENEM")
    print("=" * 50)
    
    # Processar gabaritos de 2020 primeiro (para testar)
    processor.process_all_gabaritos(year=2020, limit=2)
    
    # Verificar resultados
    processor.verify_answer_keys()
