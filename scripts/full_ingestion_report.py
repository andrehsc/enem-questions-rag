#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Ingestão Completa ENEM - Questões e Gabaritos
Processa todos os PDFs disponíveis (PV e GB) para criar base completa.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing
import threading
import re

# Import image extraction capabilities
try:
    from enem_ingestion.image_extractor import ImageExtractor, DatabaseImageHandler
    IMAGES_AVAILABLE = True
except ImportError:
    IMAGES_AVAILABLE = False

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from enem_ingestion.db_integration_final import DatabaseIntegration

class FullIngestionProcessor:
    """Processador completo de ingestão ENEM"""
    
    def __init__(self, extract_images=False):
        # Usar admin do PostgreSQL para operações de ingestão completa
        self.connection_url = "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
        self.db_integration = DatabaseIntegration(connection_url=self.connection_url)
        self.extract_images = extract_images and IMAGES_AVAILABLE
        
        # Initialize image extractor if available
        if self.extract_images:
            images_dir = Path("data/extracted_images")
            self.image_extractor = ImageExtractor(output_dir=images_dir)
            print("✅ Extração de imagens habilitada")
        else:
            self.image_extractor = None
            if extract_images and not IMAGES_AVAILABLE:
                print("⚠️  Extração de imagens desabilitada - instale PyMuPDF e Pillow")
        
    def get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def find_question_files(self):
        """Encontrar todos os arquivos de questão (PV)"""
        base_path = Path("data/downloads")
        files = []
        for year_dir in base_path.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                pv_files = list(year_dir.glob("*PV*.pdf"))
                files.extend(pv_files)
        return sorted(files)
    
    def find_answer_files(self):
        """Encontrar todos os arquivos de gabarito (GB)"""
        base_path = Path("data/downloads")
        files = []
        for year_dir in base_path.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                gb_files = list(year_dir.glob("*GB*.pdf"))
                files.extend(gb_files)
        return sorted(files)
    
    def clear_database(self):
        """Limpar tabelas antes da ingestão"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    print("Limpando banco de dados...")
                    cur.execute("TRUNCATE TABLE enem_questions.question_images CASCADE")
                    cur.execute("TRUNCATE TABLE enem_questions.question_alternatives CASCADE")
                    cur.execute("TRUNCATE TABLE enem_questions.answer_keys CASCADE")
                    cur.execute("TRUNCATE TABLE enem_questions.questions CASCADE")
                    cur.execute("TRUNCATE TABLE enem_questions.exam_metadata CASCADE")
                    conn.commit()
                    print("✅ Base de dados limpa com sucesso!")
        except Exception as e:
            print(f"❌ Erro limpando banco: {e}")
            raise
    
    def process_question_files(self, question_files):
        """Processar arquivos de questão com tratamento robusto de erros"""
        total_success = 0
        total_failed = 0
        failed_files = []
        
        for i, file_path in enumerate(question_files, 1):
            print(f"\n[{i}/{len(question_files)}] Processando: {file_path.name}")
            
            try:
                result = self.db_integration.process_pdf_file(file_path)
                
                if result['success']:
                    questions_inserted = result['questions_inserted']
                    
                    # Extrair e armazenar imagens se habilitado e questões foram inseridas
                    images_processed = 0
                    if self.extract_images and questions_inserted > 0:
                        print(f"  Iniciando extração de imagens para {file_path.name}...")
                        try:
                            images_processed = self.extract_and_store_images(file_path, [])
                            print(f"  Imagens processadas: {images_processed}")
                        except Exception as img_e:
                            print(f"  Warning: Failed to extract images: {img_e}")
                    
                    if images_processed > 0:
                        print(f"  OK: {questions_inserted}/{result['questions_parsed']} questoes + {images_processed} imagens importadas")
                    else:
                        print(f"  OK: {questions_inserted}/{result['questions_parsed']} questoes importadas")
                    
                    total_success += questions_inserted
                else:
                    print(f"  ERRO: {result['error']}")
                    total_failed += 1
                    failed_files.append(file_path.name)
                    
            except KeyboardInterrupt:
                print(f"  INTERROMPIDO pelo usuário")
                break
            except Exception as e:
                print(f"  EXCEPTION: {str(e)}")
                total_failed += 1
                failed_files.append(file_path.name)
                continue
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files
        }
    
    def process_single_file_worker(self, file_path):
        """Worker function para processamento paralelo de um único arquivo"""
        try:
            # Criar nova instância do DatabaseIntegration para thread safety usando admin credentials
            db_integration = DatabaseIntegration(connection_url=self.connection_url)
            result = db_integration.process_pdf_file(file_path)
            
            images_processed = 0
            
            if result['success']:
                # Se o processamento de questões foi bem-sucedido, extrair e armazenar imagens
                if self.extract_images and result['questions_inserted'] > 0:
                    print(f"Iniciando extração de imagens para {file_path.name}...")
                    try:
                        images_processed = self.extract_and_store_images(file_path, [])
                        print(f"Imagens processadas para {file_path.name}: {images_processed}")
                    except Exception as img_e:
                        print(f"Warning: Failed to extract images from {file_path.name}: {img_e}")
                        import traceback
                        traceback.print_exc()
                
                return {
                    'file': file_path.name,
                    'success': True,
                    'questions_parsed': result['questions_parsed'],
                    'questions_inserted': result['questions_inserted'],
                    'images_processed': images_processed,
                    'processing_time': time.time()
                }
            else:
                return {
                    'file': file_path.name,
                    'success': False,
                    'error': result['error'],
                    'images_processed': 0
                }
        except Exception as e:
            return {
                'file': file_path.name,
                'success': False,
                'error': str(e),
                'images_processed': 0
            }
    
    def process_question_files_parallel(self, question_files, max_workers=None):
        """Processar arquivos de questão em paralelo com threads"""
        if max_workers is None:
            # Usar número de CPUs disponíveis, mas limitado para não sobrecarregar o banco
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        print(f"Processando {len(question_files)} arquivos com {max_workers} workers paralelos...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        results = []
        
        start_time = time.time()
        
        # Usar ThreadPoolExecutor para I/O bound tasks (PDF parsing + DB operations)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submeter todas as tarefas
            future_to_file = {
                executor.submit(self.process_single_file_worker, file_path): file_path
                for file_path in question_files
            }
            
            # Processar resultados conforme completam
            for i, future in enumerate(as_completed(future_to_file), 1):
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        questions_inserted = result['questions_inserted']
                        images_processed = result.get('images_processed', 0)
                        total_success += questions_inserted
                        
                        if images_processed > 0:
                            print(f"[{i}/{len(question_files)}] ✓ {result['file']}: {questions_inserted}/{result['questions_parsed']} questões, {images_processed} imagens")
                        else:
                            print(f"[{i}/{len(question_files)}] ✓ {result['file']}: {questions_inserted}/{result['questions_parsed']} questões")
                    else:
                        total_failed += 1
                        failed_files.append(result['file'])
                        print(f"[{i}/{len(question_files)}] ✗ {result['file']}: {result['error']}")
                        
                except Exception as e:
                    total_failed += 1
                    failed_files.append(file_path.name)
                    print(f"[{i}/{len(question_files)}] ✗ {file_path.name}: Exception: {e}")
        
        processing_time = time.time() - start_time
        
        print(f"\nProcessamento paralelo concluído em {processing_time:.1f}s")
        print(f"Taxa: {len(question_files)/processing_time:.1f} arquivos/segundo")
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'processing_time': processing_time,
            'results': results
        }
    
    def process_question_files_batched(self, question_files, batch_size=8, max_workers=None):
        """Processar arquivos em lotes para controlar carga no banco"""
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        print(f"Processando {len(question_files)} arquivos em lotes de {batch_size} com {max_workers} workers...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        all_results = []
        
        # Dividir arquivos em lotes
        batches = [question_files[i:i+batch_size] for i in range(0, len(question_files), batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n--- LOTE {batch_num}/{len(batches)} ({len(batch)} arquivos) ---")
            
            result = self.process_question_files_parallel(batch, max_workers)
            
            total_success += result['success']
            total_failed += result['failed']
            failed_files.extend(result['failed_files'])
            all_results.extend(result['results'])
            
            # Pequena pausa entre lotes para não sobrecarregar
            if batch_num < len(batches):
                print("Pausa de 2s entre lotes...")
                time.sleep(2)
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'results': all_results
        }
    
    def get_matching_exam_metadata_id(self, gabarito_filename):
        """Encontrar exam_metadata_id correspondente ao gabarito"""
        try:
            # Converter GB para PV: 2020_GB_impresso_D1_CD2.pdf -> 2020_PV_impresso_D1_CD2.pdf
            pv_filename = gabarito_filename.replace('_GB_', '_PV_')
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM enem_questions.exam_metadata WHERE pdf_filename = %s", (pv_filename,))
                    result = cur.fetchone()
                    return result['id'] if result else None
        except Exception as e:
            print(f"Error finding matching exam metadata: {e}")
            return None
    
    def extract_answers_from_gabarito(self, file_path):
        """Extrair respostas do arquivo de gabarito usando pdfplumber"""
        try:
            import pdfplumber
            answers = {}
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Processar linha por linha
                    lines = text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Patterns para formato tabular de gabarito
                        # Exemplos: "1 C C 46 C", "2 A D 47 E", etc.
                        patterns = [
                            # Pattern principal: número + letra(s) + número + letra
                            r'(\d+)\s+([ABCDE])\s+(?:[ABCDE]\s+)?(\d+)\s+([ABCDE])',
                            # Pattern simples: número + letra
                            r'(\d+)\s+([ABCDE])(?:\s|$)',
                            # Pattern com múltiplas colunas
                            r'(\d+)\s+([ABCDE])\s+([ABCDE])',
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, line)
                            for match in matches:
                                if len(match) == 4:  # Pattern com 2 questões
                                    q1, a1, q2, a2 = match
                                    try:
                                        num1, num2 = int(q1), int(q2)
                                        if 1 <= num1 <= 180:
                                            answers[num1] = a1
                                        if 1 <= num2 <= 180:
                                            answers[num2] = a2
                                    except ValueError:
                                        continue
                                elif len(match) == 3:  # Pattern com inglês/espanhol
                                    q, a1, a2 = match
                                    try:
                                        num = int(q)
                                        if 1 <= num <= 180:
                                            # Usar primeira resposta (inglês por padrão)
                                            answers[num] = a1
                                    except ValueError:
                                        continue
                                elif len(match) == 2:  # Pattern simples
                                    q, a = match
                                    try:
                                        num = int(q)
                                        if 1 <= num <= 180:
                                            answers[num] = a
                                    except ValueError:
                                        continue
                        
                        # Pattern adicional para linhas com múltiplas respostas
                        # Ex: "1 C 2 A 3 D"
                        multi_pattern = r'(\d+)\s+([ABCDE])'
                        multi_matches = re.findall(multi_pattern, line)
                        for q_str, a in multi_matches:
                            try:
                                num = int(q_str)
                                if 1 <= num <= 180:
                                    answers[num] = a
                            except ValueError:
                                continue
            
            return answers
            
        except Exception as e:
            print(f"Error extracting answers from {file_path}: {e}")
            return {}
    
    def process_single_gabarito_worker(self, file_path):
        """Worker function para processamento paralelo de um gabarito"""
        try:
            # Encontrar exam_metadata correspondente
            exam_metadata_id = self.get_matching_exam_metadata_id(file_path.name)
            if not exam_metadata_id:
                return {
                    'file': file_path.name,
                    'success': False,
                    'error': 'Exam metadata not found',
                    'answers_inserted': 0
                }
            
            # Extrair respostas do gabarito
            answers = self.extract_answers_from_gabarito(file_path)
            if not answers:
                return {
                    'file': file_path.name,
                    'success': False,
                    'error': 'No answers extracted',
                    'answers_inserted': 0
                }
            
            # Inserir respostas no banco
            inserted_count = self.insert_answer_keys(answers, exam_metadata_id)
            
            return {
                'file': file_path.name,
                'success': True,
                'answers_extracted': len(answers),
                'answers_inserted': inserted_count,
            }
            
        except Exception as e:
            return {
                'file': file_path.name,
                'success': False,
                'error': str(e),
                'answers_inserted': 0
            }
    
    def insert_answer_keys(self, answers, exam_metadata_id):
        """Inserir gabaritos na tabela answer_keys"""
        inserted_count = 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Obter year e exam_type do exam_metadata
                    cur.execute("""
                        SELECT year, exam_type FROM enem_questions.exam_metadata 
                        WHERE id = %s
                    """, (exam_metadata_id,))
                    
                    exam_info = cur.fetchone()
                    if not exam_info:
                        print(f"Exam metadata not found for ID: {exam_metadata_id}")
                        return 0
                    
                    exam_year, exam_type = exam_info['year'], exam_info['exam_type'] or 'ENEM'
                    
                    for question_num, correct_answer in answers.items():
                        try:
                            # Verificar se já existe
                            cur.execute("""
                                SELECT id FROM enem_questions.answer_keys 
                                WHERE exam_metadata_id = %s AND question_number = %s
                            """, (exam_metadata_id, question_num))
                            
                            if cur.fetchone():
                                # Atualizar existente
                                cur.execute("""
                                    UPDATE enem_questions.answer_keys 
                                    SET correct_answer = %s
                                    WHERE exam_metadata_id = %s AND question_number = %s
                                """, (correct_answer, exam_metadata_id, question_num))
                            else:
                                # Inserir novo
                                cur.execute("""
                                    INSERT INTO enem_questions.answer_keys (exam_year, exam_type, question_number, correct_answer, exam_metadata_id)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (
                                    exam_year,
                                    exam_type,
                                    question_num,
                                    correct_answer,
                                    exam_metadata_id
                                ))
                            inserted_count += 1
                        except Exception as insert_e:
                            print(f"Error inserting question {question_num}: {insert_e}")
                            break
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"Error inserting answer keys: {e}")
            
        return inserted_count
    
    def process_answer_files_parallel(self, answer_files, max_workers=None):
        """Processar arquivos de gabarito em paralelo"""
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        print(f"Processando {len(answer_files)} gabaritos com {max_workers} workers paralelos...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        results = []
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.process_single_gabarito_worker, file_path): file_path
                for file_path in answer_files
            }
            
            for i, future in enumerate(as_completed(future_to_file), 1):
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        answers_inserted = result['answers_inserted']
                        total_success += answers_inserted
                        print(f"[{i}/{len(answer_files)}] ✓ {result['file']}: {answers_inserted}/{result['answers_extracted']} respostas")
                    else:
                        total_failed += 1
                        failed_files.append(result['file'])
                        print(f"[{i}/{len(answer_files)}] ✗ {result['file']}: {result['error']}")
                        
                except Exception as e:
                    total_failed += 1
                    failed_files.append(file_path.name)
                    print(f"[{i}/{len(answer_files)}] ✗ {file_path.name}: Exception: {e}")
        
        processing_time = time.time() - start_time
        print(f"\nProcessamento de gabaritos concluído em {processing_time:.1f}s")
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'processing_time': processing_time,
            'results': results
        }
    
    def process_answer_files_batched(self, answer_files, batch_size=8, max_workers=None):
        """Processar gabaritos em lotes"""
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        print(f"Processando {len(answer_files)} gabaritos em lotes de {batch_size} com {max_workers} workers...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        all_results = []
        
        # Dividir arquivos em lotes
        batches = [answer_files[i:i+batch_size] for i in range(0, len(answer_files), batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n--- LOTE GABARITOS {batch_num}/{len(batches)} ({len(batch)} arquivos) ---")
            
            result = self.process_answer_files_parallel(batch, max_workers)
            
            total_success += result['success']
            total_failed += result['failed']
            failed_files.extend(result['failed_files'])
            all_results.extend(result['results'])
            
            # Pequena pausa entre lotes
            if batch_num < len(batches):
                print("Pausa de 1s entre lotes...")
                time.sleep(1)
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'results': all_results
        }
    
    def run_full_ingestion(self, clear_db=False, parallel=True, max_workers=None, batch_size=8, process_answers=True):
        """Executar ingestão completa de questões"""
        print("INICIANDO INGESTÃO COMPLETA DO ENEM RAG")
        print("=" * 80)
        
        # Encontrar arquivos
        question_files = self.find_question_files()
        answer_files = self.find_answer_files() if process_answers else []
        
        print(f"Arquivos encontrados:")
        print(f"   Questões (PV): {len(question_files)}")
        if process_answers:
            print(f"   Gabaritos (GB): {len(answer_files)}")
        
        # Limpar banco se solicitado
        if clear_db:
            self.clear_database()
        
        # Processar questões
        print("\n" + "="*50)
        if parallel:
            print(f"PROCESSANDO QUESTÕES (PARALELO - {max_workers or 'auto'} workers, lotes de {batch_size})")
        else:
            print("PROCESSANDO QUESTÕES (SEQUENCIAL)")
        print("="*50)
        
        if parallel:
            question_results = self.process_question_files_batched(
                question_files, 
                batch_size=batch_size, 
                max_workers=max_workers
            )
        else:
            question_results = self.process_question_files(question_files)
        
        # Processar gabaritos se solicitado
        answer_results = None
        if process_answers and answer_files:
            print("\n" + "="*50)
            if parallel:
                print(f"PROCESSANDO GABARITOS (PARALELO - {max_workers or 'auto'} workers, lotes de {batch_size})")
            else:
                print("PROCESSANDO GABARITOS (SEQUENCIAL)")
            print("="*50)
            
            if parallel:
                answer_results = self.process_answer_files_batched(
                    answer_files,
                    batch_size=batch_size,
                    max_workers=max_workers
                )
            else:
                # Implementar versão sequencial se necessário
                answer_results = {'success': 0, 'failed': 0, 'failed_files': []}
        
        # Relatório final
        print("\n" + "="*50)
        print("RELATÓRIO FINAL")
        print("="*50)
        print(f"Questões processadas: {question_results['success']}")
        print(f"Questões falharam: {question_results['failed']}")
        
        if answer_results:
            print(f"Gabaritos processados: {answer_results['success']}")
            print(f"Gabaritos falharam: {answer_results['failed']}")
        
        if question_results['failed_files']:
            print(f"\nArquivos de questão com problema:")
            for file in question_results['failed_files']:
                print(f"  - {file}")
        
        if answer_results and answer_results['failed_files']:
            print(f"\nArquivos de gabarito com problema:")
            for file in answer_results['failed_files']:
                print(f"  - {file}")
        
        # Verificar dados finais
        self.verify_final_data()
        
        return {
            'questions': question_results,
            'answers': answer_results
        }
    
    def extract_and_store_images(self, pdf_path: Path, questions_data: list) -> int:
        """
        Extract and store images for questions from a PDF.
        
        Args:
            pdf_path: Path to the PDF file  
            questions_data: List of question data with IDs
            
        Returns:
            Number of images processed
        """
        if not self.extract_images or not self.image_extractor:
            return 0
        
        total_images = 0
        
        try:
            # Extract all images from PDF
            all_images = self.image_extractor.extract_images_from_pdf(pdf_path)
            
            if not all_images:
                return 0
            
            # Deduplicate images
            unique_images = self.image_extractor.deduplicate_images(all_images)
            
            # Store images in database
            with self.get_connection() as conn:
                image_handler = DatabaseImageHandler(self.connection_url)
                
                # Get questions from this PDF to associate images
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT q.id 
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        WHERE em.pdf_filename = %s
                        ORDER BY q.question_number
                        LIMIT 1
                    """, (pdf_path.name,))
                    
                    question_result = cur.fetchone()
                    
                    if question_result and unique_images:
                        first_question_id = question_result['id']
                        stored_count = image_handler.store_question_images(
                            first_question_id, unique_images
                        )
                        total_images += stored_count
                        
                        print(f"  Stored {stored_count} images for question {first_question_id}")
                        
                        conn.commit()
                    else:
                        print(f"  No questions found for {pdf_path.name} or no unique images to store")
            
        except Exception as e:
            print(f"Error extracting images from {pdf_path}: {e}")
        
        return total_images

    def verify_final_data(self):
        """Verificar dados finais no banco"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            'exam_metadata' as tabela, 
                            COUNT(*) as registros
                        FROM enem_questions.exam_metadata
                        UNION ALL
                        SELECT 'questions', COUNT(*) FROM enem_questions.questions
                        UNION ALL  
                        SELECT 'question_alternatives', COUNT(*) FROM enem_questions.question_alternatives
                        UNION ALL
                        SELECT 'answer_keys', COUNT(*) FROM enem_questions.answer_keys
                        UNION ALL
                        SELECT 'question_images', COUNT(*) FROM enem_questions.question_images
                        ORDER BY tabela
                    """)
                    
                    results = cur.fetchall()
                    print(f"\nDADOS FINAIS NO BANCO:")
                    for row in results:
                        print(f"  {row['tabela']}: {row['registros']}")
                        
        except Exception as e:
            print(f"Erro verificando dados finais: {e}")

if __name__ == "__main__":
    # Configurações de processamento paralelo
    parallel = True          # Usar processamento paralelo
    max_workers = 8          # Número de workers (threads) - AUMENTADO para acelerar
    batch_size = 12          # Arquivos por lote - AUMENTADO para melhor throughput
    clear_db = True          # Limpar base para começar do zero
    process_questions = True  # Processar questões
    process_answers = True    # Processar gabaritos
    extract_images = True     # ✅ ATIVAR extração de imagens das questões
    
    processor = FullIngestionProcessor(extract_images=extract_images)
    
    print(f"Configuração:")
    print(f"  Paralelo: {parallel}")
    print(f"  Workers: {max_workers}")
    print(f"  Batch size: {batch_size}")
    print(f"  Clear DB: {clear_db}")
    print(f"  Processar questões: {process_questions}")
    print(f"  Processar gabaritos: {process_answers}")
    print(f"  Extrair imagens: {extract_images}")
    print()
    
    # Executar ingestao de gabaritos apenas
    if process_questions:
        report = processor.run_full_ingestion(
            clear_db=clear_db,
            parallel=parallel,
            max_workers=max_workers,
            batch_size=batch_size,
            process_answers=process_answers
        )
    else:
        # Processar apenas gabaritos
        print("PROCESSANDO APENAS GABARITOS")
        print("=" * 80)
        
        answer_files = processor.find_answer_files()
        print(f"Gabaritos encontrados: {len(answer_files)}")
        
        if answer_files:
            print("\n" + "="*50)
            print(f"PROCESSANDO GABARITOS (PARALELO - {max_workers} workers, lotes de {batch_size})")
            print("="*50)
            
            answer_results = processor.process_answer_files_batched(
                answer_files,
                batch_size=batch_size,
                max_workers=max_workers
            )
            
            print("\n" + "="*50)
            print("RELATÓRIO FINAL - GABARITOS")
            print("="*50)
            print(f"Gabaritos processados: {answer_results['success']}")
            print(f"Gabaritos falharam: {answer_results['failed']}")
            
            if answer_results['failed_files']:
                print(f"\nArquivos com problema:")
                for file in answer_results['failed_files']:
                    print(f"  - {file}")
            
            # Verificar dados finais
            processor.verify_final_data()
