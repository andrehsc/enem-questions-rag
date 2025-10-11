#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de análise e insights para questões ENEM
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import json
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

class EnemAnalytics:
    """Sistema de análise avançada para questões ENEM"""
    
    def __init__(self):
        """Inicializa o sistema de analytics"""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='portuguese' if 'portuguese' in TfidfVectorizer().get_stop_words() else None
        )
        self.analysis_cache = {}
    
    def analyze_question_distribution(
        self, 
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analisa distribuição das questões por diferentes dimensões
        
        Args:
            questions: Lista de questões para análise
        
        Returns:
            Análise completa da distribuição
        """
        if not questions:
            return {"error": "Nenhuma questão fornecida"}
        
        df = pd.DataFrame(questions)
        
        analysis = {
            "total_questions": len(questions),
            "analysis_date": datetime.now().isoformat()
        }
        
        # Distribuição por ano
        if 'ano' in df.columns:
            year_dist = df['ano'].value_counts().to_dict()
            analysis["by_year"] = {
                "distribution": year_dist,
                "years_range": f"{min(year_dist.keys())} - {max(year_dist.keys())}",
                "most_common_year": max(year_dist, key=year_dist.get)
            }
        
        # Distribuição por matéria
        if 'materia' in df.columns:
            subject_dist = df['materia'].value_counts().to_dict()
            analysis["by_subject"] = {
                "distribution": subject_dist,
                "total_subjects": len(subject_dist),
                "most_common_subject": max(subject_dist, key=subject_dist.get)
            }
        
        # Distribuição por área do conhecimento
        if 'area' in df.columns:
            area_dist = df['area'].value_counts().to_dict()
            analysis["by_area"] = {
                "distribution": area_dist,
                "coverage": len(area_dist)
            }
        
        # Análise de texto - comprimento das questões
        if 'enunciado' in df.columns:
            text_lengths = df['enunciado'].str.len()
            analysis["text_analysis"] = {
                "avg_length": float(text_lengths.mean()),
                "median_length": float(text_lengths.median()),
                "min_length": int(text_lengths.min()),
                "max_length": int(text_lengths.max()),
                "std_length": float(text_lengths.std())
            }
        
        return analysis
    
    def find_question_clusters(
        self,
        questions: List[Dict[str, Any]],
        n_clusters: int = 5,
        text_field: str = "enunciado"
    ) -> Dict[str, Any]:
        """
        Agrupa questões similares usando clustering
        
        Args:
            questions: Lista de questões
            n_clusters: Número de clusters desejados
            text_field: Campo de texto para clustering
        
        Returns:
            Resultado do clustering com grupos identificados
        """
        if len(questions) < n_clusters:
            return {"error": f"Número insuficiente de questões para {n_clusters} clusters"}
        
        # Extrair textos
        texts = []
        valid_questions = []
        
        for q in questions:
            if text_field in q and q[text_field]:
                texts.append(str(q[text_field]))
                valid_questions.append(q)
        
        if len(texts) < n_clusters:
            return {"error": "Textos insuficientes para clustering"}
        
        # Vetorização TF-IDF
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Clustering K-means
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            # Organizar resultados por cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[int(label)].append({
                    "question": valid_questions[i],
                    "text": texts[i]
                })
            
            # Extrair palavras-chave de cada cluster
            feature_names = self.vectorizer.get_feature_names_out()
            cluster_keywords = {}
            
            for cluster_id in range(n_clusters):
                cluster_center = kmeans.cluster_centers_[cluster_id]
                top_indices = cluster_center.argsort()[-10:][::-1]  # Top 10 palavras
                cluster_keywords[cluster_id] = [feature_names[i] for i in top_indices]
            
            return {
                "clusters": dict(clusters),
                "cluster_keywords": cluster_keywords,
                "cluster_sizes": {k: len(v) for k, v in clusters.items()},
                "total_clustered": len(valid_questions),
                "clustering_method": "kmeans_tfidf"
            }
            
        except Exception as e:
            logger.error(f"Erro no clustering: {str(e)}")
            return {"error": str(e)}
    
    def detect_question_patterns(
        self,
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detecta padrões comuns nas questões
        
        Args:
            questions: Lista de questões para análise
        
        Returns:
            Padrões identificados
        """
        patterns = {
            "analysis_date": datetime.now().isoformat(),
            "total_analyzed": len(questions)
        }
        
        # Padrões de palavras-chave
        all_texts = []
        for q in questions:
            if 'enunciado' in q:
                all_texts.append(str(q['enunciado']).lower())
        
        if all_texts:
            # Palavras mais comuns
            all_words = ' '.join(all_texts).split()
            word_freq = Counter(all_words)
            patterns["common_words"] = dict(word_freq.most_common(20))
            
            # Padrões de início de questão
            question_starts = [text[:50] for text in all_texts if len(text) > 50]
            start_patterns = Counter(question_starts)
            patterns["question_starts"] = dict(start_patterns.most_common(10))
        
        # Padrões de estrutura (se houver alternativas)
        if any('alternativas' in q for q in questions):
            alt_patterns = []
            for q in questions:
                if 'alternativas' in q and isinstance(q['alternativas'], dict):
                    alt_patterns.append(len(q['alternativas']))
            
            if alt_patterns:
                patterns["alternatives_pattern"] = {
                    "avg_alternatives": np.mean(alt_patterns),
                    "most_common_count": Counter(alt_patterns).most_common(1)[0]
                }
        
        # Padrões temporais (se houver datas)
        temporal_data = []
        for q in questions:
            if 'ano' in q:
                temporal_data.append(q['ano'])
        
        if temporal_data:
            temporal_counter = Counter(temporal_data)
            patterns["temporal_patterns"] = {
                "year_distribution": dict(temporal_counter),
                "peak_year": temporal_counter.most_common(1)[0][0],
                "year_range": f"{min(temporal_data)} - {max(temporal_data)}"
            }
        
        return patterns
    
    def analyze_difficulty_progression(
        self,
        questions: List[Dict[str, Any]],
        difficulty_field: str = "dificuldade"
    ) -> Dict[str, Any]:
        """
        Analisa progressão de dificuldade das questões
        
        Args:
            questions: Lista de questões
            difficulty_field: Campo que contém informação de dificuldade
        
        Returns:
            Análise da dificuldade
        """
        df = pd.DataFrame(questions)
        
        if difficulty_field not in df.columns:
            return {"error": f"Campo {difficulty_field} não encontrado"}
        
        difficulty_counts = df[difficulty_field].value_counts()
        
        # Mapear dificuldades para valores numéricos
        difficulty_map = {
            'muito fácil': 1, 'fácil': 2, 'médio': 3, 
            'difícil': 4, 'muito difícil': 5
        }
        
        df['difficulty_numeric'] = df[difficulty_field].map(difficulty_map)
        
        analysis = {
            "difficulty_distribution": difficulty_counts.to_dict(),
            "average_difficulty": float(df['difficulty_numeric'].mean()) if 'difficulty_numeric' in df.columns else None,
            "difficulty_range": {
                "min": df[difficulty_field].min(),
                "max": df[difficulty_field].max()
            }
        }
        
        # Análise por ano (se disponível)
        if 'ano' in df.columns and 'difficulty_numeric' in df.columns:
            yearly_difficulty = df.groupby('ano')['difficulty_numeric'].mean().to_dict()
            analysis["difficulty_by_year"] = yearly_difficulty
        
        return analysis
    
    def generate_insights_report(
        self,
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gera relatório completo de insights
        
        Args:
            questions: Lista de questões para análise
        
        Returns:
            Relatório completo com todos os insights
        """
        report = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "dataset_size": len(questions)
        }
        
        # Análise de distribuição
        report["distribution_analysis"] = self.analyze_question_distribution(questions)
        
        # Clustering de questões
        if len(questions) >= 5:
            report["clustering_analysis"] = self.find_question_clusters(questions)
        
        # Padrões identificados
        report["pattern_analysis"] = self.detect_question_patterns(questions)
        
        # Análise de dificuldade
        report["difficulty_analysis"] = self.analyze_difficulty_progression(questions)
        
        # Insights e recomendações
        report["insights"] = self._generate_actionable_insights(report)
        
        return report
    
    def _generate_actionable_insights(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera insights acionáveis baseados na análise"""
        insights = []
        
        # Insight sobre distribuição por matéria
        if "distribution_analysis" in analysis_data and "by_subject" in analysis_data["distribution_analysis"]:
            subject_dist = analysis_data["distribution_analysis"]["by_subject"]["distribution"]
            most_common = max(subject_dist, key=subject_dist.get)
            least_common = min(subject_dist, key=subject_dist.get)
            
            insights.append({
                "type": "subject_balance",
                "title": "Equilíbrio de Matérias",
                "description": f"Matéria mais comum: {most_common} ({subject_dist[most_common]} questões). Matéria menos comum: {least_common} ({subject_dist[least_common]} questões).",
                "recommendation": "Considere balancear melhor a distribuição de questões entre as matérias.",
                "priority": "medium"
            })
        
        # Insight sobre clusters
        if "clustering_analysis" in analysis_data and "clusters" in analysis_data["clustering_analysis"]:
            clusters = analysis_data["clustering_analysis"]["clusters"]
            largest_cluster = max(clusters.keys(), key=lambda k: len(clusters[k]))
            
            insights.append({
                "type": "content_clustering",
                "title": "Agrupamento de Conteúdo",
                "description": f"Identificados {len(clusters)} grupos de questões similares. Maior grupo contém {len(clusters[largest_cluster])} questões.",
                "recommendation": "Use os clusters para criar simulados temáticos ou identificar lacunas de conteúdo.",
                "priority": "high"
            })
        
        # Insight sobre dificuldade
        if "difficulty_analysis" in analysis_data and "difficulty_distribution" in analysis_data["difficulty_analysis"]:
            diff_dist = analysis_data["difficulty_analysis"]["difficulty_distribution"]
            if len(diff_dist) > 0:
                most_common_difficulty = max(diff_dist, key=diff_dist.get)
                
                insights.append({
                    "type": "difficulty_balance",
                    "title": "Distribuição de Dificuldade",
                    "description": f"Dificuldade mais comum: {most_common_difficulty} ({diff_dist[most_common_difficulty]} questões).",
                    "recommendation": "Verifique se a distribuição de dificuldade atende aos objetivos pedagógicos.",
                    "priority": "medium"
                })
        
        return insights
    
    def export_analysis(
        self,
        analysis_data: Dict[str, Any],
        format_type: str = "json",
        file_path: Optional[str] = None
    ) -> str:
        """
        Exporta análise em diferentes formatos
        
        Args:
            analysis_data: Dados da análise
            format_type: Formato de exportação (json, csv, html)
            file_path: Caminho do arquivo (opcional)
        
        Returns:
            Caminho do arquivo exportado ou conteúdo
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if not file_path:
            file_path = f"analysis_export_{timestamp}.{format_type}"
        
        try:
            if format_type == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            elif format_type == "html":
                html_content = self._generate_html_report(analysis_data)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            logger.info(f"Análise exportada para: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Erro na exportação: {str(e)}")
            return f"Erro: {str(e)}"
    
    def _generate_html_report(self, analysis_data: Dict[str, Any]) -> str:
        """Gera relatório HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Relatório de Análise ENEM</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }}
                .insights {{ background-color: #f0f8ff; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Relatório de Análise - Questões ENEM</h1>
            <p>Gerado em: {analysis_data.get('generated_at', 'N/A')}</p>
            
            <div class="section">
                <h2>Resumo do Dataset</h2>
                <p>Total de questões analisadas: {analysis_data.get('dataset_size', 'N/A')}</p>
            </div>
            
            <div class="section insights">
                <h2>Principais Insights</h2>
                {self._format_insights_html(analysis_data.get('insights', []))}
            </div>
        </body>
        </html>
        """
        return html
    
    def _format_insights_html(self, insights: List[Dict[str, Any]]) -> str:
        """Formata insights para HTML"""
        if not insights:
            return "<p>Nenhum insight disponível.</p>"
        
        html = "<ul>"
        for insight in insights:
            html += f"""
            <li>
                <strong>{insight.get('title', 'Insight')}</strong><br>
                {insight.get('description', '')}<br>
                <em>Recomendação: {insight.get('recommendation', '')}</em>
            </li>
            """
        html += "</ul>"
        return html

# Instância global
analytics = EnemAnalytics()
