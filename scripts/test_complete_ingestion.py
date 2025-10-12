#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Completo de Carga Integrada ENEM
"""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime
import time

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from enem_ingestion.db_integration_final import DatabaseIntegration
from enem_ingestion.image_extractor import ImageExtractor, DatabaseImageHandler

CONNECTION_URL = "postgresql://enem_rag_service:enem_rag_password@localhost:5433/teachershub_enem"

class CompleteIngestionTester:
    """Testador completo de ingestão ENEM"""
    
    def __init__(self):
        self.db_integration = DatabaseIntegration()
        self.image_extractor = ImageExtractor()
        self.db_image_handler = DatabaseImageHandler(CONNECTION_URL)
        
    def get_database_stats(self):
        """Obtém estatísticas atuais do banco"""
        conn = psycopg2.connect(CONNECTION_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        stats = {}
        tables = ['exam_metadata', 'questions', 'question_alternatives', 'answer_keys', 'question_images']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            result = cursor.fetchone()
            stats[table] = result['count']
        
        conn.close()
        return stats
    
    def test_single_pdf_complete_flow(self, pdf_path):
        """Testa fluxo completo com um único PDF"""
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            print(f"PDF nao encontrado: {pdf_path}")
            return False
        
        print(f"TESTE COMPLETO: {pdf_file.name}")
        print("=" * 60)
        
        try:
            # 1. Testar extração de metadados
            print("1. Testando extracao de metadados...")
            metadata = self.db_integration.parser.parse_filename(pdf_file.name)
            print(f"   Metadados: {metadata}")
            
            # 2. Processar o arquivo
            print("2. Processando arquivo PDF...")
            success = self.db_integration.process_pdf_file(Path(pdf_file))
            if "PV" in pdf_file.name:  # Prova de questões
                print(f"   Questoes processadas: {success}")
            else:  # Gabarito
                print(f"   Gabaritos processados: {success}")
            
            # 3. Testar extração de imagens (apenas para questões)
            if "PV" in pdf_file.name:
                print("3. Testando extracao de imagens...")
                extracted_images = self.image_extractor.extract_images_from_pdf(str(pdf_file))
                print(f"   Imagens extraidas: {len(extracted_images)}")
                
                if extracted_images:
                    # Mostrar algumas imagens como exemplo
                    for i, img in enumerate(extracted_images[:3], 1):
                        print(f"     Imagem {i}: {img.width}x{img.height} px, Pagina {img.page_number}, Seq {img.sequence}")
                    
                    if len(extracted_images) > 3:
                        print(f"     ... e mais {len(extracted_images) - 3} imagens")
                    
                    # Associar imagens com questões
                    print("4. Associando imagens com questoes...")
                    conn = psycopg2.connect(CONNECTION_URL, cursor_factory=RealDictCursor)
                    cursor = conn.cursor()
                    
                    # Buscar questões do mesmo ano/tipo
                    year = pdf_file.stem.split('_')[0]
                    cursor.execute("""
                        SELECT q.id, q.question_number, q.subject
                        FROM questions q
                        JOIN exam_metadata em ON q.exam_metadata_id = em.id
                        WHERE em.year = %s
                        ORDER BY q.question_number
                        LIMIT 1
                    """, (int(year),))
                    
                    questions = cursor.fetchall()
                    
                    if questions:
                        # Associar primeira questão com todas as imagens (para teste)
                        test_question = questions[0]
                        
                        stored_count = self.db_image_handler.store_question_images(
                            question_id=str(test_question['id']),
                            images=extracted_images
                        )
                        
                        print(f"   {stored_count} imagens associadas a questao {test_question['question_number']}")
                    else:
                        print("   Nenhuma questao encontrada para associar imagens")
                    
                    conn.close()
            
            print("Teste completo realizado com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro durante teste: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_comprehensive_test(self):
        """Executa teste abrangente em múltiplos arquivos"""
        
        print("TESTE ABRANGENTE DE CARGA INTEGRADA")
        print("=" * 50)
        print(f"Iniciado em: {datetime.now()}")
        
        # Stats iniciais
        print("\nEstado inicial do banco:")
        initial_stats = self.get_database_stats()
        self.print_stats(initial_stats)
        
        # Arquivos para teste
        test_files = [
            "data/downloads/2023/2023_PV_impresso_D1_CD1.pdf",  # Questões
            "data/downloads/2023/2023_GB_impresso_D1_CD1.pdf",  # Gabarito
        ]
        
        successful_tests = 0
        
        for pdf_path in test_files:
            if Path(pdf_path).exists():
                print(f"\n{'='*60}")
                success = self.test_single_pdf_complete_flow(pdf_path)
                if success:
                    successful_tests += 1
                time.sleep(2)  # Pausa entre testes
            else:
                print(f"Arquivo nao encontrado: {pdf_path}")
        
        # Stats finais
        print(f"\n{'='*60}")
        print("Estado final do banco:")
        final_stats = self.get_database_stats()
        self.print_stats(final_stats)
        
        # Comparação
        print("\nMudancas:")
        for table in initial_stats.keys():
            change = final_stats[table] - initial_stats[table]
            if change > 0:
                print(f"  {table}: +{change} registros")
        
        print(f"\nResultado: {successful_tests}/{len(test_files)} testes bem-sucedidos")
        
        return successful_tests == len(test_files)
    
    def print_stats(self, stats):
        """Imprime estatísticas formatadas"""
        for table, count in stats.items():
            print(f"  {table}: {count} registros")

def main():
    """Função principal"""
    tester = CompleteIngestionTester()
    
    if len(sys.argv) > 1:
        # Testar arquivo específico
        pdf_path = sys.argv[1]
        success = tester.test_single_pdf_complete_flow(pdf_path)
        return 0 if success else 1
    else:
        # Teste abrangente
        success = tester.run_comprehensive_test()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
