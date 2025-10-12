import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from pathlib import Path
import logging

from .parser import EnemPDFParser

logger = logging.getLogger(__name__)

class DatabaseIntegration:
    """Database integration for ENEM questions"""
    
    def __init__(self, connection_url=None):
        if connection_url:
            self.connection_url = connection_url
        else:
            self.connection_url = "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
        self.connection = psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
        self.parser = EnemPDFParser()
        
    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
    
    def insert_exam_metadata(self, pdf_path):
        """Insert exam metadata"""
        try:
            # Handle both string and Path objects
            if isinstance(pdf_path, str):
                pdf_filename = Path(pdf_path).name
            else:
                pdf_filename = pdf_path.name
            
            # Clean existing data
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM enem_questions.exam_metadata WHERE pdf_filename = %s", (pdf_filename,))
                existing = cur.fetchone()
                
                if existing:
                    exam_metadata_id = existing['id']
                    print(f"Cleaning existing data for {pdf_filename}")
                    
                    cur.execute("DELETE FROM enem_questions.question_alternatives WHERE question_id IN (SELECT id FROM enem_questions.questions WHERE exam_metadata_id = %s)", (exam_metadata_id,))
                    cur.execute("DELETE FROM enem_questions.answer_keys WHERE exam_metadata_id = %s", (exam_metadata_id,))
                    cur.execute("DELETE FROM enem_questions.questions WHERE exam_metadata_id = %s", (exam_metadata_id,))
                    cur.execute("DELETE FROM enem_questions.exam_metadata WHERE id = %s", (exam_metadata_id,))
                    
                    self.connection.commit()
                    print("Cleanup committed")
            
            # Parse metadata
            metadata = self.parser.parse_filename(pdf_filename)
            
            # Insert new data
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                exam_metadata_id = str(uuid.uuid4())
                
                cur.execute("""
                    INSERT INTO enem_questions.exam_metadata (
                        id, year, exam_type, application_type, language,
                        day, caderno, file_type, pdf_filename, pdf_path, 
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    exam_metadata_id,
                    metadata.year,
                    metadata.exam_type,
                    metadata.application_type,
                    metadata.language,
                    metadata.day,
                    metadata.caderno,
                    'caderno_questoes',
                    pdf_filename,
                    str(pdf_path),
                    datetime.now(),
                    datetime.now()
                ))
                
                self.connection.commit()
                print(f"New metadata inserted with ID: {exam_metadata_id}")
                return exam_metadata_id
                
        except Exception as e:
            print(f"Error in insert_exam_metadata: {e}")
            self.connection.rollback()
            return None
    
    def insert_questions(self, questions, exam_metadata_id):
        """Insert questions with correct schema including exam_id"""
        inserted_count = 0
        
        for question in questions:
            try:
                with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                    question_id = str(uuid.uuid4())
                    
                    # Generate sequential exam_id if not exists
                    cur.execute("SELECT COALESCE(MAX(exam_id), 0) + 1 AS next_id FROM enem_questions.questions")
                    result = cur.fetchone()
                    next_exam_id = result['next_id'] if result else 1
                    
                    # Use correct table schema with exam_id
                    cur.execute("""
                        INSERT INTO enem_questions.questions (
                            id, exam_id, question_number, question_text, subject, 
                            exam_metadata_id, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        question_id,
                        next_exam_id,
                        question.number,
                        question.text,
                        str(question.subject) if question.subject else 'General',
                        exam_metadata_id,
                        datetime.now(),
                        datetime.now()
                    ))
                    
                    # Insert alternatives
                    alternative_letters = ['A', 'B', 'C', 'D', 'E']
                    for i, alt_text in enumerate(question.alternatives):
                        if i < len(alternative_letters):
                            cur.execute("""
                                INSERT INTO enem_questions.question_alternatives (id, question_id, alternative_letter, alternative_text)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                str(uuid.uuid4()),
                                question_id,
                                alternative_letters[i],
                                alt_text
                            ))
                    
                    self.connection.commit()
                    inserted_count += 1
                    
            except Exception as e:
                print(f"Error inserting question {question.number}: {str(e)}")
                print(f"Question data: number={question.number}, text_len={len(question.text) if question.text else 0}, alternatives={len(question.alternatives) if question.alternatives else 0}")
                self.connection.rollback()
                continue
                
        return inserted_count
    
    def process_pdf_file(self, pdf_path):
        """Process PDF file"""
        try:
            # Log removido - já é feito no full_ingestion_report.py
            
            questions = self.parser.parse_questions(pdf_path)
            print(f"Parsed {len(questions)} questions")
            
            if not questions:
                return {'success': False, 'error': 'No questions parsed'}
            
            exam_metadata_id = self.insert_exam_metadata(pdf_path)
            if not exam_metadata_id:
                return {'success': False, 'error': 'Failed to insert metadata'}
            
            inserted_count = self.insert_questions(questions, exam_metadata_id)
            
            return {
                'success': True,
                'questions_parsed': len(questions),
                'questions_inserted': inserted_count
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
