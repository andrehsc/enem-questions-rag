#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Gerar Relatório Completo de Caderno ENEM
Gera um arquivo de texto com todas as questões de um caderno específico.

EXEMPLOS DE USO:

1. Gerar relatório do CD5:
   python scripts/generate_caderno_report.py --caderno CD5

2. Gerar relatório do CD5 de 2024:
   python scripts/generate_caderno_report.py --caderno CD5 --year 2024

3. Gerar relatório de todos os cadernos disponíveis:
   python scripts/generate_caderno_report.py --all

4. Listar cadernos disponíveis:
   python scripts/generate_caderno_report.py --list-cadernos
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import os

# Adicionar o diretório scripts ao path para importar question_details
sys.path.append(str(Path(__file__).parent))
from question_details import QuestionDetailsAnalyzer

class CadernoReportGenerator:
    """Gerador de relatórios por caderno"""
    
    def __init__(self):
        self.analyzer = QuestionDetailsAnalyzer()
        self.reports_dir = Path(__file__).parent.parent / "data" / "reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def get_available_cadernos(self):
        """Listar todos os cadernos disponíveis"""
        try:
            with self.analyzer.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT 
                            em.caderno,
                            em.year,
                            em.day,
                            em.application_type,
                            COUNT(q.id) as question_count
                        FROM enem_questions.exam_metadata em
                        LEFT JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                        GROUP BY em.caderno, em.year, em.day, em.application_type
                        ORDER BY em.year DESC, em.day, em.caderno
                    """)
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"Erro ao listar cadernos: {e}")
            return []
    
    def get_caderno_questions(self, caderno, year=None, application_type=None):
        """Buscar todas as questões de um caderno"""
        try:
            with self.analyzer.get_connection() as conn:
                with conn.cursor() as cur:
                    conditions = ["em.caderno = %s"]
                    params = [caderno]
                    
                    if year:
                        conditions.append("em.year = %s")
                        params.append(year)
                    
                    if application_type:
                        conditions.append("em.application_type = %s")
                        params.append(application_type)
                    
                    where_clause = "WHERE " + " AND ".join(conditions)
                    
                    cur.execute(f"""
                        SELECT 
                            q.id,
                            q.question_number,
                            q.question_text,
                            q.context_text,
                            q.subject,
                            q.has_images,
                            q.parsing_confidence,
                            em.year,
                            em.day,
                            em.caderno,
                            em.application_type,
                            em.pdf_filename
                        FROM enem_questions.questions q
                        JOIN enem_questions.exam_metadata em ON q.exam_metadata_id = em.id
                        {where_clause}
                        ORDER BY q.question_number
                    """, params)
                    
                    questions = [dict(row) for row in cur.fetchall()]
                    
                    # Buscar alternativas e imagens para cada questão
                    for question in questions:
                        question_data = self.analyzer.get_question_by_id(question['id'])
                        if question_data:
                            question['alternatives'] = question_data['alternatives']
                            question['images'] = question_data['images']
                            question['answer_key'] = question_data['answer_key']
                    
                    return questions
                    
        except Exception as e:
            print(f"Erro ao buscar questões do caderno: {e}")
            return []
    
    def format_question_for_report(self, question, question_num):
        """Formatar uma questão para o relatório"""
        lines = []
        
        lines.append("=" * 100)
        lines.append(f"QUESTÃO {question_num}: Q{question['question_number']} - {question['year']} - DIA {question['day']} - {question['caderno']}")
        lines.append("=" * 100)
        
        lines.append(f"ID: {question['id']}")
        lines.append(f"Arquivo: {question['pdf_filename']}")
        lines.append(f"Tipo: {question['application_type']}")
        lines.append(f"Matéria: {question['subject']}")
        lines.append(f"Confiança: {question['parsing_confidence']:.3f}")
        lines.append(f"Tem imagens: {'Sim' if question['has_images'] else 'Não'}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("ENUNCIADO:")
        lines.append("-" * 60)
        lines.append(question['question_text'])
        
        if question['context_text']:
            lines.append("")
            lines.append("-" * 40)
            lines.append("CONTEXTO:")
            lines.append("-" * 40)
            lines.append(question['context_text'])
        
        lines.append("")
        lines.append("-" * 40)
        lines.append("ALTERNATIVAS:")
        lines.append("-" * 40)
        
        alternatives = question.get('alternatives', [])
        for alt in alternatives:
            lines.append(f"{alt['alternative_letter']}) {alt['alternative_text']}")
        
        # Gabarito
        if question.get('answer_key'):
            ak = question['answer_key']
            lines.append("")
            lines.append(f"🔑 GABARITO: {ak['correct_answer']}")
            if ak.get('language_option'):
                lines.append(f"   Idioma: {ak['language_option']}")
        
        # Imagens
        images = question.get('images', [])
        if images:
            lines.append("")
            lines.append("-" * 40)
            lines.append("IMAGENS:")
            lines.append("-" * 40)
            total_size = sum(img['image_size_bytes'] for img in images)
            lines.append(f"Total: {len(images)} imagens ({total_size/1024:.1f} KB)")
            
            for img in images:
                size_kb = img['image_size_bytes'] / 1024
                lines.append(f"  #{img['image_sequence']}: {img['image_format']} - {img['image_width']}x{img['image_height']} - {size_kb:.1f}KB")
        
        lines.append("")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_caderno_report(self, caderno, year=None, application_type=None):
        """Gerar relatório completo do caderno"""
        print(f"Gerando relatório para caderno {caderno}...")
        
        questions = self.get_caderno_questions(caderno, year, application_type)
        
        if not questions:
            print(f"Nenhuma questão encontrada para o caderno {caderno}")
            return None
        
        # Nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_parts = [f"caderno_{caderno}"]
        
        if year:
            filename_parts.append(f"{year}")
        
        if application_type:
            filename_parts.append(f"{application_type}")
        
        filename = "_".join(filename_parts) + f"_{timestamp}.txt"
        filepath = self.reports_dir / filename
        
        # Gerar conteúdo do relatório
        lines = []
        
        # Cabeçalho
        lines.append("📚 RELATÓRIO COMPLETO DO CADERNO ENEM")
        lines.append("=" * 80)
        lines.append(f"Caderno: {caderno}")
        
        if questions:
            sample_q = questions[0]
            lines.append(f"Ano: {sample_q['year']}")
            lines.append(f"Dia: {sample_q['day']}")
            lines.append(f"Tipo: {sample_q['application_type']}")
            lines.append(f"Arquivo: {sample_q['pdf_filename']}")
        
        lines.append(f"Total de Questões: {len(questions)}")
        lines.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
        lines.append("")
        lines.append("")
        
        # Questões
        for i, question in enumerate(questions, 1):
            question_report = self.format_question_for_report(question, i)
            lines.append(question_report)
        
        # Estatísticas finais
        lines.append("=" * 100)
        lines.append("📊 ESTATÍSTICAS DO CADERNO")
        lines.append("=" * 100)
        
        total_questions = len(questions)
        questions_with_images = sum(1 for q in questions if q['has_images'])
        total_alternatives = sum(len(q.get('alternatives', [])) for q in questions)
        total_images = sum(len(q.get('images', [])) for q in questions)
        
        lines.append(f"Total de questões: {total_questions}")
        lines.append(f"Questões com imagens: {questions_with_images} ({questions_with_images/total_questions*100:.1f}%)")
        lines.append(f"Total de alternativas: {total_alternatives}")
        lines.append(f"Total de imagens: {total_images}")
        
        # Distribuição por matéria
        subjects = {}
        for q in questions:
            subject = q['subject']
            subjects[subject] = subjects.get(subject, 0) + 1
        
        lines.append("\nDistribuição por matéria:")
        for subject, count in subjects.items():
            lines.append(f"  {subject}: {count} questões ({count/total_questions*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 100)
        lines.append("FIM DO RELATÓRIO")
        lines.append("=" * 100)
        
        # Salvar arquivo
        content = "\n".join(lines)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Relatório gerado com sucesso!")
            print(f"📁 Arquivo: {filepath}")
            print(f"📊 Questões processadas: {len(questions)}")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
            return None
    
    def generate_all_cadernos_reports(self):
        """Gerar relatórios para todos os cadernos"""
        cadernos = self.get_available_cadernos()
        
        if not cadernos:
            print("Nenhum caderno encontrado.")
            return
        
        print(f"Gerando relatórios para {len(cadernos)} cadernos...")
        
        success_count = 0
        for caderno_info in cadernos:
            print(f"\n🔄 Processando {caderno_info['caderno']} ({caderno_info['year']} - {caderno_info['application_type']})...")
            
            filepath = self.generate_caderno_report(
                caderno_info['caderno'],
                caderno_info['year'],
                caderno_info['application_type']
            )
            
            if filepath:
                success_count += 1
        
        print(f"\n✅ Concluído! {success_count}/{len(cadernos)} relatórios gerados com sucesso.")


def main():
    parser = argparse.ArgumentParser(description='Gerar Relatório Completo de Caderno ENEM')
    
    parser.add_argument('--caderno', type=str, help='Código do caderno (ex: CD5)')
    parser.add_argument('--year', type=int, help='Ano do exame')
    parser.add_argument('--application-type', type=str, help='Tipo de aplicação')
    parser.add_argument('--all', action='store_true', help='Gerar relatórios para todos os cadernos')
    parser.add_argument('--list-cadernos', action='store_true', help='Listar cadernos disponíveis')
    
    args = parser.parse_args()
    
    generator = CadernoReportGenerator()
    
    if args.list_cadernos:
        print("📚 Cadernos disponíveis:")
        print("-" * 60)
        cadernos = generator.get_available_cadernos()
        for caderno in cadernos:
            print(f"{caderno['caderno']} - {caderno['year']} - Dia {caderno['day']} - {caderno['application_type']} ({caderno['question_count']} questões)")
        return
    
    if args.all:
        generator.generate_all_cadernos_reports()
        return
    
    if args.caderno:
        generator.generate_caderno_report(args.caderno, args.year, args.application_type)
        return
    
    # Se nenhum argumento, mostrar ajuda
    parser.print_help()


if __name__ == "__main__":
    main()