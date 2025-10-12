#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Production Ingestion Script for ENEM Questions
==================================================
This script performs complete ingestion of all ENEM files in the downloads folder
including questões (PV), gabaritos (GB), and image extraction.
"""

import os
import sys
import logging
import glob
import time
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from enem_ingestion.db_integration_final import DatabaseIntegration
from enem_ingestion.image_extractor import ImageExtractor, DatabaseImageHandler

CONNECTION_URL = "postgresql://enem_rag_service:enem_rag_password@localhost:5433/teachershub_enem"

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_production_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FullProductionIngestion:
    """Classe para realizar ingestão completa de produção."""
    
    def __init__(self):
        """Inicializa o sistema de ingestão."""
        self.db_integration = DatabaseIntegration()
        self.image_extractor = ImageExtractor()
        self.db_image_handler = DatabaseImageHandler(CONNECTION_URL)
        
        # Estatísticas
        self.stats = {
            'files_processed': 0,
            'questions_processed': 0,
            'questions_inserted': 0,
            'alternatives_inserted': 0,
            'answer_keys_inserted': 0,
            'images_extracted': 0,
            'images_stored': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def get_all_pdf_files(self, downloads_dir: str = "data/downloads") -> Dict[str, List[str]]:
        """Obtém todos os arquivos PDF separados por tipo."""
        pv_files = glob.glob(os.path.join(downloads_dir, "**/*PV*.pdf"), recursive=True)
        gb_files = glob.glob(os.path.join(downloads_dir, "**/*GB*.pdf"), recursive=True)
        
        # Ordenar por ano e caderno
        pv_files.sort()
        gb_files.sort()
        
        return {
            'questions': pv_files,
            'answers': gb_files
        }
    
    def process_question_file(self, pdf_path: str) -> Dict:
        """Processa um arquivo de questões (PV)."""
        logger.info(f"Processando questões: {os.path.basename(pdf_path)}")
        
        try:
            # Processar PDF usando o sistema existente
            result = self.db_integration.process_pdf_file(Path(pdf_path))
            
            if result and result.get('success', False):
                self.stats['questions_processed'] += result.get('questions_parsed', 0)
                self.stats['questions_inserted'] += result.get('questions_inserted', 0)
                self.stats['alternatives_inserted'] += result.get('alternatives_inserted', 0)
                
                # Extrair e armazenar imagens se houver questões
                if result.get('questions_inserted', 0) > 0:
                    images_result = self.extract_and_store_images(pdf_path)
                    self.stats['images_extracted'] += images_result.get('images_extracted', 0)
                    self.stats['images_stored'] += images_result.get('images_stored', 0)
                
                return result
            else:
                return {'success': False, 'error': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Erro processando {pdf_path}: {e}")
            self.stats['errors'] += 1
            return {'success': False, 'error': str(e)}
    
    def process_answer_file(self, pdf_path: str) -> Dict:
        """Processa um arquivo de gabaritos (GB)."""
        logger.info(f"Processando gabaritos: {os.path.basename(pdf_path)}")
        
        try:
            # Processar gabaritos usando o sistema existente
            result = self.db_integration.process_pdf_file(Path(pdf_path))
            
            if result and result.get('success', False):
                self.stats['answer_keys_inserted'] += result.get('answer_keys_processed', 0)
                return result
            else:
                return {'success': False, 'error': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Erro processando gabaritos {pdf_path}: {e}")
            self.stats['errors'] += 1
            return {'success': False, 'error': str(e)}
    
    def extract_and_store_images(self, pdf_path: str) -> Dict:
        """Extrai e armazena imagens de um PDF."""
        try:
            # Extrair imagens do PDF
            images = self.image_extractor.extract_images_from_pdf(pdf_path)
            
            if not images:
                return {'images_extracted': 0, 'images_stored': 0}
            
            logger.info(f"Extraídas {len(images)} imagens de {os.path.basename(pdf_path)}")
            
            # Buscar questões relacionadas a este PDF para associar imagens
            conn = psycopg2.connect(CONNECTION_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()
            
            # Extrair ano do nome do arquivo
            filename = os.path.basename(pdf_path)
            year = filename.split('_')[0]
            
            cursor.execute("""
                SELECT q.id FROM enem_questions.questions q
                JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                WHERE em.pdf_filename = %s
                ORDER BY q.question_number
                LIMIT 1
            """, (filename,))
            
            question_result = cursor.fetchone()
            images_stored = 0
            
            if question_result and images:
                # Associar imagens à primeira questão encontrada
                question_id = str(question_result['id'])
                stored_count = self.db_image_handler.store_question_images(question_id, images)
                images_stored = stored_count
                logger.info(f"Armazenadas {stored_count} imagens para questão {question_id}")
            
            conn.close()
            
            return {
                'images_extracted': len(images),
                'images_stored': images_stored
            }
            
        except Exception as e:
            logger.error(f"Erro extraindo imagens de {pdf_path}: {e}")
            return {'images_extracted': 0, 'images_stored': 0}
    
    def print_progress(self, current: int, total: int, file_type: str, filename: str):
        """Imprime progresso da operação."""
        progress = (current / total) * 100
        elapsed = datetime.now() - self.stats['start_time']
        
        print(f"\n{'='*60}")
        print(f"PROGRESSO: {current}/{total} ({progress:.1f}%)")
        print(f"TIPO: {file_type}")
        print(f"ARQUIVO: {filename}")
        print(f"TEMPO DECORRIDO: {elapsed}")
        print(f"QUESTÕES: {self.stats['questions_processed']} processadas, {self.stats['questions_inserted']} inseridas")
        print(f"ALTERNATIVAS: {self.stats['alternatives_inserted']} inseridas")
        print(f"GABARITOS: {self.stats['answer_keys_inserted']} inseridos")
        print(f"IMAGENS: {self.stats['images_extracted']} extraídas, {self.stats['images_stored']} armazenadas")
        print(f"ERROS: {self.stats['errors']}")
        print(f"{'='*60}")
    
    def run_full_ingestion(self):
        """Executa ingestão completa de todos os arquivos."""
        logger.info("INICIANDO INGESTÃO COMPLETA DE PRODUÇÃO")
        logger.info(f"Iniciado em: {self.stats['start_time']}")
        
        try:
            # Obter todos os arquivos
            files = self.get_all_pdf_files()
            total_files = len(files['questions']) + len(files['answers'])
            
            logger.info(f"Total de arquivos encontrados: {total_files}")
            logger.info(f"  - Questões (PV): {len(files['questions'])}")
            logger.info(f"  - Gabaritos (GB): {len(files['answers'])}")
            
            current_file = 0
            
            # Processar arquivos de questões
            logger.info("\n📝 PROCESSANDO ARQUIVOS DE QUESTÕES...")
            for pdf_path in files['questions']:
                current_file += 1
                filename = os.path.basename(pdf_path)
                self.print_progress(current_file, total_files, "QUESTÕES", filename)
                
                result = self.process_question_file(pdf_path)
                self.stats['files_processed'] += 1
                
                if not result['success']:
                    logger.error(f"❌ Falha: {filename} - {result.get('error', 'Unknown error')}")
                else:
                    logger.info(f"✅ Sucesso: {filename}")
                
                # Pequena pausa para não sobrecarregar
                time.sleep(0.5)
            
            # Processar arquivos de gabaritos
            logger.info("\n🎯 PROCESSANDO ARQUIVOS DE GABARITOS...")
            for pdf_path in files['answers']:
                current_file += 1
                filename = os.path.basename(pdf_path)
                self.print_progress(current_file, total_files, "GABARITOS", filename)
                
                result = self.process_answer_file(pdf_path)
                self.stats['files_processed'] += 1
                
                if not result['success']:
                    logger.error(f"❌ Falha: {filename} - {result.get('error', 'Unknown error')}")
                else:
                    logger.info(f"✅ Sucesso: {filename}")
                
                # Pequena pausa para não sobrecarregar
                time.sleep(0.5)
            
            # Estatísticas finais
            self.print_final_statistics()
            
        except Exception as e:
            logger.error(f"Erro na ingestão completa: {e}")
            raise
    
    def print_final_statistics(self):
        """Imprime estatísticas finais."""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        print(f"\n{'='*80}")
        print(f"INGESTÃO COMPLETA FINALIZADA!")
        print(f"{'='*80}")
        print(f"TEMPO TOTAL: {duration}")
        print(f"INÍCIO: {self.stats['start_time']}")
        print(f"FIM: {end_time}")
        print(f"\nESTATÍSTICAS FINAIS:")
        print(f"  📁 Arquivos processados: {self.stats['files_processed']}")
        print(f"  📝 Questões processadas: {self.stats['questions_processed']}")
        print(f"  ✅ Questões inseridas: {self.stats['questions_inserted']}")
        print(f"  📋 Alternativas inseridas: {self.stats['alternatives_inserted']}")
        print(f"  🎯 Gabaritos inseridos: {self.stats['answer_keys_inserted']}")
        print(f"  🖼️  Imagens extraídas: {self.stats['images_extracted']}")
        print(f"  💾 Imagens armazenadas: {self.stats['images_stored']}")
        print(f"  ❌ Erros: {self.stats['errors']}")
        print(f"{'='*80}")
        
        # Log final
        logger.info("INGESTÃO COMPLETA FINALIZADA COM SUCESSO!")
        logger.info(f"Estatísticas: {self.stats}")
        
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
    """Função principal."""
    print("🚀 INGESTÃO COMPLETA DE PRODUÇÃO - ENEM RAG SYSTEM 🚀")
    print("=" * 60)
    
    try:
        ingestion = FullProductionIngestion()
        ingestion.run_full_ingestion()
        print("\n✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️ INTERROMPIDO PELO USUÁRIO")
        logger.info("Processo interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {e}")
        logger.error(f"Erro fatal na ingestão: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
