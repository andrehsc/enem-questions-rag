#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço de database para API ENEM Questions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict, Any, Tuple
import os
from contextlib import contextmanager
import math

class DatabaseService:
    """Serviço de acesso ao banco de dados"""
    
    def __init__(self):
        self.connection_url = os.getenv(
            'DATABASE_URL',
            'postgresql://enem_user:enem_password_2024@localhost:5432/enem_questions_rag'
        )
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões com o banco"""
        conn = psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
        try:
            yield conn
        finally:
            conn.close()
    
    def health_check(self) -> Tuple[bool, int]:
        """Verificar se o banco está acessível e retornar total de questões"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM questions")
                    result = cur.fetchone()
                    return True, result['count']
        except Exception:
            return False, 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas da base de dados"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Contadores principais
                cur.execute("SELECT COUNT(*) as count FROM questions")
                total_questions = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM question_alternatives")
                total_alternatives = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM answer_keys")
                total_answer_keys = cur.fetchone()['count']
                
                # Questões por ano
                cur.execute("""
                    SELECT em.year, COUNT(q.id) as count
                    FROM exam_metadata em
                    LEFT JOIN questions q ON em.id = q.exam_metadata_id
                    GROUP BY em.year
                    ORDER BY em.year
                """)
                questions_by_year = {row['year']: row['count'] for row in cur.fetchall()}
                
                # Questões por matéria
                cur.execute("""
                    SELECT 
                        CASE 
                            WHEN subject LIKE '%LINGUAGENS%' THEN 'Linguagens'
                            WHEN subject LIKE '%HUMANAS%' THEN 'Ciências Humanas'
                            WHEN subject LIKE '%NATUREZA%' THEN 'Ciências da Natureza'
                            WHEN subject LIKE '%MATEMATICA%' THEN 'Matemática'
                            ELSE subject
                        END as subject_clean,
                        COUNT(*) as count
                    FROM questions
                    GROUP BY subject
                    ORDER BY count DESC
                """)
                questions_by_subject = {row['subject_clean']: row['count'] for row in cur.fetchall()}
                
                # Distribuição de respostas
                cur.execute("""
                    SELECT correct_answer, COUNT(*) as count
                    FROM answer_keys
                    GROUP BY correct_answer
                    ORDER BY correct_answer
                """)
                answer_distribution = {row['correct_answer']: row['count'] for row in cur.fetchall()}
                
                return {
                    'total_questions': total_questions,
                    'total_alternatives': total_alternatives,
                    'total_answer_keys': total_answer_keys,
                    'questions_by_year': questions_by_year,
                    'questions_by_subject': questions_by_subject,
                    'answer_distribution': answer_distribution
                }
    
    def get_questions_summary(self, page: int = 1, size: int = 20, 
                            year: Optional[int] = None, 
                            subject: Optional[str] = None,
                            caderno: Optional[str] = None) -> Tuple[List[Dict], int]:
        """Obter resumo paginado das questões"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Construir WHERE clause
                where_conditions = []
                params = []
                
                if year:
                    where_conditions.append("em.year = %s")
                    params.append(year)
                
                if subject:
                    where_conditions.append("q.subject ILIKE %s")
                    params.append(f"%{subject}%")
                
                if caderno:
                    where_conditions.append("em.caderno = %s")
                    params.append(caderno)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                # Query principal
                query = f"""
                    SELECT 
                        q.id,
                        q.question_number,
                        q.subject,
                        em.year,
                        em.day,
                        em.caderno,
                        ak.correct_answer,
                        LEFT(q.statement, 100) as statement_preview
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN answer_keys ak ON em.id = ak.exam_metadata_id AND q.question_number = ak.question_number
                    {where_clause}
                    ORDER BY em.year DESC, em.day, em.caderno, q.question_number
                    LIMIT %s OFFSET %s
                """
                
                offset = (page - 1) * size
                params.extend([size, offset])
                
                cur.execute(query, params)
                questions = cur.fetchall()
                
                # Contar total
                count_query = f"""
                    SELECT COUNT(*) as count
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    {where_clause}
                """
                
                cur.execute(count_query, params[:-2])  # Remove LIMIT e OFFSET params
                total = cur.fetchone()['count']
                
                return questions, total
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """Obter questão completa por ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Questão com metadados
                cur.execute("""
                    SELECT 
                        q.*,
                        em.id as metadata_id,
                        em.year,
                        em.day,
                        em.caderno,
                        em.application_type,
                        em.accessibility,
                        em.file_type,
                        em.pdf_filename,
                        em.pdf_path,
                        em.file_size,
                        em.pages_count,
                        em.created_at as metadata_created_at,
                        em.updated_at as metadata_updated_at
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    WHERE q.id = %s
                """, (question_id,))
                
                question = cur.fetchone()
                if not question:
                    return None
                
                # Alternativas
                cur.execute("""
                    SELECT id, letter, text, alternative_order
                    FROM question_alternatives
                    WHERE question_id = %s
                    ORDER BY alternative_order
                """, (question_id,))
                
                alternatives = cur.fetchall()
                
                # Gabarito
                cur.execute("""
                    SELECT id, question_number, correct_answer, subject, language_option
                    FROM answer_keys
                    WHERE exam_metadata_id = %s AND question_number = %s
                """, (question['metadata_id'], question['question_number']))
                
                answer_key = cur.fetchone()
                
                return {
                    'question': question,
                    'alternatives': alternatives,
                    'answer_key': answer_key
                }
    
    def search_questions(self, query: str, page: int = 1, size: int = 20) -> Tuple[List[Dict], int]:
        """Buscar questões por texto"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                search_query = f"""
                    SELECT 
                        q.id,
                        q.question_number,
                        q.subject,
                        em.year,
                        em.day,
                        em.caderno,
                        ak.correct_answer,
                        LEFT(q.statement, 100) as statement_preview,
                        ts_rank(to_tsvector('portuguese', q.statement), plainto_tsquery('portuguese', %s)) as rank
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN answer_keys ak ON em.id = ak.exam_metadata_id AND q.question_number = ak.question_number
                    WHERE to_tsvector('portuguese', q.statement) @@ plainto_tsquery('portuguese', %s)
                    ORDER BY rank DESC, em.year DESC, q.question_number
                    LIMIT %s OFFSET %s
                """
                
                offset = (page - 1) * size
                cur.execute(search_query, (query, query, size, offset))
                questions = cur.fetchall()
                
                # Contar total
                count_query = """
                    SELECT COUNT(*) as count
                    FROM questions q
                    WHERE to_tsvector('portuguese', q.statement) @@ plainto_tsquery('portuguese', %s)
                """
                
                cur.execute(count_query, (query,))
                total = cur.fetchone()['count']
                
                return questions, total
