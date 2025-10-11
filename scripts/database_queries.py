# -*- coding: utf-8 -*-
"""
Script com consultas SQL para visualizar dados completos do ENEM RAG.

Este script fornece várias views dos dados:
- Visão geral das questões
- Questões com alternativas 
- Questões com gabarito (quando disponível)
- Estatísticas detalhadas
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

class ENEMDataViewer:
    """Classe para visualizar dados do ENEM no banco"""
    
    def __init__(self):
        self.connection_url = "postgresql://enem_user:enem_password_2024@localhost:5432/enem_questions_rag"
    
    def get_connection(self):
        """Conectar ao banco"""
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def view_basic_stats(self):
        """Estatísticas básicas do banco de dados"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print("ESTATISTICAS BASICAS DO BANCO ENEM RAG")
                print("=" * 60)
                
                # Contadores básicos
                cur.execute("SELECT COUNT(*) as total FROM exam_metadata")
                meta_count = cur.fetchone()['total']
                
                cur.execute("SELECT COUNT(*) as total FROM questions")
                questions_count = cur.fetchone()['total']
                
                cur.execute("SELECT COUNT(*) as total FROM question_alternatives")
                alternatives_count = cur.fetchone()['total']
                
                cur.execute("SELECT COUNT(*) as total FROM answer_keys")
                answers_count = cur.fetchone()['total']
                
                print(f"Arquivos processados: {meta_count}")
                print(f"Total de questoes: {questions_count}")
                print(f"Total de alternativas: {alternatives_count}")
                print(f"Gabaritos disponiveis: {answers_count}")
                
                if questions_count > 0:
                    print(f"Media alternativas por questao: {alternatives_count/questions_count:.1f}")
                
                print()
                
                # Por ano
                cur.execute("""
                    SELECT year, COUNT(*) as arquivos
                    FROM exam_metadata 
                    GROUP BY year 
                    ORDER BY year
                """)
                print("Distribuicao por ano:")
                for row in cur.fetchall():
                    print(f"   {row['year']}: {row['arquivos']} arquivo(s)")
                
                print()
                
                # Por matéria
                cur.execute("""
                    SELECT subject, COUNT(*) as questoes
                    FROM questions 
                    GROUP BY subject 
                    ORDER BY questoes DESC
                """)
                print("Distribuicao por materia:")
                for row in cur.fetchall():
                    print(f"   {row['subject']}: {row['questoes']} questoes")
                
                print()
    
    def view_questions_with_alternatives(self, limit=5):
        """Visualizar questões completas com alternativas"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print(f"QUESTOES COMPLETAS COM ALTERNATIVAS (Primeiras {limit})")
                print("=" * 60)
                
                cur.execute("""
                    SELECT 
                        q.question_number,
                        q.subject,
                        q.question_text,
                        em.year,
                        em.day,
                        em.caderno
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    ORDER BY q.question_number
                    LIMIT %s
                """, (limit,))
                
                questions = cur.fetchall()
                
                for question in questions:
                    print(f"\nQUESTAO {question['question_number']}")
                    print(f"Materia: {question['subject']}")
                    print(f"Ano: {question['year']} | Dia: {question['day']} | Caderno: {question['caderno']}")
                    print(f"Texto: {question['question_text'][:200]}{'...' if len(question['question_text']) > 200 else ''}")
                    
                    # Buscar alternativas
                    cur.execute("""
                        SELECT alternative_letter, alternative_text
                        FROM question_alternatives
                        WHERE question_id = (
                            SELECT id FROM questions 
                            WHERE question_number = %s 
                            AND exam_metadata_id = (
                                SELECT id FROM exam_metadata 
                                WHERE year = %s AND day = %s AND caderno = %s
                            )
                        )
                        ORDER BY alternative_letter
                    """, (question['question_number'], question['year'], question['day'], question['caderno']))
                    
                    alternatives = cur.fetchall()
                    print("Alternativas:")
                    for alt in alternatives:
                        alt_text = alt['alternative_text'][:100] + '...' if len(alt['alternative_text']) > 100 else alt['alternative_text']
                        print(f"   {alt['alternative_letter']}) {alt_text}")
                    
                    print("-" * 50)
    
    def view_questions_with_answers(self, limit=10):
        """Visualizar questões com gabarito (quando disponível)"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print(f"QUESTOES COM GABARITO (Primeiras {limit})")
                print("=" * 60)
                
                cur.execute("""
                    SELECT 
                        q.question_number,
                        q.subject,
                        SUBSTR(q.question_text, 1, 150) as question_preview,
                        ak.correct_answer,
                        ak.language_option,
                        em.year,
                        em.day,
                        em.caderno
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN answer_keys ak ON ak.question_number = q.question_number 
                        AND ak.exam_metadata_id = em.id
                    WHERE ak.correct_answer IS NOT NULL
                    ORDER BY q.question_number
                    LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
                
                if not results:
                    print("AVISO: Nenhuma questao com gabarito encontrada.")
                    print("   (Gabaritos precisam ser processados separadamente)")
                    return
                
                for row in results:
                    print(f"\nQUESTAO {row['question_number']}")
                    print(f"Materia: {row['subject']}")
                    print(f"{row['year']} - Dia {row['day']} - {row['caderno']}")
                    print(f"Texto: {row['question_preview']}...")
                    print(f"Resposta Correta: {row['correct_answer']}")
                    if row['language_option']:
                        print(f"Idioma: {row['language_option']}")
                    print("-" * 40)
    
    def view_alternatives_distribution(self):
        """Distribuição das alternativas no banco"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print("DISTRIBUICAO DAS ALTERNATIVAS")
                print("=" * 60)
                
                cur.execute("""
                    SELECT 
                        alternative_letter,
                        COUNT(*) as quantidade,
                        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentual
                    FROM question_alternatives
                    GROUP BY alternative_letter
                    ORDER BY alternative_letter
                """)
                
                results = cur.fetchall()
                
                print("Distribuicao por letra:")
                for row in results:
                    bar = "=" * int(row['percentual'] / 2)  # Barra visual
                    print(f"   {row['alternative_letter']}: {row['quantidade']:4d} ({row['percentual']:5.1f}%) {bar}")
                
                print()
                
                # Questões com problemas nas alternativas
                cur.execute("""
                    SELECT 
                        q.question_number,
                        COUNT(qa.alternative_letter) as num_alternativas
                    FROM questions q
                    LEFT JOIN question_alternatives qa ON q.id = qa.question_id
                    GROUP BY q.id, q.question_number
                    HAVING COUNT(qa.alternative_letter) != 5
                    ORDER BY q.question_number
                    LIMIT 10
                """)
                
                problematic = cur.fetchall()
                if problematic:
                    print("AVISO: Questoes com numero incorreto de alternativas:")
                    for row in problematic:
                        print(f"   Questao {row['question_number']}: {row['num_alternativas']} alternativas")
                else:
                    print("OK: Todas as questoes tem exatamente 5 alternativas!")
                
                print()
    
    def view_sample_complete_question(self):
        """Mostrar uma questão completa como exemplo"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print("EXEMPLO DE QUESTAO COMPLETA")
                print("=" * 60)
                
                # Pegar uma questão aleatória
                cur.execute("""
                    SELECT 
                        q.id,
                        q.question_number,
                        q.question_text,
                        q.subject,
                        em.year,
                        em.day,
                        em.caderno,
                        em.pdf_filename
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    ORDER BY RANDOM()
                    LIMIT 1
                """)
                
                question = cur.fetchone()
                if not question:
                    print("ERRO: Nenhuma questao encontrada")
                    return
                
                print(f"QUESTAO {question['question_number']}")
                print(f"Materia: {question['subject']}")
                print(f"Fonte: {question['pdf_filename']}")
                print(f"Ano: {question['year']} | Dia: {question['day']} | Caderno: {question['caderno']}")
                print()
                print("ENUNCIADO:")
                print(f"   {question['question_text']}")
                print()
                
                # Buscar alternativas
                cur.execute("""
                    SELECT alternative_letter, alternative_text
                    FROM question_alternatives
                    WHERE question_id = %s
                    ORDER BY alternative_letter
                """, (question['id'],))
                
                alternatives = cur.fetchall()
                print("ALTERNATIVAS:")
                for alt in alternatives:
                    print(f"   {alt['alternative_letter']}) {alt['alternative_text']}")
                
                # Verificar se há gabarito
                cur.execute("""
                    SELECT correct_answer, language_option
                    FROM answer_keys 
                    WHERE question_number = %s 
                    AND exam_metadata_id = (
                        SELECT exam_metadata_id FROM questions WHERE id = %s
                    )
                """, (question['question_number'], question['id']))
                
                answer = cur.fetchone()
                if answer:
                    print()
                    print(f"GABARITO: {answer['correct_answer']}")
                    if answer['language_option']:
                        print(f"Idioma: {answer['language_option']}")
                else:
                    print()
                    print("AVISO: Gabarito nao disponivel")
                
                print()
    
    def view_consolidated_questions(self, limit=10):
        """View consolidada: questão + alternativas em uma só consulta"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print(f"VIEW CONSOLIDADA - QUESTOES + ALTERNATIVAS (Limit {limit})")
                print("=" * 60)
                
                cur.execute("""
                    SELECT 
                        q.question_number,
                        q.subject,
                        q.question_text,
                        em.year,
                        em.day,
                        em.caderno,
                        STRING_AGG(
                            qa.alternative_letter || ') ' || qa.alternative_text, 
                            E'\n' ORDER BY qa.alternative_letter
                        ) as all_alternatives,
                        ak.correct_answer
                    FROM questions q
                    JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN question_alternatives qa ON q.id = qa.question_id
                    LEFT JOIN answer_keys ak ON ak.question_number = q.question_number 
                        AND ak.exam_metadata_id = em.id
                    GROUP BY q.id, q.question_number, q.subject, q.question_text, 
                             em.year, em.day, em.caderno, ak.correct_answer
                    ORDER BY q.question_number
                    LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
                
                for row in results:
                    print(f"\n>>> QUESTAO {row['question_number']} <<<")
                    print(f"Materia: {row['subject']} | Ano: {row['year']} | Dia: {row['day']}")
                    print(f"Fonte: {row['caderno']}")
                    print()
                    print("ENUNCIADO:")
                    print(row['question_text'][:300] + ('...' if len(row['question_text']) > 300 else ''))
                    print()
                    print("ALTERNATIVAS:")
                    if row['all_alternatives']:
                        for alt in row['all_alternatives'].split('\n'):
                            print(f"   {alt}")
                    else:
                        print("   [Nenhuma alternativa encontrada]")
                    
                    if row['correct_answer']:
                        print(f"\nGABARITO: {row['correct_answer']}")
                    else:
                        print("\nGABARITO: Nao disponivel")
                    
                    print("=" * 60)
    
    def run_all_views(self):
        """Executar todas as visualizações"""
        print("EXECUTANDO TODAS AS CONSULTAS DO ENEM RAG")
        print("=" * 60)
        
        self.view_basic_stats()
        self.view_alternatives_distribution()
        self.view_sample_complete_question()
        self.view_questions_with_alternatives(3)
        self.view_questions_with_answers(5)
        self.view_consolidated_questions(2)
        
        print("\n" + "=" * 60)
        print("TODAS AS CONSULTAS EXECUTADAS COM SUCESSO!")
        print("=" * 60)

if __name__ == "__main__":
    viewer = ENEMDataViewer()
    
    # Executar todas as views
    viewer.run_all_views()
