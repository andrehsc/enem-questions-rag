#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Avaliação da Qualidade de Extração do ENEM
==========================================
Script para analisar a qualidade da extração de texto e imagens dos PDFs do ENEM
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pdfplumber
import fitz  # PyMuPDF

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from enem_ingestion.parser import EnemPDFParser
from enem_ingestion.image_extractor import ImageExtractor


class ExtractionQualityAnalyzer:
    """Analisador de qualidade de extração."""
    
    def __init__(self):
        self.parser = EnemPDFParser()
        self.image_extractor = ImageExtractor()
        
    def analyze_pdf_content(self, pdf_path: Path) -> Dict:
        """Analisa conteúdo de um PDF específico."""
        results = {
            'pdf_file': pdf_path.name,
            'pages': 0,
            'raw_text_quality': {},
            'questions_found': 0,
            'alternatives_quality': {},
            'images_found': 0,
            'encoding_issues': [],
            'parsing_issues': []
        }
        
        try:
            # Análise básica do PDF
            with pdfplumber.open(pdf_path) as pdf:
                results['pages'] = len(pdf.pages)
                
                # Analisar primeira página para identificar problemas de encoding
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text()
                    results['raw_text_quality'] = self._analyze_text_quality(first_page_text)
                    
            # Análise de questões parseadas
            questions = self.parser.parse_questions(pdf_path)
            results['questions_found'] = len(questions)
            
            if questions:
                # Analisar qualidade das alternativas
                results['alternatives_quality'] = self._analyze_alternatives_quality(questions)
                
            # Análise de imagens extraídas
            images = self.image_extractor.extract_images_from_pdf(pdf_path)
            results['images_found'] = len(images)
            
            return results
            
        except Exception as e:
            results['error'] = str(e)
            return results
    
    def _analyze_text_quality(self, text: str) -> Dict:
        """Analisa qualidade do texto extraído."""
        if not text:
            return {'status': 'no_text', 'issues': ['No text extracted']}
        
        quality = {
            'status': 'good',
            'total_chars': len(text),
            'issues': [],
            'encoding_problems': 0,
            'suspicious_patterns': []
        }
        
        # Verificar problemas de encoding
        encoding_issues = [
            (r'[^\x00-\x7F\u00C0-\u017F\u2000-\u206F]', 'non_latin_chars'),
            (r'Ã¡|Ã©|Ã­|Ã³|Ãº', 'utf8_mojibake'),
            (r'\?{2,}', 'question_mark_artifacts'),
            (r'[^\w\s\.,!?()[\]{}":;/-]', 'unusual_chars')
        ]
        
        for pattern, issue_type in encoding_issues:
            matches = re.findall(pattern, text)
            if matches:
                quality['encoding_problems'] += len(matches)
                quality['issues'].append(f"{issue_type}: {len(matches)} occurrences")
                quality['suspicious_patterns'].extend(matches[:5])  # Primeiros 5 exemplos
        
        # Verificar caracteres problemáticos específicos
        problematic_chars = []
        for char in text:
            if ord(char) > 65535:  # Caracteres fora do BMP
                problematic_chars.append(char)
        
        if problematic_chars:
            quality['issues'].append(f"High Unicode chars: {len(set(problematic_chars))}")
        
        # Determinar status geral
        if quality['encoding_problems'] > 50:
            quality['status'] = 'poor'
        elif quality['encoding_problems'] > 10:
            quality['status'] = 'fair'
            
        return quality
    
    def _analyze_alternatives_quality(self, questions: List) -> Dict:
        """Analisa qualidade das alternativas extraídas."""
        quality = {
            'total_questions': len(questions),
            'questions_with_5_alternatives': 0,
            'questions_with_incomplete_alternatives': 0,
            'average_alternative_length': 0,
            'problematic_alternatives': []
        }
        
        total_alternatives = 0
        total_length = 0
        
        for question in questions:
            alt_count = len(question.alternatives)
            total_alternatives += alt_count
            
            if alt_count == 5:
                quality['questions_with_5_alternatives'] += 1
            else:
                quality['questions_with_incomplete_alternatives'] += 1
                quality['problematic_alternatives'].append({
                    'question_number': question.number,
                    'alternatives_found': alt_count,
                    'alternatives': question.alternatives
                })
            
            for alt in question.alternatives:
                total_length += len(alt)
        
        if total_alternatives > 0:
            quality['average_alternative_length'] = total_length / total_alternatives
        
        return quality
    
    def analyze_sample_pdfs(self, pdf_dir: Path, max_files: int = 3) -> Dict:
        """Analisa uma amostra de PDFs."""
        pdf_files = list(pdf_dir.glob("*PV*.pdf"))[:max_files]
        
        results = {
            'analysis_summary': {
                'files_analyzed': len(pdf_files),
                'total_issues_found': 0,
                'common_problems': [],
                'recommendations': []
            },
            'individual_results': []
        }
        
        for pdf_file in pdf_files:
            print(f"Analisando: {pdf_file.name}")
            file_results = self.analyze_pdf_content(pdf_file)
            results['individual_results'].append(file_results)
            
        # Compilar problemas comuns
        self._compile_common_issues(results)
        
        return results
    
    def _compile_common_issues(self, results: Dict):
        """Compila problemas comuns encontrados."""
        all_issues = []
        
        for file_result in results['individual_results']:
            if 'raw_text_quality' in file_result:
                all_issues.extend(file_result['raw_text_quality'].get('issues', []))
        
        # Contar ocorrências
        issue_counts = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        # Problemas mais comuns
        common_problems = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        results['analysis_summary']['common_problems'] = common_problems
        results['analysis_summary']['total_issues_found'] = sum(issue_counts.values())
        
        # Gerar recomendações
        recommendations = []
        
        if any('utf8_mojibake' in issue for issue in all_issues):
            recommendations.append("Implementar correção de encoding UTF-8/Latin-1")
        
        if any('question_mark_artifacts' in issue for issue in all_issues):
            recommendations.append("Melhorar detecção de caracteres especiais")
        
        if any(result.get('images_found', 0) > 0 for result in results['individual_results']):
            recommendations.append("Desenvolver pipeline de OCR para imagens com texto")
        
        results['analysis_summary']['recommendations'] = recommendations


