#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Consulta Detalhada de Questões ENEM
Mostra todos os detalhes relacionados a uma questão específica.

EXEMPLOS DE USO:

1. Consultar questão por ID:
   python scripts/question_details.py --id "uuid-da-questao"

2. Consultar questão por número e caderno:
   python scripts/question_details.py --number 105 --caderno "CD5" --year 2024

3. Buscar questões por palavra-chave:
   python scripts/question_details.py --search "matemática função"

4. Listar questões com mais imagens:
   python scripts/question_details.py --top-images 10

5. Relatório completo de extração:
   python scripts/question_details.py --report
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
import sys
from pathlib import Path
import json
from datetime import datetime
from decimal import Decimal

class QuestionDetailsAnalyzer:
    """Analisador detalhado de questões ENEM"""
    
    def __init__(self):
        self.connection_url = "postgresql://postgres:postgres123@localhost:5433/teachershub_enem"
    
    def get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def get_question_by_id(self, question_id):
        """Buscar questão por ID UUID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            q.id,
                            q.question_number,
                            q.question_text,
                            q.context_text,
                            q.subject,
                            q.raw_text,
                            q.parsing_confidence,
                            q.has_images,
                            q.images_description,
                            q.created_at,
                            q.exam_metadata_id,
                            em.year,
                            em.day,
                            em.caderno,
                            em.application_type,
                            em.accessibility,
                            em.pdf_filename,
                            em.pdf_path,
                            em.pages_count
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        WHERE q.id = %s
                    """, (question_id,))
                    
                    question = cur.fetchone()
                    if not question:
                        return None
                    
                    # Buscar alternativas
                    cur.execute("""
                        SELECT 
                            alternative_letter,
                            alternative_text,
                            alternative_order
                        FROM enem_questions.question_alternatives
                        WHERE question_id = %s
                        ORDER BY alternative_order, alternative_letter
                    """, (question_id,))
                    
                    alternatives = cur.fetchall()
                    
                    # Buscar imagens
                    cur.execute("""
                        SELECT 
                            id,
                            image_sequence,
                            image_format,
                            image_width,
                            image_height,
                            image_size_bytes,
                            extracted_at
                        FROM enem_questions.question_images
                        WHERE question_id = %s
                        ORDER BY image_sequence
                    """, (question_id,))
                    
                    images = cur.fetchall()
                    
                    # Buscar gabarito (se existir)
                    cur.execute("""
                        SELECT 
                            correct_answer,
                            language_option
                        FROM enem_questions.answer_keys
                        WHERE exam_metadata_id = %s 
                        AND question_number = %s
                    """, (question['exam_metadata_id'], question['question_number']))
                    
                    answer_key = cur.fetchone()
                    
                    return {
                        'question': dict(question),
                        'alternatives': [dict(alt) for alt in alternatives],
                        'images': [dict(img) for img in images],
                        'answer_key': dict(answer_key) if answer_key else None
                    }
                    
        except Exception as e:
            print(f"Erro ao buscar questão: {e}")
            return None
    
    def find_questions_by_criteria(self, number=None, caderno=None, year=None, day=None):
        """Buscar questões por critérios"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    conditions = []
                    params = []
                    
                    if number is not None:
                        conditions.append("q.question_number = %s")
                        params.append(number)
                    
                    if caderno is not None:
                        conditions.append("em.caderno = %s")
                        params.append(caderno)
                    
                    if year is not None:
                        conditions.append("em.year = %s")
                        params.append(year)
                    
                    if day is not None:
                        conditions.append("em.day = %s")
                        params.append(day)
                    
                    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                    
                    cur.execute(f"""
                        SELECT 
                            q.id,
                            q.question_number,
                            em.year,
                            em.day,
                            em.caderno,
                            em.application_type,
                            q.subject,
                            q.parsing_confidence,
                            q.has_images,
                            COUNT(qi.id) as image_count,
                            COUNT(qa.id) as alternatives_count
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        LEFT JOIN enem_questions.question_images qi ON qi.question_id = q.id
                        LEFT JOIN enem_questions.question_alternatives qa ON qa.question_id = q.id
                        {where_clause}
                        GROUP BY q.id, q.question_number, em.year, em.day, em.caderno, em.application_type, q.subject, q.parsing_confidence, q.has_images
                        ORDER BY em.year DESC, em.day, em.caderno, q.question_number
                    """, params)
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"Erro ao buscar questões: {e}")
            return []
    
    def search_questions_by_text(self, search_term):
        """Buscar questões por texto"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            q.id,
                            q.question_number,
                            em.year,
                            em.day,
                            em.caderno,
                            q.subject,
                            q.question_text as preview,
                            q.parsing_confidence
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        WHERE 
                            q.question_text ILIKE %s
                            OR q.context_text ILIKE %s
                        ORDER BY em.year DESC
                        LIMIT 50
                    """, (f"%{search_term}%", f"%{search_term}%"))
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"Erro na busca textual: {e}")
            return []
    
    def get_top_questions_by_images(self, limit=10):
        """Questões com mais imagens"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            q.id,
                            q.question_number,
                            em.year,
                            em.day,
                            em.caderno,
                            q.subject,
                            COUNT(qi.id) as image_count,
                            SUM(qi.image_size_bytes) as total_size_bytes,
                            ROUND(AVG(qi.image_size_bytes)/1024.0, 2) as avg_size_kb
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        LEFT JOIN enem_questions.question_images qi ON qi.question_id = q.id
                        WHERE qi.id IS NOT NULL
                        GROUP BY q.id, q.question_number, em.year, em.day, em.caderno, q.subject
                        ORDER BY COUNT(qi.id) DESC, SUM(qi.image_size_bytes) DESC
                        LIMIT %s
                    """, (limit,))
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"Erro ao buscar questões com imagens: {e}")
            return []
    
    def generate_extraction_report(self):
        """Gerar relatório completo da extração"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Estatísticas gerais
                    cur.execute("""
                        SELECT 
                            COUNT(DISTINCT em.id) as total_exams,
                            COUNT(DISTINCT q.id) as total_questions,
                            COUNT(DISTINCT qa.id) as total_alternatives,
                            COUNT(DISTINCT qi.id) as total_images,
                            ROUND(AVG(q.parsing_confidence), 3) as avg_confidence,
                            SUM(qi.image_size_bytes) as total_image_size
                        FROM enem_questions.exam_metadata em
                        LEFT JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                        LEFT JOIN enem_questions.question_alternatives qa ON qa.question_id = q.id
                        LEFT JOIN enem_questions.question_images qi ON qi.question_id = q.id
                    """)
                    
                    stats_row = cur.fetchone()
                    stats = {}
                    for key, value in stats_row.items():
                        if isinstance(value, Decimal):
                            stats[key] = float(value)
                        else:
                            stats[key] = value
                    
                    # Por dia e caderno
                    cur.execute("""
                        SELECT 
                            em.year,
                            em.day,
                            em.caderno,
                            em.application_type,
                            COUNT(q.id) as questions,
                            COUNT(qi.id) as images,
                            ROUND(AVG(q.parsing_confidence), 3) as avg_confidence
                        FROM enem_questions.exam_metadata em
                        LEFT JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                        LEFT JOIN enem_questions.question_images qi ON qi.question_id = q.id
                        GROUP BY em.year, em.day, em.caderno, em.application_type
                        ORDER BY em.year, em.day, em.caderno
                    """)
                    
                    by_caderno = []
                    for row in cur.fetchall():
                        caderno_data = {}
                        for key, value in row.items():
                            if isinstance(value, Decimal):
                                caderno_data[key] = float(value)
                            else:
                                caderno_data[key] = value
                        by_caderno.append(caderno_data)
                    
                    return {
                        'statistics': stats,
                        'by_caderno': by_caderno,
                        'generated_at': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return None
    
    def display_question_details(self, question_data):
        """Exibir detalhes formatados de uma questão"""
        if not question_data:
            print("Questão não encontrada.")
            return
        
        q = question_data['question']
        
        print("=" * 80)
        print(f"QUESTÃO {q['question_number']} - {q['year']} - DIA {q['day']} - {q['caderno']}")
        print("=" * 80)
        print(f"ID: {q['id']}")
        print(f"Arquivo: {q['pdf_filename']}")
        print(f"Tipo: {q['application_type']}")
        if q['accessibility']:
            print(f"Acessibilidade: {q['accessibility']}")
        print(f"Matéria: {q['subject']}")
        print(f"Confiança: {q['parsing_confidence']:.3f}")
        print(f"Tem imagens: {'Sim' if q['has_images'] else 'Não'}")
        print(f"Criado em: {q['created_at']}")
        
        print("\n" + "-" * 50)
        print("ENUNCIADO:")
        print("-" * 50)
        print(q['question_text'])
        
        if q['context_text']:
            print("\n" + "-" * 30)
            print("CONTEXTO:")
            print("-" * 30)
            print(q['context_text'])
        
        print("\n" + "-" * 30)
        print("ALTERNATIVAS:")
        print("-" * 30)
        for alt in question_data['alternatives']:
            print(f"{alt['alternative_letter']}) {alt['alternative_text']}")
        
        if question_data['answer_key']:
            ak = question_data['answer_key']
            print(f"\n🔑 GABARITO: {ak['correct_answer']}")
            if ak['language_option']:
                print(f"   Idioma: {ak['language_option']}")
        
        if question_data['images']:
            print("\n" + "-" * 30)
            print("IMAGENS:")
            print("-" * 30)
            total_size = sum(img['image_size_bytes'] for img in question_data['images'])
            print(f"Total: {len(question_data['images'])} imagens ({total_size/1024:.1f} KB)")
            
            for img in question_data['images'][:3]:  # Mostrar apenas as 3 primeiras
                size_kb = img['image_size_bytes'] / 1024
                print(f"  #{img['image_sequence']}: {img['image_format']} - {img['image_width']}x{img['image_height']} - {size_kb:.1f}KB")
            
            if len(question_data['images']) > 3:
                print(f"  ... e mais {len(question_data['images']) - 3} imagens")


def main():
    parser = argparse.ArgumentParser(description='Consulta Detalhada de Questões ENEM')
    
    parser.add_argument('--id', type=str, help='ID UUID da questão')
    parser.add_argument('--number', type=int, help='Número da questão')
    parser.add_argument('--caderno', type=str, help='Caderno (ex: CD5)')
    parser.add_argument('--year', type=int, help='Ano do exame')
    parser.add_argument('--day', type=int, help='Dia do exame (1 ou 2)')
    parser.add_argument('--search', type=str, help='Buscar por texto')
    parser.add_argument('--top-images', type=int, help='Top N questões com mais imagens')
    parser.add_argument('--report', action='store_true', help='Gerar relatório completo')
    
    args = parser.parse_args()
    
    analyzer = QuestionDetailsAnalyzer()
    
    if args.report:
        print("Gerando relatório de extração...")
        report = analyzer.generate_extraction_report()
        if report:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    
    if args.id:
        question_data = analyzer.get_question_by_id(args.id)
        analyzer.display_question_details(question_data)
        return
    
    if args.search:
        print(f"Buscando questões por: '{args.search}'")
        results = analyzer.search_questions_by_text(args.search)
        if results:
            for i, q in enumerate(results, 1):
                print(f"{i}. Q{q['question_number']} ({q['year']} - {q['caderno']}) - {q['subject']}")
                print(f"   Enunciado: {q['preview']}")
                print(f"   ID: {q['id']}")
                print("-" * 80)
        else:
            print("Nenhuma questão encontrada.")
        return
    
    if args.top_images:
        print(f"Top {args.top_images} questões com mais imagens:")
        results = analyzer.get_top_questions_by_images(args.top_images)
        for i, q in enumerate(results, 1):
            print(f"{i}. Q{q['question_number']} ({q['year']} - {q['caderno']}) - {q['subject']}")
            print(f"   Imagens: {q['image_count']} ({q['total_size_bytes']/1024:.1f} KB total)")
            print(f"   Média: {q['avg_size_kb']} KB por imagem")
            print(f"   ID: {q['id']}")
            print()
        return
    
    if any([args.number is not None, args.caderno, args.year, args.day]):
        results = analyzer.find_questions_by_criteria(
            number=args.number,
            caderno=args.caderno, 
            year=args.year,
            day=args.day
        )
        
        if results:
            if len(results) == 1:
                # Se só uma questão, mostrar detalhes completos
                question_data = analyzer.get_question_by_id(results[0]['id'])
                analyzer.display_question_details(question_data)
            else:
                # Se múltiplas questões, mostrar lista
                print(f"Encontradas {len(results)} questões:")
                for q in results:
                    print(f"- Q{q['question_number']} ({q['year']} - {q['caderno']}) - {q['subject']} - ID: {q['id']}")
        else:
            print("Nenhuma questão encontrada com os critérios especificados.")
        return
    
    # Se nenhum argumento, mostrar ajuda
    parser.print_help()


if __name__ == "__main__":
    main()