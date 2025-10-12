#!/usr/bin/env python3
"""
Comprehensive quality analysis of 2024 reprocessed data
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from collections import defaultdict

def analyze_2024_data_quality():
    """Analyze quality of reprocessed 2024 data"""
    
    # Database connection
    connection_url = "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
    
    try:
        conn = psycopg2.connect(connection_url, cursor_factory=RealDictCursor)
        print("‚úÖ Database connection established")
    except Exception as e:
        print(f"‚ùå Database connection failed: {e}")
        return
    
    with conn.cursor() as cur:
        print("\n" + "="*60)
        print("QUALITY ANALYSIS OF 2024 REPROCESSED DATA")
        print("="*60)
        
        # 1. Overall Statistics
        print("\nÌ≥ä OVERALL STATISTICS")
        print("-" * 30)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_questions,
                COUNT(DISTINCT exam_metadata_id) as total_files,
                MIN(created_at) as first_processed,
                MAX(created_at) as last_processed
            FROM enem_questions.questions q
            JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
            WHERE em.year = 2024
        """)
        
        stats = cur.fetchone()
        print(f"Total 2024 questions: {stats['total_questions']}")
        print(f"Total 2024 files: {stats['total_files']}")
        print(f"Processing timespan: {stats['first_processed']} to {stats['last_processed']}")
        
        # 2. Questions per file breakdown
        print("\nÌ≥Å QUESTIONS PER FILE BREAKDOWN")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                em.pdf_filename,
                em.day,
                em.caderno,
                COUNT(q.id) as question_count,
                COUNT(qa.id) as alternative_count,
                ROUND(COUNT(qa.id)::float / COUNT(q.id), 1) as avg_alternatives_per_question
            FROM enem_questions.exam_metadata em
            LEFT JOIN enem_questions.questions q ON em.id = q.exam_metadata_id
            LEFT JOIN enem_questions.question_alternatives qa ON q.id = qa.question_id
            WHERE em.year = 2024 AND em.pdf_filename LIKE '%PV_impresso%'
            GROUP BY em.id, em.pdf_filename, em.day, em.caderno
            ORDER BY em.day, em.caderno
        """)
        
        files_data = cur.fetchall()
        day1_total = 0
        day2_total = 0
        
        for file_data in files_data:
            day = file_data['day']
            print(f"Day {day} - {file_data['pdf_filename']}: {file_data['question_count']} questions, {file_data['avg_alternatives_per_question']} avg alternatives")
            
            if day == 1:
                day1_total += file_data['question_count']
            else:
                day2_total += file_data['question_count']
        
        print(f"\nÌ≥à TOTALS BY DAY:")
        print(f"Day 1 (Languages + Humanities): {day1_total} questions")
        print(f"Day 2 (Math + Sciences): {day2_total} questions")
        
        # 3. Alternative Quality Analysis
        print("\nÌæØ ALTERNATIVE QUALITY ANALYSIS")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                COUNT(*) as questions_with_5_alternatives
            FROM (
                SELECT 
                    q.id,
                    COUNT(qa.id) as alt_count
                FROM enem_questions.questions q
                JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                LEFT JOIN enem_questions.question_alternatives qa ON q.id = qa.question_id
                WHERE em.year = 2024
                GROUP BY q.id
                HAVING COUNT(qa.id) = 5
            ) t
        """)
        
        perfect_questions = cur.fetchone()['questions_with_5_alternatives']
        total_questions = stats['total_questions']
        quality_rate = (perfect_questions / total_questions * 100) if total_questions > 0 else 0
        
        print(f"Questions with exactly 5 alternatives: {perfect_questions}/{total_questions}")
        print(f"Quality rate: {quality_rate:.1f}%")
        
        # 4. Check for placeholder alternatives
        print("\nÌ¥ç PLACEHOLDER ANALYSIS")
        print("-" * 30)
        
        cur.execute("""
            SELECT COUNT(*) as placeholder_count
            FROM enem_questions.question_alternatives qa
            JOIN enem_questions.questions q ON qa.question_id = q.id
            JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
            WHERE em.year = 2024 AND qa.alternative_text LIKE '%[Alternative not found]%'
        """)
        
        placeholders = cur.fetchone()['placeholder_count']
        total_alternatives = stats['total_questions'] * 5  # Expected 5 per question
        placeholder_rate = (placeholders / total_alternatives * 100) if total_alternatives > 0 else 0
        
        print(f"Placeholder alternatives: {placeholders}")
        print(f"Placeholder rate: {placeholder_rate:.1f}%")
        print(f"Real extraction rate: {100 - placeholder_rate:.1f}%")
        
        # 5. Text Quality Samples
        print("\nÌ≥ù TEXT QUALITY SAMPLES")
        print("-" * 30)
        
        cur.execute("""
            SELECT 
                q.question_number,
                em.pdf_filename,
                LENGTH(q.question_text) as text_length,
                CASE 
                    WHEN q.question_text LIKE '%ENEM2024%' THEN 'Contains ENEM2024 pattern'
                    WHEN LENGTH(q.question_text) < 50 THEN 'Very short'
                    WHEN LENGTH(q.question_text) > 2000 THEN 'Very long'
                    ELSE 'Normal'
                END as quality_flag
            FROM enem_questions.questions q
            JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
            WHERE em.year = 2024
            AND (
                q.question_text LIKE '%ENEM2024%' 
                OR LENGTH(q.question_text) < 50 
                OR LENGTH(q.question_text) > 2000
            )
            ORDER BY em.day, q.question_number
            LIMIT 10
        """)
        
        quality_issues = cur.fetchall()
        if quality_issues:
            print("Questions with potential quality issues:")
            for issue in quality_issues:
                print(f"  Q{issue['question_number']} ({issue['pdf_filename'][:20]}...): {issue['quality_flag']} (len: {issue['text_length']})")
        else:
            print("‚úÖ No major text quality issues detected!")
        
        # 6. Comparison with Previous Data
        print("\nÌ≥ä COMPARISON WITH OTHER YEARS")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                em.year,
                COUNT(q.id) as question_count,
                ROUND(AVG(LENGTH(q.question_text)), 0) as avg_text_length
            FROM enem_questions.questions q
            JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
            WHERE em.year IN (2020, 2021, 2022, 2023, 2024)
            GROUP BY em.year
            ORDER BY em.year
        """)
        
        year_comparison = cur.fetchall()
        for year_data in year_comparison:
            marker = "Ì∂ï" if year_data['year'] == 2024 else "  "
            print(f"{marker} {year_data['year']}: {year_data['question_count']} questions, avg length: {year_data['avg_text_length']} chars")
        
        # 7. Final Quality Score
        print("\nÌøÜ FINAL QUALITY SCORE")
        print("-" * 25)
        
        completeness_score = (perfect_questions / total_questions * 100) if total_questions > 0 else 0
        extraction_score = 100 - placeholder_rate
        consistency_score = 100 if len(files_data) == 12 else (len(files_data) / 12 * 100)
        
        overall_score = (completeness_score + extraction_score + consistency_score) / 3
        
        print(f"Completeness Score: {completeness_score:.1f}% (5 alternatives per question)")
        print(f"Extraction Score: {extraction_score:.1f}% (real content vs placeholders)")
        print(f"Consistency Score: {consistency_score:.1f}% (all files processed)")
        print(f"\nÌæØ OVERALL QUALITY SCORE: {overall_score:.1f}%")
        
        if overall_score >= 90:
            print("Ìø¢ EXCELLENT - Ready for production!")
        elif overall_score >= 80:
            print("ÔøΩÔøΩ GOOD - Minor improvements recommended")
        else:
            print("Ì¥¥ NEEDS IMPROVEMENT - Address quality issues")
    
    conn.close()

if __name__ == "__main__":
    analyze_2024_data_quality()
