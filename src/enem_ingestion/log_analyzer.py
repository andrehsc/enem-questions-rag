#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Historical Log Analyzer for ENEM Structure Guardrails
Analisa logs históricos para identificar padrões e fundamentar recomendações arquiteturais.

Author: Winston (Architect)
Date: October 15, 2025
Phase: 1 - Historical Analysis Implementation
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


@dataclass
class ExtractionAttempt:
    """Representa uma tentativa de extração de questão"""
    question_number: int
    alternatives_found: int
    success: bool
    error_type: str
    file_source: str
    timestamp: Optional[str] = None
    
    
@dataclass 
class LogAnalysisResult:
    """Resultado da análise de logs"""
    total_files_analyzed: int
    total_questions_attempted: int
    success_rate: float
    error_patterns: Dict[str, int]
    problematic_questions: List[int]
    recommendations: List[str]
    file_specific_issues: Dict[str, List[str]]


class HistoricalLogAnalyzer:
    """
    Analisador de logs históricos para identificar padrões de erro
    e fundamentar as especificações estruturais ENEM
    """
    
    def __init__(self, logs_directory: str = None):
        """
        Inicializa analisador
        
        Args:
            logs_directory: Diretório com logs históricos (default: data/extraction/)
        """
        if logs_directory is None:
            # Default para o diretório de extração do projeto
            project_root = Path(__file__).parent.parent.parent
            logs_directory = project_root / "data" / "extraction"
        
        self.logs_directory = Path(logs_directory)
        self.extraction_attempts: List[ExtractionAttempt] = []
        self.analysis_cache: Dict[str, LogAnalysisResult] = {}
        
    def scan_extraction_logs(self) -> int:
        """
        Escaneia diretório de logs para identificar arquivos de extração
        
        Returns:
            Número de arquivos de log encontrados
        """
        log_files = []
        
        if self.logs_directory.exists():
            # Buscar arquivos de erro (.txt)
            error_files = list(self.logs_directory.glob("*-errors.txt"))
            log_files.extend(error_files)
            
            # Buscar logs de ingestão
            ingestion_logs = list(self.logs_directory.glob("*ingestion*.log"))
            log_files.extend(ingestion_logs)
            
            # Buscar relatórios JSON
            json_reports = list(self.logs_directory.glob("*report*.json"))
            log_files.extend(json_reports)
        
        # Também buscar na raiz do projeto (logs de desenvolvimento)
        project_root = Path(__file__).parent.parent.parent
        root_logs = list(project_root.glob("*ingestion*.txt"))
        log_files.extend(root_logs)
        
        print(f"��� Encontrados {len(log_files)} arquivos de log para análise")
        
        for log_file in log_files:
            print(f"   - {log_file.name}")
            self._parse_log_file(log_file)
        
        return len(log_files)
    
    def _parse_log_file(self, log_file: Path) -> None:
        """
        Analisa arquivo de log específico
        
        Args:
            log_file: Caminho para arquivo de log
        """
        try:
            if log_file.suffix == '.json':
                self._parse_json_log(log_file)
            elif log_file.suffix == '.txt':
                self._parse_text_log(log_file)
            elif log_file.suffix == '.log':
                self._parse_ingestion_log(log_file)
        except Exception as e:
            print(f"⚠️  Erro ao processar {log_file}: {e}")
    
    def _parse_text_log(self, log_file: Path) -> None:
        """Analisa logs de texto com padrões de erro"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Pattern para questões com erro
            # Ex: "Questão 10: 0 alternativas encontradas"
            question_patterns = [
                r'Quest[ãa]o (\d+): (\d+) alternativas encontradas',
                r'Question (\d+): (\d+) alternatives found',
                r'Erro na quest[ãa]o (\d+)',
                r'Failed to extract question (\d+)'
            ]
            
            for pattern in question_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 2:
                        question_num = int(match[0])
                        alternatives_count = int(match[1]) if match[1].isdigit() else 0
                    else:
                        question_num = int(match[0])
                        alternatives_count = 0
                    
                    success = alternatives_count == 5
                    error_type = self._classify_error(alternatives_count)
                    
                    attempt = ExtractionAttempt(
                        question_number=question_num,
                        alternatives_found=alternatives_count,
                        success=success,
                        error_type=error_type,
                        file_source=log_file.name
                    )
                    
                    self.extraction_attempts.append(attempt)
                    
        except Exception as e:
            print(f"Erro ao processar arquivo de texto {log_file}: {e}")
    
    def _parse_json_log(self, log_file: Path) -> None:
        """Analisa logs JSON com dados estruturados"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Se for relatório de qualidade
            if 'extraction_results' in data:
                for result in data['extraction_results']:
                    question_num = result.get('question_number', 0)
                    alternatives = result.get('alternatives_found', 0)
                    
                    attempt = ExtractionAttempt(
                        question_number=question_num,
                        alternatives_found=alternatives,
                        success=alternatives == 5,
                        error_type=self._classify_error(alternatives),
                        file_source=log_file.name
                    )
                    
                    self.extraction_attempts.append(attempt)
                    
        except Exception as e:
            print(f"Erro ao processar arquivo JSON {log_file}: {e}")
    
    def _parse_ingestion_log(self, log_file: Path) -> None:
        """Analisa logs de ingestão com timestamps"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                # Buscar padrões de sucesso/erro com timestamp
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else None
                
                # Padrões de questão processada
                question_match = re.search(r'quest[ãa]o (\d+).*?(\d+) alternativas', line, re.IGNORECASE)
                if question_match:
                    question_num = int(question_match.group(1))
                    alternatives = int(question_match.group(2))
                    
                    attempt = ExtractionAttempt(
                        question_number=question_num,
                        alternatives_found=alternatives,
                        success=alternatives == 5,
                        error_type=self._classify_error(alternatives),
                        file_source=log_file.name,
                        timestamp=timestamp
                    )
                    
                    self.extraction_attempts.append(attempt)
                    
        except Exception as e:
            print(f"Erro ao processar log de ingestão {log_file}: {e}")
    
    def _classify_error(self, alternatives_found: int) -> str:
        """
        Classifica tipo de erro baseado no número de alternativas encontradas
        
        Args:
            alternatives_found: Número de alternativas extraídas
            
        Returns:
            Tipo de erro classificado
        """
        if alternatives_found == 0:
            return "zero_alternatives"
        elif alternatives_found < 5:
            return "incomplete_alternatives"
        elif alternatives_found == 5:
            return "success"
        else:
            return "excess_alternatives"
    
    def analyze_extraction_patterns(self) -> LogAnalysisResult:
        """
        Analisa padrões de extração baseado nos logs coletados
        
        Returns:
            Resultado detalhado da análise
        """
        if not self.extraction_attempts:
            return LogAnalysisResult(
                total_files_analyzed=0,
                total_questions_attempted=0,
                success_rate=0.0,
                error_patterns={},
                problematic_questions=[],
                recommendations=[],
                file_specific_issues={}
            )
        
        # Estatísticas gerais
        total_attempts = len(self.extraction_attempts)
        successful_attempts = sum(1 for attempt in self.extraction_attempts if attempt.success)
        success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0
        
        # Padrões de erro
        error_counter = Counter(attempt.error_type for attempt in self.extraction_attempts)
        
        # Questões problemáticas (com mais de 1 falha)
        question_failures = defaultdict(int)
        for attempt in self.extraction_attempts:
            if not attempt.success:
                question_failures[attempt.question_number] += 1
        
        problematic_questions = [
            q for q, failures in question_failures.items() 
            if failures > 1
        ]
        
        # Issues específicas por arquivo
        file_issues = defaultdict(list)
        for attempt in self.extraction_attempts:
            if not attempt.success:
                issue = f"Questão {attempt.question_number}: {attempt.error_type}"
                file_issues[attempt.file_source].append(issue)
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(error_counter, success_rate, problematic_questions)
        
        # Arquivos únicos analisados
        unique_files = len(set(attempt.file_source for attempt in self.extraction_attempts))
        
        result = LogAnalysisResult(
            total_files_analyzed=unique_files,
            total_questions_attempted=total_attempts,
            success_rate=success_rate,
            error_patterns=dict(error_counter),
            problematic_questions=sorted(problematic_questions),
            recommendations=recommendations,
            file_specific_issues=dict(file_issues)
        )
        
        return result
    
    def _generate_recommendations(self, error_counter: Counter, success_rate: float, 
                                 problematic_questions: List[int]) -> List[str]:
        """
        Gera recomendações baseadas na análise dos padrões
        
        Args:
            error_counter: Contador de tipos de erro
            success_rate: Taxa de sucesso geral
            problematic_questions: Lista de questões problemáticas
            
        Returns:
            Lista de recomendações arquiteturais
        """
        recommendations = []
        
        # Recomendações baseadas na taxa de sucesso
        if success_rate < 0.5:
            recommendations.append("⚠️  CRÍTICO: Taxa de sucesso muito baixa - revisar algoritmo base")
        elif success_rate < 0.8:
            recommendations.append("��� MELHORIA: Taxa de sucesso moderada - aplicar estratégias especializadas")
        else:
            recommendations.append("✅ BOM: Taxa de sucesso adequada - manter estratégias atuais")
        
        # Recomendações baseadas em padrões de erro
        if error_counter.get('zero_alternatives', 0) > 10:
            recommendations.append("��� IMPLEMENTAR: Enhanced Alternative Detection para questões sem alternativas")
        
        if error_counter.get('incomplete_alternatives', 0) > 20:
            recommendations.append("��� IMPLEMENTAR: Multiline Pattern Strategy com boost de confiança")
        
        if len(problematic_questions) > 15:
            recommendations.append("⚙️  IMPLEMENTAR: Mathematical Strategy para questões complexas")
        
        # Recomendação para questões específicas
        if problematic_questions:
            if any(q in range(91, 180) for q in problematic_questions):
                recommendations.append("��� FOCO: Questões de Matemática/Natureza precisam de tratamento especial")
            
            if any(q in range(1, 90) for q in problematic_questions):
                recommendations.append("��� FOCO: Questões de Linguagens/Humanas precisam de análise de layout")
        
        return recommendations
    
    def generate_empirical_report(self) -> str:
        """
        Gera relatório empírico detalhado para fundamentar especificações
        
        Returns:
            Relatório formatado em markdown
        """
        analysis = self.analyze_extraction_patterns()
        
        report = f"""# Relatório Empírico - Análise de Logs Históricos ENEM

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Autor:** Winston (Architect) - Fase 1 Implementação