def print_analysis_report(results: Dict):
    """Imprime relatório de análise formatado."""
    print("\n" + "="*60)
    print("RELATÓRIO DE QUALIDADE DE EXTRAÇÃO")
    print("="*60)
    
    summary = results['analysis_summary']
    print(f"\n📊 RESUMO:")
    print(f"  • Arquivos analisados: {summary['files_analyzed']}")
    print(f"  • Total de problemas: {summary['total_issues_found']}")
    
    if summary['common_problems']:
        print(f"\n🔍 PROBLEMAS MAIS COMUNS:")
        for problem, count in summary['common_problems'][:5]:
            print(f"  • {problem}: {count} ocorrências")
    
    if summary['recommendations']:
        print(f"\n💡 RECOMENDAÇÕES:")
        for i, rec in enumerate(summary['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print(f"\n📋 DETALHES POR ARQUIVO:")
    for result in results['individual_results']:
        print(f"\n📄 {result['pdf_file']}:")
        print(f"  • Páginas: {result['pages']}")
        print(f"  • Questões encontradas: {result['questions_found']}")
        print(f"  • Imagens encontradas: {result['images_found']}")
        
        if 'raw_text_quality' in result:
            quality = result['raw_text_quality']
            print(f"  • Qualidade do texto: {quality['status']}")
            if quality['issues']:
                print(f"    - Problemas: {', '.join(quality['issues'][:3])}")
        
        if 'alternatives_quality' in result:
            alt_quality = result['alternatives_quality']
            complete_ratio = (alt_quality['questions_with_5_alternatives'] / 
                            max(alt_quality['total_questions'], 1)) * 100
            print(f"  • Questões com 5 alternativas: {complete_ratio:.1f}%")


if __name__ == "__main__":
    print("🔍 ENEM Extraction Quality Analyzer")
    print("="*50)
    
    # Configurações
    base_dir = Path("data/downloads/2020")
    
    if not base_dir.exists():
        print(f"❌ Diretório não encontrado: {base_dir}")
        sys.exit(1)
    
    analyzer = ExtractionQualityAnalyzer()
    
    # Analisar amostra de PDFs
    results = analyzer.analyze_sample_pdfs(base_dir, max_files=2)
    
    # Imprimir relatório
    print_analysis_report(results)
    
    # Salvar relatório em JSON
    output_file = Path("extraction_quality_report.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo em: {output_file}")