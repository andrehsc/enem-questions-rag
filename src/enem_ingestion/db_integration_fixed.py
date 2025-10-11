import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from pathlib import Path
import logging
import re

from src.enem_ingestion.parser import EnemPDFParser

logger = logging.getLogger(__name__)

class DatabaseIntegration:
    """Database integration for ENEM questions"""
    
    def __init__(self):
        # Updated connection config
        self.connection_url = "postgresql://enem_user:enem_password_2024@localhost:5432/enem_questions_rag"
        self.connection = psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
        self.parser = EnemPDFParser()
        
    def __del__(self):
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
    
    def insert_exam_metadata(self, pdf_path):
        """Insert exam metadata with proper transaction handling"""
        try:
            pdf_filename = pdf_path.name
            
            # First, check and clean existing data
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM exam_metadata WHERE pdf_filename = %s", (pdf_filename,))
                existing = cur.fetchone()
                
                if existing:
                    exam_metadata_id = existing['id']
                    print(f"Cleaning existing data for {pdf_filename}")
                    
                    # Clean in correct order
                    cur.execute("DELETE FROM question_alternatives WHERE question_id IN (SELECT id FROM questions WHERE exam_metadata_id = %s)", (exam_metadata_id,))
                    cur.execute("DELETE FROM answer_keys WHERE exam_metadata_id = %s", (exam_metadata_id,))
                    cur.execute("DELETE FROM questions WHERE exam_metadata_id = %s", (exam_metadata_id,))
                    cur.execute("DELETE FROM exam_metadata WHERE id = %s", (exam_metadata_id,))
                    
                    # Commit cleanup
                    self.connection.commit()
                    print("Cleanup committed")
            
            # Now insert new data in fresh transaction
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                exam_metadata_id = str(uuid.uuid4())
                
                cur.execute("""
                    INSERT INTO exam_metadata (id, pdf_filename, file_path, processed_at, exam_year, exam_type, exam_day)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    exam_metadata_id,
                    pdf_filename,
                    str(pdf_path),
                    datetime.now(),
                    self._extract_year(pdf_filename),
                    self._extract_exam_type(pdf_filename),
                    self._extract_exam_day(pdf_filename)
                ))
                
                self.connection.commit()
                print(f"New metadata inserted with ID: {exam_metadata_id}")
                return exam_metadata_id
                
        except Exception as e:
            print(f"Error in insert_exam_metadata: {e}")
            self.connection.rollback()
            return None
    
    def insert_questions(self, questions, exam_metadata_id):
        """Insert questions with proper error handling"""
        inserted_count = 0
        
        try:
            for question in questions:
                try:
                    with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                        # Insert question
                        question_id = str(uuid.uuid4())
                        
                        cur.execute("""
                            INSERT INTO questions (id, exam_metadata_id, question_number, question_text, subject_area)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            question_id,
                            exam_metadata_id,
                            question['question_number'],
                            question['question_text'],
                            question.get('subject_area', 'General')
                        ))
                        
                        # Insert alternatives
                        for alt_letter, alt_text in question['alternatives'].items():
                            cur.execute("""
                                INSERT INTO question_alternatives (id, question_id, alternative_letter, alternative_text)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                str(uuid.uuid4()),
                                question_id,
                                alt_letter,
                                alt_text
                            ))
                        
                        # Commit each question individually
                        self.connection.commit()
                        inserted_count += 1
                        
                except Exception as e:
                    print(f"Error inserting question {question['question_number']}: {e}")
                    self.connection.rollback()
                    continue
                    
        except Exception as e:
            print(f"Error in insert_questions: {e}")
            self.connection.rollback()
            
        return inserted_count
    
    def process_pdf_file(self, pdf_path):
        """Process a PDF file completely"""
        try:
            print(f"Processing: {pdf_path.name}")
            
            # Parse questions
            questions = self.parser.parse_questions(pdf_path)
            print(f"Parsed {len(questions)} questions")
            
            if not questions:
                return {'success': False, 'error': 'No questions parsed'}
            
            # Insert metadata
            exam_metadata_id = self.insert_exam_metadata(pdf_path)
            if not exam_metadata_id:
                return {'success': False, 'error': 'Failed to insert metadata'}
            
            # Insert questions
            inserted_count = self.insert_questions(questions, exam_metadata_id)
            
            return {
                'success': True,
                'questions_parsed': len(questions),
                'questions_inserted': inserted_count
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_year(self, pdf_filename):
        match = re.search(r'(\d{4})', pdf_filename)
        return int(match.group(1)) if match else None
    
    def _extract_exam_type(self, pdf_filename):
        if 'PV' in pdf_filename:
            return 'Primeiro Dia'
        elif 'SV' in pdf_filename:
            return 'Segundo Dia'
        return 'Unknown'
    
    def _extract_exam_day(self, pdf_filename):
        if 'D1' in pdf_filename:
            return 1
        elif 'D2' in pdf_filename:
            return 2
        return None
