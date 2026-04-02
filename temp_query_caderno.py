import psycopg2
from psycopg2.extras import RealDictCursor

connection_url = 'postgresql://postgres:postgres123@localhost:5433/teachershub_enem'

try:
    with psycopg2.connect(connection_url, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            # Query completa para todas as questoes do caderno com resumos
            cur.execute("""
                SELECT 
                    q.id,
                    q.question_number,
                    q.subject,
                    q.competency,
                    q.skill,
                    q.difficulty_level,
                    q.correct_answer,
                    q.question_text,
                    q.explanation,
                    CASE WHEN q.image_path IS NOT NULL AND q.image_path != '' THEN true ELSE false END as has_images,
                    em.year,
                    em.day,
                    em.caderno,
                    em.application_type,
                    em.language,
                    em.exam_type,
                    em.pdf_filename,
                    -- Criar um resumo da questao (primeiras 200 caracteres)
                    LEFT(q.question_text, 200) || '...' as question_summary,
                    -- Contar alternativas
                    (SELECT COUNT(*) FROM enem_questions.question_alternatives qa 
                     WHERE qa.question_id = q.id) as alternatives_count,
                    -- Buscar resposta correta das alternativas se disponivel
                    (SELECT ak.correct_answer 
                     FROM enem_questions.answer_keys ak 
                     WHERE ak.exam_metadata_id = em.id 
                     AND ak.question_number = q.question_number 
                     LIMIT 1) as answer_key
                FROM enem_questions.questions q
                JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                WHERE em.pdf_filename = %s
                ORDER BY q.question_number
            """, ('2020_PV_impresso_D1_CD1.pdf',))
            
            questions = cur.fetchall()
            
            print('=' * 80)
            print('CADERNO: 2020_PV_impresso_D1_CD1.pdf')
            print('TOTAL DE QUESTOES: ' + str(len(questions)))
            print('=' * 80)
            
            for q in questions:
                print('\n* QUESTAO ' + str(q["question_number"]) + ' - ' + str(q["subject"]))
                print('   ID: ' + str(q["id"]))
                if q['competency']:
                    print('   Competencia: ' + str(q["competency"]))
                if q['skill']:
                    print('   Habilidade: ' + str(q["skill"]))
                if q['difficulty_level']:
                    print('   Dificuldade: ' + str(q["difficulty_level"]))
                if q['answer_key']:
                    print('   Resposta: ' + str(q["answer_key"]))
                elif q['correct_answer']:
                    print('   Resposta: ' + str(q["correct_answer"]))
                print('   Alternativas: ' + str(q["alternatives_count"]))
                print('   Tem imagens: ' + ('Sim' if q["has_images"] else 'Nao'))
                print('   ')
                print('   >> RESUMO: ' + str(q["question_summary"]))
                if q['explanation']:
                    print('   ')
                    print('   >> EXPLICACAO: ' + str(q["explanation"][:200]) + '...')
                print('   ' + '-' * 70)
                
        print('\n[OK] Total processado: ' + str(len(questions)) + ' questoes')
        
except Exception as e:
    print('[ERRO] ' + str(e))
