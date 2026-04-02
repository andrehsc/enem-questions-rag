#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Ingestão Completa ENEM - Questões e Gabaritos
Processa todos os PDFs disponíveis (PV e GB) para criar base completa.

EXEMPLOS DE USO:

1. Processar tudo (padrão):
   python scripts/full_ingestion_report.py

2. Processar apenas lote 1:
   python scripts/full_ingestion_report.py --question-batches "1"

3. Processar lotes específicos (1, 4, 5):
   python scripts/full_ingestion_report.py --question-batches "1,4,5"

4. Processar apenas gabaritos, lotes 2 e 3:
   python scripts/full_ingestion_report.py --no-questions --answer-batches "2,3"

5. Processar sem limpar banco, lotes específicos:
   python scripts/full_ingestion_report.py --no-clear --question-batches "1,2"

6. Processar com configurações personalizadas:
   python scripts/full_ingestion_report.py --workers 4 --batch-size 8 --question-batches "1,3"

OBSERVAÇÕES:
- Os logs de erros específicos são salvos em data/extraction/<timestamp>/
- Cada arquivo PDF terá seu próprio arquivo de erro com sufixo "-errors.txt"
- Os logs no console são otimizados para mostrar apenas informações essenciais
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
import logging
import os
import argparse
from io import StringIO

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

# Import image extraction capabilities
try:
    from enem_ingestion.image_extractor import ImageExtractor, DatabaseImageHandler
    IMAGES_AVAILABLE = True
except ImportError as e:
    print(f"DEBUG - Image extractor import failed: {e}")
    IMAGES_AVAILABLE = False

from enem_ingestion.db_integration_final import DatabaseIntegration
from enem_ingestion.enem_structure_spec import EnemStructuralGuardrailsController