## ��� Estatísticas Gerais

- **Arquivos de Log Analisados:** {analysis.total_files_analyzed}
- **Tentativas de Extração:** {analysis.total_questions_attempted:,}
- **Taxa de Sucesso Geral:** {analysis.success_rate:.1%}
- **Questões Problemáticas:** {len(analysis.problematic_questions)}

## ��� Padrões de Erro Identificados

"""
        
        for error_type, count in analysis.error_patterns.items():
            percentage = (count / analysis.total_questions_attempted) * 100 if analysis.total_questions_attempted > 0 else 0
            report += f"- **{error_type}:** {count} ocorrências ({percentage:.1f}%)\n"
        
        report += f"""
## ⚠️  Questões Mais Problemáticas

{', '.join(map(str, analysis.problematic_questions[:20]))}
{"..." if len(analysis.problematic_questions) > 20 else ""}

## ��� Recomendações Arquiteturais Baseadas em Dados

"""
        
        for i, rec in enumerate(analysis.recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""
## ��� Issues por Arquivo

"""
        
        for file_name, issues in list(analysis.file_specific_issues.items())[:10]:  # Top 10 files
            report += f"### {file_name}\n"
            for issue in issues[:5]:  # Top 5 issues per file
                report += f"- {issue}\n"
            if len(issues) > 5:
                report += f"- ... e mais {len(issues) - 5} issues\n"
            report += "\n"
        
        report += f"""
## ��️  Impacto nas Especificações Estruturais

Esta análise empírica fundamenta as seguintes definições em `EnemStructureSpecification`:

1. **HISTORICAL_ERROR_PATTERNS:** Baseado nos padrões identificados acima
2. **LAYOUT_PATTERNS:** Ajustado conforme questões problemáticas por tipo
3. **VALIDATION_RULES:** Definidas para questões com alta taxa de falha
4. **CONFIDENCE_ADJUSTMENTS:** Calibrados pela taxa de sucesso observada

## ��� Métricas de Melhoria

**META:** Elevar taxa de sucesso de {analysis.success_rate:.1%} para >95% com implementação das especificações estruturais.

**BASELINE ATUAL:** {analysis.success_rate:.1%} (Enhanced Alternative Extractor atingiu 100% em testes controlados)

---
*Este relatório fundamenta empiricamente as decisões arquiteturais do ENEM Structure Guardrails.*
"""
        
        return report
    
    def export_analysis_data(self, output_file: str) -> None:
        """
        Exporta dados de análise para arquivo JSON
        
        Args:
            output_file: Caminho do arquivo de saída
        """
        analysis = self.analyze_extraction_patterns()
        
        export_data = {
            'analysis_timestamp': datetime.now().isoformat(),
            'summary': asdict(analysis),
            'raw_attempts': [asdict(attempt) for attempt in self.extraction_attempts],
            'analyzer_version': '1.0.0',
            'phase': 'Phase 1 - Structure Specification Implementation'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"��� Dados de análise exportados para: {output_file}")


