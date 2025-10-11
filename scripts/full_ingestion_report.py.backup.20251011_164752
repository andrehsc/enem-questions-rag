#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de ingestao completa do ENEM RAG com relatorio detalhado.

Este script processa todos os arquivos de questoes (PV) e gabaritos (GB)
disponiveis e gera um relatorio completo com metricas de importacao.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import sys
import time
from datetime import datetime
import json

# Adicionar src ao path
sys.path.append('src')
sys.path.append('.')

from src.enem_ingestion.db_integration_final import DatabaseIntegration

class FullIngestionProcessor:
    """Processador completo de ingestao ENEM"""
    
    def __init__(self):
        self.connection_url = "postgresql://postgres:postgres123@localhost:5432/enem_rag"
        self.db_integration = DatabaseIntegration()
        self.report = {
            'start_time': datetime.now(),
            'end_time': None,
            'files_processed': {
                'questions': [],
                'answer_keys': []
            },
            'metrics': {
                'total_files_found': 0,
                'total_files_processed': 0,
                'total_questions_parsed': 0,
                'total_questions_inserted': 0,
                'total_alternatives_expected': 0,
                'total_alternatives_inserted': 0,
                'total_answer_keys_parsed': 0,
                'total_answer_keys_inserted': 0,
                'success_rate_questions': 0,
                'success_rate_alternatives': 0,
                'processing_time_seconds': 0
            },
            'errors': [],
            'by_year': {},
            'by_subject': {}
        }
    
    def get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def find_all_files(self):
        """Encontrar todos os arquivos PV (questoes) e GB (gabaritos)"""
        base_path = Path("data/downloads")
        
        question_files = list(base_path.glob("*/*PV*.pdf"))
        answer_files = list(base_path.glob("*/*GB*.pdf"))
        
        # Ordenar por ano e nome
        question_files.sort(key=lambda x: (x.parts[-2], x.name))
        answer_files.sort(key=lambda x: (x.parts[-2], x.name))
        
        return question_files, answer_files
    
    def clear_database(self):
        """Limpar banco de dados antes da ingestao completa"""
        print("Limpando banco de dados...")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM question_alternatives")
                cur.execute("DELETE FROM answer_keys")
                cur.execute("DELETE FROM questions")
                cur.execute("DELETE FROM exam_metadata")
            conn.commit()
        
        print("OK: Banco de dados limpo")
    
    def process_question_files(self, question_files):
        """Processar todos os arquivos de questoes"""
        print(f"\nProcessando {len(question_files)} arquivos de questoes...")
        
        processed = 0
        
        for i, file_path in enumerate(question_files, 1):
            print(f"\n[{i}/{len(question_files)}] Processando: {file_path.name}")
            
            try:
                result = self.db_integration.process_pdf_file(file_path)
                
                if result['success']:
                    questions_parsed = result.get('questions_parsed', 0)
                    questions_inserted = result.get('questions_inserted', 0)
                    
                    file_info = {
                        'filename': file_path.name,
                        'year': file_path.parts[-2],
                        'questions_parsed': questions_parsed,
                        'questions_inserted': questions_inserted,
                        'success': True
                    }
                    
                    self.report['files_processed']['questions'].append(file_info)
                    self.report['metrics']['total_questions_parsed'] += questions_parsed
                    self.report['metrics']['total_questions_inserted'] += questions_inserted
                    self.report['metrics']['total_alternatives_expected'] += questions_inserted * 5
                    
                    processed += 1
                    
                    print(f"  OK: {questions_inserted}/{questions_parsed} questoes importadas")
                    
                else:
                    error_info = {
                        'filename': file_path.name,
                        'error': result.get('error', 'Unknown error'),
                        'type': 'question_processing'
                    }
                    self.report['errors'].append(error_info)
                    print(f"  ERRO: {result.get('error', 'Unknown')}")
            
            except Exception as e:
                error_info = {
                    'filename': file_path.name,
                    'error': str(e),
                    'type': 'question_processing_exception'
                }
                self.report['errors'].append(error_info)
                print(f"  EXCECAO: {e}")
        
        self.report['metrics']['total_files_processed'] = processed
        print(f"\nArquivos de questoes processados: {processed}/{len(question_files)}")
    
    def process_answer_files(self, answer_files):
        """Processar todos os arquivos de gabaritos"""
        print(f"\nProcessando {len(answer_files)} arquivos de gabaritos...")
        
        # Importar o processador de gabaritos localmente
        import importlib.util
        spec = importlib.util.spec_from_file_location("process_answer_keys", "scripts/process_answer_keys.py")
        answer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(answer_module)
        AnswerKeyProcessor = answer_module.AnswerKeyProcessor
        
        answer_processor = AnswerKeyProcessor()
        processed = 0
        
        for i, file_path in enumerate(answer_files, 1):
            print(f"\n[{i}/{len(answer_files)}] Processando gabarito: {file_path.name}")
            
            try:
                inserted_count = answer_processor.process_answer_key_file(file_path)
                
                if inserted_count > 0:
                    file_info = {
                        'filename': file_path.name,
                        'year': file_path.parts[-2],
                        'answers_inserted': inserted_count,
                        'success': True
                    }
                    
                    self.report['files_processed']['answer_keys'].append(file_info)
                    self.report['metrics']['total_answer_keys_inserted'] += inserted_count
                    processed += 1
                    
                    print(f"  OK: {inserted_count} gabaritos importados")
                else:
                    print(f"  AVISO: Nenhum gabarito importado")
            
            except Exception as e:
                error_info = {
                    'filename': file_path.name,
                    'error': str(e),
                    'type': 'answer_processing_exception'
                }
                self.report['errors'].append(error_info)
                print(f"  EXCECAO: {e}")
        
        print(f"\nArquivos de gabaritos processados: {processed}/{len(answer_files)}")
    
    def calculate_final_metrics(self):
        """Calcular metricas finais do banco de dados"""
        print("\nCalculando metricas finais...")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Contar alternativas reais no banco
                cur.execute("SELECT COUNT(*) FROM question_alternatives")
                actual_alternatives = cur.fetchone()[0]
                self.report['metrics']['total_alternatives_inserted'] = actual_alternatives
                
                # Contar gabaritos reais
                cur.execute("SELECT COUNT(*) FROM answer_keys")
                actual_answers = cur.fetchone()[0]
                self.report['metrics']['total_answer_keys_parsed'] = actual_answers
                
                # Metricas por ano
                cur.execute("""
                    SELECT 
                        em.year,
                        COUNT(DISTINCT em.id) as files,
                        COUNT(q.id) as questions,
                        COUNT(qa.id) as alternatives,
                        COUNT(ak.id) as answers
                    FROM exam_metadata em
                    LEFT JOIN questions q ON em.id = q.exam_metadata_id
                    LEFT JOIN question_alternatives qa ON q.id = qa.question_id
                    LEFT JOIN answer_keys ak ON em.id = ak.exam_metadata_id
                    GROUP BY em.year
                    ORDER BY em.year
                """)
                
                for row in cur.fetchall():
                    self.report['by_year'][row['year']] = {
                        'files': row['files'],
                        'questions': row['questions'],
                        'alternatives': row['alternatives'],
                        'answers': row['answers']
                    }
                
                # Metricas por materia
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN subject LIKE '%LINGUAGENS%' THEN 'Linguagens'
                            WHEN subject LIKE '%HUMANAS%' THEN 'Ciencias Humanas'
                            WHEN subject LIKE '%NATUREZA%' THEN 'Ciencias da Natureza'
                            WHEN subject LIKE '%MATEMATICA%' THEN 'Matematica'
                            ELSE subject
                        END as materia,
                        COUNT(*) as questions
                    FROM questions
                    GROUP BY subject
                    ORDER BY questions DESC
                """)
                
                for row in cur.fetchall():
                    self.report['by_subject'][row['materia']] = row['questions']
        
        # Calcular taxas de sucesso
        if self.report['metrics']['total_questions_parsed'] > 0:
            self.report['metrics']['success_rate_questions'] = (
                self.report['metrics']['total_questions_inserted'] / 
                self.report['metrics']['total_questions_parsed'] * 100
            )
        
        if self.report['metrics']['total_alternatives_expected'] > 0:
            self.report['metrics']['success_rate_alternatives'] = (
                self.report['metrics']['total_alternatives_inserted'] / 
                self.report['metrics']['total_alternatives_expected'] * 100
            )
    
    def generate_report(self):
        """Gerar relatorio final detalhado"""
        self.report['end_time'] = datetime.now()
        self.report['metrics']['processing_time_seconds'] = (
            self.report['end_time'] - self.report['start_time']
        ).total_seconds()
        
        print("\n" + "=" * 80)
        print("RELATORIO FINAL DE INGESTAO ENEM RAG")
        print("=" * 80)
        
        # Resumo geral
        print(f"\nTEMPO DE PROCESSAMENTO: {self.report['metrics']['processing_time_seconds']:.1f} segundos")
        print(f"PERIODO: {self.report['start_time'].strftime('%Y-%m-%d %H:%M:%S')} - {self.report['end_time'].strftime('%H:%M:%S')}")
        
        # Metricas principais
        m = self.report['metrics']
        print(f"\nMETRICAS PRINCIPAIS:")
        print(f"   Arquivos encontrados: {len(self.report['files_processed']['questions']) + len(self.report['files_processed']['answer_keys'])}")
        print(f"   Arquivos processados: {m['total_files_processed']}")
        print(f"   Questoes parseadas: {m['total_questions_parsed']}")
        print(f"   Questoes inseridas: {m['total_questions_inserted']}")
        print(f"   Alternativas esperadas: {m['total_alternatives_expected']}")
        print(f"   Alternativas inseridas: {m['total_alternatives_inserted']}")
        print(f"   Gabaritos inseridos: {m['total_answer_keys_inserted']}")
        
        # Taxas de sucesso
        print(f"\nTAXAS DE SUCESSO:")
        print(f"   Questoes: {m['success_rate_questions']:.1f}%")
        print(f"   Alternativas: {m['success_rate_alternatives']:.1f}%")
        
        # Por ano
        print(f"\nDADOS POR ANO:")
        for year, data in self.report['by_year'].items():
            print(f"   {year}: {data['files']} arquivos, {data['questions']} questoes, {data['alternatives']} alternativas, {data['answers']} gabaritos")
        
        # Por materia
        print(f"\nDADOS POR MATERIA:")
        for subject, count in self.report['by_subject'].items():
            print(f"   {subject}: {count} questoes")
        
        # Erros
        if self.report['errors']:
            print(f"\nERROS ENCONTRADOS ({len(self.report['errors'])}):")
            for error in self.report['errors'][:10]:  # Mostrar so os primeiros 10
                print(f"   {error['filename']}: {error['error'][:60]}...")
        else:
            print(f"\nNENHUM ERRO ENCONTRADO!")
        
        # Salvar relatorio em JSON
        report_file = f"reports/ingestion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("reports").mkdir(exist_ok=True)
        
        # Converter datetime para string para JSON
        report_copy = self.report.copy()
        report_copy['start_time'] = self.report['start_time'].isoformat()
        report_copy['end_time'] = self.report['end_time'].isoformat()
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_copy, f, ensure_ascii=False, indent=2)
        
        print(f"\nRelatorio salvo em: {report_file}")
        print("=" * 80)
        
        return self.report
    
    def run_full_ingestion(self, clear_db=True):
        """Executar ingestao completa"""
        print("INICIANDO INGESTAO COMPLETA DO ENEM RAG")
        print("=" * 80)
        
        # Encontrar arquivos
        question_files, answer_files = self.find_all_files()
        self.report['metrics']['total_files_found'] = len(question_files) + len(answer_files)
        
        print(f"Arquivos encontrados:")
        print(f"   Questoes (PV): {len(question_files)}")
        print(f"   Gabaritos (GB): {len(answer_files)}")
        
        # Limpar banco se solicitado
        if clear_db:
            self.clear_database()
        
        # Processar questoes
        self.process_question_files(question_files)
        
        # Processar gabaritos
        self.process_answer_files(answer_files)
        
        # Calcular metricas finais
        self.calculate_final_metrics()
        
        # Gerar relatorio
        return self.generate_report()

if __name__ == "__main__":
    processor = FullIngestionProcessor()
    
    # Executar ingestao completa
    report = processor.run_full_ingestion(clear_db=True)