class ExtractorLogHandler:
    """Gerenciador de logs de extração com saída por arquivo"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_start = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.errors_dir = self.output_dir / self.extraction_start
        self.errors_dir.mkdir(exist_ok=True)
        self.file_handlers = {}
        
    def get_error_file(self, pdf_filename: str) -> Path:
        """Obter arquivo de erro para um PDF específico"""
        error_filename = f"{pdf_filename}-errors.txt"
        return self.errors_dir / error_filename
    
    def log_file_error(self, pdf_filename: str, error_message: str):
        """Logar erro específico do arquivo em seu dump de erros"""
        error_file = self.get_error_file(pdf_filename)
        
        with open(error_file, 'a', encoding='utf-8') as f:
            f.write(f"{error_message}\n")
    
    def get_extraction_dir(self) -> Path:
        """Retornar diretório de extração atual"""
        return self.errors_dir

class FullIngestionProcessor:
    """Processador completo de ingestão ENEM"""
    
    def __init__(self, extract_images=False):
        # Usar admin do PostgreSQL para operações de ingestão completa
        self.connection_url = "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
        self.db_integration = DatabaseIntegration(connection_url=self.connection_url)
        self.extract_images = extract_images and IMAGES_AVAILABLE
        
        # Initialize log handler for extraction errors
        self.log_handler = ExtractorLogHandler(Path("data/extraction"))
        
        # Initialize image extractor if available
        if self.extract_images:
            images_dir = Path("data/extracted_images")
            self.image_extractor = ImageExtractor(output_dir=images_dir)
            print("OK - Extracao de imagens habilitada")
        else:
            self.image_extractor = None
            if extract_images and not IMAGES_AVAILABLE:
                print("AVISO - Extracao de imagens desabilitada - instale PyMuPDF e Pillow")
        
        # Initialize guardrails controller for metrics
        self.guardrails_controller = EnemStructuralGuardrailsController()
        self.guardrails_metrics = {
            'total_questions_analyzed': 0,
            'direct_success': 0,
            'recovery_applied': 0,
            'critical_zone_detected': 0,
            'validation_failures': 0
        }
        
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
                    print("OK - Base de dados limpa com sucesso!")
        except Exception as e:
            print(f"ERRO - Erro limpando banco: {e}")
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
            
            # Capturar logs de parsing errors para arquivo específico
            old_log_handler = self._setup_file_logging(file_path.name)
            
            try:
                result = db_integration.process_pdf_file(file_path)
                
                # Capturar métricas dos guardrails se disponíveis
                if hasattr(db_integration.parser, '_last_guardrails_metrics'):
                    metrics = db_integration.parser._last_guardrails_metrics
                    # Thread-safe update das métricas globais
                    with threading.Lock():
                        self.guardrails_metrics['total_questions_analyzed'] += metrics.get('total_analyzed', 0)
                        self.guardrails_metrics['direct_success'] += metrics.get('direct_success', 0)
                        self.guardrails_metrics['recovery_applied'] += metrics.get('recovery_applied', 0)
                        self.guardrails_metrics['critical_zone_detected'] += metrics.get('critical_zone_detected', 0)
                        self.guardrails_metrics['validation_failures'] += metrics.get('validation_failures', 0)
                        
            finally:
                # Restaurar logging original
                self._restore_logging(old_log_handler)
            
            images_processed = 0
            
            if result['success']:
                # Se o processamento de questões foi bem-sucedido, extrair e armazenar imagens
                if self.extract_images and result['questions_inserted'] > 0:
                    try:
                        images_processed = self.extract_and_store_images(file_path, [])
                        # Não logar detalhes de imagens - será incluído no log de conclusão
                    except Exception as img_e:
                        # Log image extraction errors to file, not console
                        self.log_handler.log_file_error(file_path.name, f"Image extraction error: {img_e}")
                
                return {
                    'file': file_path.name,
                    'success': True,
                    'questions_parsed': result['questions_parsed'],
                    'questions_inserted': result['questions_inserted'],
                    'images_processed': images_processed,
                    'processing_time': time.time()
                }
            else:
                # Log critical errors that stop processing
                self.log_handler.log_file_error(file_path.name, f"Critical processing error: {result['error']}")
                return {
                    'file': file_path.name,
                    'success': False,
                    'error': result['error'],
                    'images_processed': 0
                }
        except Exception as e:
            # Log critical errors that stop processing
            self.log_handler.log_file_error(file_path.name, f"Critical exception: {e}")
            return {
                'file': file_path.name,
                'success': False,
                'error': str(e),
                'images_processed': 0
            }
    
    def _setup_file_logging(self, pdf_filename: str):
        """Configurar logging para capturar erros do parser em arquivo específico"""
        # Capturar logs do parser para arquivo específico
        class FileErrorCapture(logging.Handler):
            def __init__(self, log_handler, pdf_filename):
                super().__init__()
                self.log_handler = log_handler
                self.pdf_filename = pdf_filename
                
            def emit(self, record):
                if record.levelno >= logging.WARNING:
                    message = self.format(record)
                    # Filtrar apenas logs de parsing de alternativas/questões
                    if any(keyword in message for keyword in [
                        'alternatives', 'Skipping question', 'Expected 5 alternatives',
                        'Found only', 'not in alphabetical order'
                    ]):
                        self.log_handler.log_file_error(self.pdf_filename, message)
        
        # Adicionar handler temporário
        file_handler = FileErrorCapture(self.log_handler, pdf_filename)
        parser_logger = logging.getLogger('enem_ingestion.parser')
        parser_logger.addHandler(file_handler)
        return file_handler
    
    def _restore_logging(self, file_handler):
        """Restaurar configuração de logging original"""
        parser_logger = logging.getLogger('enem_ingestion.parser')
        parser_logger.removeHandler(file_handler)
    
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
        # Log resumido dos arquivos sendo processados
        for file_path in question_files:
            print(f"Processing: {file_path.name}")
        
        # Log início de extração de imagens se habilitado
        if self.extract_images:
            for file_path in question_files:
                print(f"Iniciando extração de imagens para {file_path.name}...")
        
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
                        questions_parsed = result['questions_parsed']
                        images_processed = result.get('images_processed', 0)
                        total_success += questions_inserted
                        
                        # Log format otimizado
                        if images_processed > 0:
                            print(f"[{i}/{len(question_files)}] OK {result['file']}: {questions_inserted}/{questions_parsed} questoes, {images_processed}/{images_processed} imagens")
                        else:
                            print(f"[{i}/{len(question_files)}] OK {result['file']}: {questions_inserted}/{questions_parsed} questoes")
                    else:
                        total_failed += 1
                        failed_files.append(result['file'])
                        # Apenas log de falha crítica - detalhes foram para arquivo
                        print(f"[{i}/{len(question_files)}] ERRO {result['file']}: FALHA CRITICA")
                        
                except Exception as e:
                    total_failed += 1
                    failed_files.append(file_path.name)
                    print(f"[{i}/{len(question_files)}] ERRO {file_path.name}: EXCECAO CRITICA")
        
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
    
    def process_question_files_batched(self, question_files, batch_size=8, max_workers=None, selected_batches=None):
        """Processar arquivos em lotes para controlar carga no banco"""
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        # Dividir arquivos em lotes
        batches = [question_files[i:i+batch_size] for i in range(0, len(question_files), batch_size)]
        
        # Filtrar lotes específicos se solicitado
        if selected_batches is not None:
            filtered_batches = []
            for batch_idx in selected_batches:
                if 1 <= batch_idx <= len(batches):
                    filtered_batches.append((batch_idx, batches[batch_idx - 1]))
                else:
                    print(f"AVISO - Lote {batch_idx} nao existe (maximo: {len(batches)})")
            batches = filtered_batches
            print(f"Processando lotes específicos: {selected_batches}")
        else:
            # Manter formato original para compatibilidade
            batches = [(i + 1, batch) for i, batch in enumerate(batches)]
            print(f"Processando {len(question_files)} arquivos em lotes de {batch_size} com {max_workers} workers...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        all_results = []
        
        for batch_num, batch in batches:
            # Calcular total de lotes corretamente
            if selected_batches is None:
                total_batches = len([x for x, _ in batches])  # Total de lotes processados
            else:
                # Dividir arquivos em lotes para calcular total correto
                all_batches = [question_files[i:i+batch_size] for i in range(0, len(question_files), batch_size)]
                total_batches = len(all_batches)
            
            print(f"\n--- LOTE {batch_num}/{total_batches} ({len(batch)} arquivos) ---")
            
            result = self.process_question_files_parallel(batch, max_workers)
            
            total_success += result['success']
            total_failed += result['failed']
            failed_files.extend(result['failed_files'])
            all_results.extend(result['results'])
            
            # Log resumido do processamento do lote
            processing_time = result.get('processing_time', 0)
            if processing_time > 0:
                print(f"Concluído em {processing_time:.1f}s - Taxa: {len(batch)/processing_time:.1f} arquivos/s")
            
            # Pequena pausa entre lotes para não sobrecarregar
            # Verificar se não é o último lote sendo processado
            is_last_batch = (batch_num == batches[-1][0]) if batches else True
            if not is_last_batch:
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
            # Capturar logs de parsing errors para arquivo específico
            old_log_handler = self._setup_file_logging(file_path.name)
            
            try:
                # Encontrar exam_metadata correspondente
                exam_metadata_id = self.get_matching_exam_metadata_id(file_path.name)
                if not exam_metadata_id:
                    self.log_handler.log_file_error(file_path.name, "Exam metadata not found")
                    return {
                        'file': file_path.name,
                        'success': False,
                        'error': 'Exam metadata not found',
                        'answers_inserted': 0
                    }
                
                # Extrair respostas do gabarito
                answers = self.extract_answers_from_gabarito(file_path)
                if not answers:
                    self.log_handler.log_file_error(file_path.name, "No answers extracted from file")
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
            finally:
                # Restaurar logging original
                self._restore_logging(old_log_handler)
                
        except Exception as e:
            # Log critical errors to file
            self.log_handler.log_file_error(file_path.name, f"Critical gabarito error: {e}")
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
                        answers_extracted = result['answers_extracted']
                        total_success += answers_inserted
                        print(f"[{i}/{len(answer_files)}] OK {result['file']}: {answers_inserted}/{answers_extracted} respostas")
                    else:
                        total_failed += 1
                        failed_files.append(result['file'])
                        # Log apenas falha crítica - detalhes foram para arquivo
                        print(f"[{i}/{len(answer_files)}] ERRO {result['file']}: FALHA CRITICA")
                        
                except Exception as e:
                    total_failed += 1
                    failed_files.append(file_path.name)
                    print(f"[{i}/{len(answer_files)}] ERRO {file_path.name}: EXCECAO CRITICA")
        
        processing_time = time.time() - start_time
        print(f"\nProcessamento de gabaritos concluído em {processing_time:.1f}s")
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'processing_time': processing_time,
            'results': results
        }
    
    def process_answer_files_batched(self, answer_files, batch_size=8, max_workers=None, selected_batches=None):
        """Processar gabaritos em lotes"""
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)
        
        # Dividir arquivos em lotes
        batches = [answer_files[i:i+batch_size] for i in range(0, len(answer_files), batch_size)]
        
        # Filtrar lotes específicos se solicitado
        if selected_batches is not None:
            filtered_batches = []
            for batch_idx in selected_batches:
                if 1 <= batch_idx <= len(batches):
                    filtered_batches.append((batch_idx, batches[batch_idx - 1]))
                else:
                    print(f"AVISO - Lote gabarito {batch_idx} nao existe (maximo: {len(batches)})")
            batches = filtered_batches
            print(f"Processando lotes de gabaritos específicos: {selected_batches}")
        else:
            # Manter formato original para compatibilidade
            batches = [(i + 1, batch) for i, batch in enumerate(batches)]
            print(f"Processando {len(answer_files)} gabaritos em lotes de {batch_size} com {max_workers} workers...")
        
        total_success = 0
        total_failed = 0
        failed_files = []
        all_results = []
        
        for batch_num, batch in batches:
            # Calcular total de lotes corretamente
            if selected_batches is None:
                total_batches = len([x for x, _ in batches])  # Total de lotes processados
            else:
                # Dividir arquivos em lotes para calcular total correto
                all_batches = [answer_files[i:i+batch_size] for i in range(0, len(answer_files), batch_size)]
                total_batches = len(all_batches)
            
            print(f"\n--- LOTE GABARITOS {batch_num}/{total_batches} ({len(batch)} arquivos) ---")
            
            result = self.process_answer_files_parallel(batch, max_workers)
            
            total_success += result['success']
            total_failed += result['failed']
            failed_files.extend(result['failed_files'])
            all_results.extend(result['results'])
            
            # Log resumido do processamento do lote para gabaritos
            processing_time = result.get('processing_time', 0)
            if processing_time > 0:
                print(f"Concluído em {processing_time:.1f}s")
            
            # Pequena pausa entre lotes
            # Verificar se não é o último lote sendo processado
            is_last_batch = (batch_num == batches[-1][0]) if batches else True
            if not is_last_batch:
                print("Pausa de 1s entre lotes...")
                time.sleep(1)
        
        return {
            'success': total_success,
            'failed': total_failed,
            'failed_files': failed_files,
            'results': all_results
        }
    
    def run_full_ingestion(self, clear_db=False, parallel=True, max_workers=None, batch_size=8, 
                          process_answers=True, selected_question_batches=None, selected_answer_batches=None):
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
        
        # Log dos lotes selecionados se especificados
        if selected_question_batches:
            print(f"   Lotes de questões selecionados: {selected_question_batches}")
        if selected_answer_batches:
            print(f"   Lotes de gabaritos selecionados: {selected_answer_batches}")
        
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
                max_workers=max_workers,
                selected_batches=selected_question_batches
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
                    max_workers=max_workers,
                    selected_batches=selected_answer_batches
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
        
        # Relatório de Guardrails Estruturais
        print("\n" + "="*30)
        print("ENEM STRUCTURAL GUARDRAILS")
        print("="*30)
        if self.guardrails_metrics['total_questions_analyzed'] > 0:
            total = self.guardrails_metrics['total_questions_analyzed']
            direct_pct = (self.guardrails_metrics['direct_success'] / total) * 100
            recovery_pct = (self.guardrails_metrics['recovery_applied'] / total) * 100
            
            print(f"Total de questões analisadas: {total}")
            print(f"Sucesso direto: {self.guardrails_metrics['direct_success']} ({direct_pct:.1f}%)")
            print(f"Recovery aplicado: {self.guardrails_metrics['recovery_applied']} ({recovery_pct:.1f}%)")
            print(f"Zona crítica detectada: {self.guardrails_metrics['critical_zone_detected']}")
            print(f"Falhas de validação: {self.guardrails_metrics['validation_failures']}")
            
            if self.guardrails_metrics['critical_zone_detected'] > 0:
                print(f"⚠️  {self.guardrails_metrics['critical_zone_detected']} questões na zona crítica (Q91-110)")
        else:
            print("Guardrails: Nenhuma questão processada pelos guardrails")
        
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
        
        # Log final do diretório de extrações
        print(f"\nLogs de extração salvos em: {self.log_handler.get_extraction_dir()}")
        
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
                        
                        # Log removido - será mostrado no resumo final do arquivo
                        
                        conn.commit()
                    else:
                        # Log removido - será mostrado no resumo final do arquivo
                        pass
            
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

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Ingestão completa ENEM - Questões e Gabaritos')
    
    parser.add_argument('--no-parallel', action='store_true', 
                       help='Desabilitar processamento paralelo')
    parser.add_argument('--workers', type=int, default=8,
                       help='Número de workers paralelos (padrão: 8)')
    parser.add_argument('--batch-size', type=int, default=12,
                       help='Tamanho do lote (padrão: 12)')
    parser.add_argument('--no-clear', action='store_true',
                       help='Não limpar banco antes de processar')
    parser.add_argument('--no-questions', action='store_true',
                       help='Não processar questões')
    parser.add_argument('--no-answers', action='store_true',
                       help='Não processar gabaritos')
    parser.add_argument('--no-images', action='store_true',
                       help='Desabilitar extração de imagens')
    parser.add_argument('--question-batches', type=str,
                       help='Lotes específicos de questões para processar (ex: "1,3,5" ou "2")')
    parser.add_argument('--answer-batches', type=str,
                       help='Lotes específicos de gabaritos para processar (ex: "1,3,5" ou "2")')
    
    return parser.parse_args()

def parse_batch_list(batch_str):
    """Parse string de lotes em lista de inteiros"""
    if not batch_str:
        return None
    
    try:
        batches = [int(x.strip()) for x in batch_str.split(',')]
        return batches
    except ValueError:
        print(f"ERRO - Formato invalido para lotes: {batch_str}")
        print("Use formato: '1,3,5' ou '2'")
        sys.exit(1)

if __name__ == "__main__":
    args = parse_arguments()
    
    # Configurações baseadas nos argumentos
    parallel = not args.no_parallel
    max_workers = args.workers
    batch_size = args.batch_size
    clear_db = not args.no_clear
    process_questions = not args.no_questions
    process_answers = not args.no_answers
    extract_images = not args.no_images
    
    # Parse dos lotes específicos
    selected_question_batches = parse_batch_list(args.question_batches)
    selected_answer_batches = parse_batch_list(args.answer_batches)
    
    processor = FullIngestionProcessor(extract_images=extract_images)
    
    print(f"Configuração:")
    print(f"  Paralelo: {parallel}")
    print(f"  Workers: {max_workers}")
    print(f"  Batch size: {batch_size}")
    print(f"  Clear DB: {clear_db}")
    print(f"  Processar questões: {process_questions}")
    print(f"  Processar gabaritos: {process_answers}")
    print(f"  Extrair imagens: {extract_images}")
    if selected_question_batches:
        print(f"  Lotes questões: {selected_question_batches}")
    if selected_answer_batches:
        print(f"  Lotes gabaritos: {selected_answer_batches}")
    print()
    
    # Executar ingestão
    if process_questions:
        report = processor.run_full_ingestion(
            clear_db=clear_db,
            parallel=parallel,
            max_workers=max_workers,
            batch_size=batch_size,
            process_answers=process_answers,
            selected_question_batches=selected_question_batches,
            selected_answer_batches=selected_answer_batches
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
                max_workers=max_workers,
                selected_batches=selected_answer_batches
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