# === FACTORY FUNCTIONS ===

def create_log_analyzer(logs_directory: str = None) -> HistoricalLogAnalyzer:
    """Factory function para criar analisador de logs"""
    return HistoricalLogAnalyzer(logs_directory)


def quick_log_analysis() -> LogAnalysisResult:
    """
    Executa análise rápida dos logs disponíveis
    
    Returns:
        Resultado da análise
    """
    analyzer = create_log_analyzer()
    analyzer.scan_extraction_logs()
    return analyzer.analyze_extraction_patterns()


# === CLI ENTRY POINT ===

if __name__ == "__main__":
    print("��� ENEM Historical Log Analyzer - Fase 1")
    print("=" * 50)
    
    analyzer = create_log_analyzer()
    files_found = analyzer.scan_extraction_logs()
    
    if files_found > 0:
        print(f"\n��� Analisando {len(analyzer.extraction_attempts)} tentativas de extração...")
        
        analysis = analyzer.analyze_extraction_patterns()
        
        print(f"\n✅ RESULTADOS:")
        print(f"   Taxa de Sucesso: {analysis.success_rate:.1%}")
        print(f"   Questões Problemáticas: {len(analysis.problematic_questions)}")
        print(f"   Tipos de Erro: {len(analysis.error_patterns)}")
        
        # Gerar relatório
        report = analyzer.generate_empirical_report()
        
        # Salvar relatório
        project_root = Path(__file__).parent.parent.parent
        report_file = project_root / "docs" / "empirical-analysis-report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n��� Relatório empírico salvo em: {report_file}")
        
        # Exportar dados
        data_file = project_root / "data" / "extraction" / "historical-analysis.json"
        analyzer.export_analysis_data(str(data_file))
        
    else:
        print("⚠️  Nenhum arquivo de log encontrado para análise")
