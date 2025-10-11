"""
Database integration module for ENEM Questions RAG.

This module handles the integ                        # Clean existing data for reprocessing in a separate transaction
                        cur.execute("DELETE FROM question_alternatives WHERE question_id IN (SELECT id FROM questions WHERE exam_metadata_id = %s)", (existing_id,))
                        deleted_alts = cur.rowcount
                        cur.execute("DELETE FROM answer_keys WHERE exam_metadata_id = %s", (existing_id,))
                        deleted_answers = cur.rowcount
                        cur.execute("DELETE FROM questions WHERE exam_metadata_id = %s", (existing_id,))
                        deleted_questions = cur.rowcount
                        
                        # Commit the cleanup
                        conn.commit()
                        
                        logger.info(f"Cleaned {deleted_questions} questions, {deleted_alts} alternatives, {deleted_answers} answers")
                        return existing_idween the PDF parser and PostgreSQL database,
providing methods to store parsed questions, answers, and metadata.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import uuid
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import dotenv

from .parser import (
    EnemPDFParser, QuestionMetadata, AnswerKey, Question, 
    ExamType, Subject, LanguageOption
)

# Load environment variables
dotenv.load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseIntegration:
    """Database integration for ENEM Questions RAG."""
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize database integration.
        
        Args:
            connection_url: PostgreSQL connection URL. If None, uses DATABASE_URL from env.
        """
        self.connection_url = connection_url or os.getenv('DATABASE_URL')
        if not self.connection_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self.parser = EnemPDFParser()
        
    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor)
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def insert_exam_metadata(self, metadata: QuestionMetadata, file_path: Path, 
                           file_type: ExamType) -> str:
        """
        Insert exam metadata into database.
        
        Args:
            metadata: Question metadata
            file_path: Path to PDF file
            file_type: Type of exam file (caderno_questoes or gabarito)
            
        Returns:
            UUID of inserted metadata record
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if file already exists
                    cur.execute("""
                        SELECT id FROM exam_metadata 
                        WHERE pdf_filename = %s
                    """, (file_path.name,))
                    
                    existing = cur.fetchone()
                    if existing:
                        existing_id = existing['id']  # RealDictCursor returns dict-like object
                        logger.info(f"Metadata for {file_path.name} already exists, will clean existing data")
                        
                        # Clean existing data for reprocessing
                        cur.execute("DELETE FROM question_alternatives WHERE question_id IN (SELECT id FROM questions WHERE exam_metadata_id = %s)", (existing_id,))
                        deleted_alts = cur.rowcount
                        cur.execute("DELETE FROM answer_keys WHERE exam_metadata_id = %s", (existing_id,))
                        deleted_answers = cur.rowcount
                        cur.execute("DELETE FROM questions WHERE exam_metadata_id = %s", (existing_id,))
                        deleted_questions = cur.rowcount
                        
                        logger.info(f"Cleaned {deleted_questions} questions, {deleted_alts} alternatives, {deleted_answers} answers")
                        
                        logger.info(f"Cleaned existing data for metadata {existing_id}")
                        return existing_id
                    
                    # Get file stats
                    file_size = file_path.stat().st_size if file_path.exists() else None
                    
                    # Insert new metadata
                    metadata_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO exam_metadata (
                            id, year, day, caderno, application_type, accessibility,
                            file_type, pdf_filename, pdf_path, file_size, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                    """, (
                        metadata_id,
                        metadata.year,
                        metadata.day,
                        metadata.caderno,
                        metadata.application_type,
                        metadata.accessibility,
                        file_type.value,
                        file_path.name,
                        str(file_path),
                        file_size
                    ))
                    
                    logger.info(f"Inserted metadata for {file_path.name}: {metadata_id}")
                    return metadata_id
                    
        except Exception as e:
            logger.error(f"Error inserting exam metadata: {e}")
            raise
    
    def insert_answer_keys(self, answer_keys: List[AnswerKey], metadata_id: str) -> int:
        """
        Insert answer keys into database.
        
        Args:
            answer_keys: List of answer keys
            metadata_id: ID of associated exam metadata
            
        Returns:
            Number of inserted answer keys
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Clear existing answer keys for this exam
                    cur.execute("""
                        DELETE FROM answer_keys WHERE exam_metadata_id = %s
                    """, (metadata_id,))
                    
                    inserted_count = 0
                    for answer_key in answer_keys:
                        try:
                            cur.execute("""
                                INSERT INTO answer_keys (
                                    id, question_number, correct_answer, subject,
                                    language_option, exam_metadata_id, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, NOW()
                                )
                            """, (
                                str(uuid.uuid4()),
                                answer_key.question_number,
                                answer_key.correct_answer,
                                answer_key.subject.value if answer_key.subject else None,
                                answer_key.language_option.value if answer_key.language_option else None,
                                metadata_id
                            ))
                            inserted_count += 1
                        except Exception as e:
                            logger.warning(f"Error inserting answer key {answer_key.question_number}: {e}")
                    
                    logger.info(f"Inserted {inserted_count} answer keys for metadata {metadata_id}")
                    return inserted_count
                    
        except Exception as e:
            logger.error(f"Error inserting answer keys: {e}")
            raise
    
    def insert_questions(self, questions: List[Question], metadata_id: str) -> int:
        """
        Insert questions and alternatives into database.
        
        Args:
            questions: List of questions
            metadata_id: ID of associated exam metadata
            
        Returns:
            Number of inserted questions
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    inserted_count = 0
                    for question in questions:
                        try:
                            # Insert question
                            question_id = str(uuid.uuid4())
                            cur.execute("""
                                INSERT INTO questions (
                                    id, question_number, question_text, context_text,
                                    subject, exam_metadata_id, raw_text, parsing_confidence,
                                    has_images, images_description, created_at, updated_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                                )
                            """, (
                                question_id,
                                question.number,
                                question.text,
                                question.context,
                                question.subject.value if question.subject else None,
                                metadata_id,
                                question.text,  # Using text as raw_text for now
                                0.8,  # Default confidence
                                len(question.alternatives) == 0,  # Assume no images if no alternatives
                                None
                            ))
                            
                            # Insert alternatives with duplicate prevention
                            inserted_letters = set()
                            
                            for i, alternative in enumerate(question.alternatives):
                                if alternative and len(alternative) > 3:
                                    # Extract letter and text from alternative
                                    alt_letter = None
                                    alt_text = None
                                    
                                    # Try different formats: "A) text", "A text", "A: text"
                                    import re
                                    match = re.match(r'^([A-E])\s*[\)\:\.\-\s]\s*(.+)', alternative)
                                    if match:
                                        alt_letter = match.group(1)
                                        alt_text = match.group(2).strip()
                                    else:
                                        # Fallback: assume first char is letter if it's A-E
                                        if alternative[0] in 'ABCDE':
                                            alt_letter = alternative[0]
                                            alt_text = alternative[1:].strip().lstrip('):.- ')
                                    
                                    # Insert if we have valid data and letter not already inserted
                                    if (alt_letter and alt_text and len(alt_text) > 3 and 
                                        alt_letter not in inserted_letters):
                                        
                                        cur.execute("""
                                            INSERT INTO question_alternatives (
                                                id, question_id, alternative_letter,
                                                alternative_text, alternative_order, created_at
                                            ) VALUES (
                                                %s, %s, %s, %s, %s, NOW()
                                            )
                                        """, (
                                            str(uuid.uuid4()),
                                            question_id,
                                            alt_letter,
                                            alt_text,
                                            i
                                        ))
                                        inserted_letters.add(alt_letter)
                            
                            inserted_count += 1
                            logger.debug(f"Successfully inserted question {question.number}")
                            
                        except Exception as e:
                            logger.warning(f"Error inserting question {question.number}: {e}")
                            continue
                    
                    # Commit the transaction
                    conn.commit()
                    logger.info(f"Inserted {inserted_count} questions for metadata {metadata_id}")
                    return inserted_count
                    
        except Exception as e:
            logger.error(f"Error inserting questions: {e}")
            raise
    
    def process_pdf_file(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Process a PDF file and store all data in database.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing PDF file: {pdf_path}")
        
        try:
            # Parse the file
            parsed_data = self.parser.parse_file(pdf_path)
            file_type = parsed_data['type']
            data = parsed_data['data']
            metadata = parsed_data['metadata']
            
            # Insert metadata
            metadata_id = self.insert_exam_metadata(metadata, pdf_path, file_type)
            
            result = {
                'file_path': str(pdf_path),
                'file_type': file_type.value,
                'metadata_id': metadata_id,
                'success': True
            }
            
            if file_type == ExamType.GABARITO:
                # Process answer keys
                answer_count = self.insert_answer_keys(data, metadata_id)
                result['answer_keys_inserted'] = answer_count
                
            elif file_type == ExamType.CADERNO_QUESTOES:
                # Process questions
                question_count = self.insert_questions(data, metadata_id)
                result['questions_inserted'] = question_count
            
            logger.info(f"Successfully processed {pdf_path}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF file {pdf_path}: {e}")
            return {
                'file_path': str(pdf_path),
                'success': False,
                'error': str(e)
            }
    
    def process_directory(self, directory_path: Path) -> Dict[str, Any]:
        """
        Process all PDF files in a directory and subdirectories.
        
        Args:
            directory_path: Path to directory containing PDFs
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing directory: {directory_path}")
        
        pdf_files = list(directory_path.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        results = {
            'total_files': len(pdf_files),
            'processed_files': 0,
            'successful': 0,
            'failed': 0,
            'gabaritos': 0,
            'cadernos': 0,
            'total_questions': 0,
            'total_answers': 0,
            'file_results': []
        }
        
        for pdf_file in pdf_files:
            result = self.process_pdf_file(pdf_file)
            results['file_results'].append(result)
            results['processed_files'] += 1
            
            if result['success']:
                results['successful'] += 1
                
                if 'answer_keys_inserted' in result:
                    results['gabaritos'] += 1
                    results['total_answers'] += result['answer_keys_inserted']
                
                if 'questions_inserted' in result:
                    results['cadernos'] += 1
                    results['total_questions'] += result['questions_inserted']
            else:
                results['failed'] += 1
        
        logger.info(f"Directory processing complete: {results}")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Use our custom function
                    cur.execute("SELECT * FROM get_parsing_stats()")
                    stats = cur.fetchone()
                    
                    return {
                        'total_exams': stats['total_exams'],
                        'total_questions': stats['total_questions'],
                        'total_alternatives': stats['total_alternatives'],
                        'avg_confidence': float(stats['avg_confidence']) if stats['avg_confidence'] else 0.0,
                        'questions_with_images': stats['questions_with_images'],
                        'years_covered': stats['years_covered']
                    }
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def search_questions(self, search_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search questions using full-text search.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching questions
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM find_similar_questions(%s, %s)", 
                              (search_text, limit))
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            'question_id': row['question_id'],
                            'question_number': row['question_number'],
                            'question_text': row['question_text'],
                            'subject': row['subject'],
                            'year': row['year'],
                            'similarity_score': float(row['similarity_score'])
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []