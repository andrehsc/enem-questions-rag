#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soluções para Melhoria da Extração ENEM
=======================================
Propostas de melhorias para qualidade de extração e renderização de questões com imagens
"""

import sys
import json
from pathlib import Path
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))


class ExtractionImprovementSolutions:
    """Propostas de soluções para melhorar a extração."""
    
    def __init__(self):
        self.connection_string = "host=localhost port=5433 user=postgres password=postgres123 dbname=enem_questions"
        
    def analyze_current_data_quality(self) -> Dict:
        """Analisa qualidade atual dos dados no banco."""
        analysis = {
            'questions_with_corrupted_text': 0,
            'questions_with_images': 0,
            'questions_without_complete_alternatives': 0,
            'sample_corrupted_questions': [],
            'sample_image_questions': []
        }
        
        try:
            conn = psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)
            cursor = conn.cursor()
            
            # Contar questões com imagens
            cursor.execute("""
                SELECT COUNT(*) as count FROM enem_questions.questions 
                WHERE has_images = true
            """)
            analysis['questions_with_images'] = cursor.fetchone()['count']
            
            # Amostrar questões com imagens
            cursor.execute("""
                SELECT q.id, q.question_number, q.question_text,
                       COUNT(qi.id) as image_count
                FROM enem_questions.questions q
                LEFT JOIN enem_questions.question_images qi ON q.id = qi.question_id
                WHERE q.has_images = true
                GROUP BY q.id, q.question_number, q.question_text
                LIMIT 3
            """)
            
            image_samples = cursor.fetchall()
            analysis['sample_image_questions'] = [
                {
                    'id': str(row['id']),
                    'number': row['question_number'],
                    'text_preview': row['question_text'][:100] + '...',
                    'image_count': row['image_count']
                }
                for row in image_samples
            ]
            
            conn.close()
            
        except Exception as e:
            analysis['error'] = str(e)
            
        return analysis
    
    def propose_text_extraction_improvements(self) -> Dict:
        """Propõe melhorias para extração de texto."""
        return {
            'current_issues': [
                'Problemas de encoding UTF-8/Latin-1',
                'Caracteres especiais mal interpretados',
                'Parsing incompleto de alternativas',
                'Quebras de linha problemáticas'
            ],
            'proposed_solutions': {
                'encoding_normalization': {
                    'description': 'Implementar normalização de encoding robusta',
                    'implementation': {
                        'pre_processing': [
                            'Detectar encoding automaticamente (chardet)',
                            'Normalizar para UTF-8',
                            'Mapear caracteres problemáticos comuns',
                            'Aplicar correções específicas do ENEM'
                        ],
                        'post_processing': [
                            'Validar caracteres válidos para português',
                            'Corrigir acentuação comum',
                            'Remover artifacts de PDF'
                        ]
                    }
                },
                'alternative_parsing_enhancement': {
                    'description': 'Melhorar parsing de alternativas múltiplas',
                    'implementation': {
                        'regex_improvements': [
                            'Padrões mais robustos para A) B) C) D) E)',
                            'Detecção de alternativas em contextos complexos',
                            'Tratamento de alternativas com quebras de linha'
                        ],
                        'context_awareness': [
                            'Análise de layout de página',
                            'Detecção de colunas',
                            'Identificação de seções de questão'
                        ]
                    }
                }
            }
        }
    
    def propose_image_rendering_solutions(self) -> Dict:
        """Propõe soluções para renderização de questões com imagens."""
        return {
            'current_challenges': [
                'Imagens extraídas não associadas ao contexto da questão',
                'Falta de OCR para texto em imagens',
                'Necessidade de renderização completa para frontend',
                'Posicionamento correto de imagens no contexto'
            ],
            'comprehensive_solutions': {
                'solution_1_hybrid_rendering': {
                    'name': 'Sistema Híbrido de Renderização',
                    'description': 'Combinar texto extraído com imagens posicionadas',
                    'components': {
                        'image_positioning': {
                            'description': 'Mapear posição das imagens no texto',
                            'implementation': [
                                'Usar coordenadas bbox das imagens',
                                'Identificar pontos de inserção no texto',
                                'Criar marcadores de posição {{IMAGE_1}}',
                                'Manter ordem sequencial'
                            ]
                        },
                        'frontend_renderer': {
                            'description': 'Componente React/Vue para renderização',
                            'features': [
                                'Parser de texto com placeholders de imagem',
                                'Carregamento lazy de imagens',
                                'Zoom e pan para imagens complexas',
                                'Responsividade para mobile'
                            ]
                        }
                    }
                },
                'solution_2_ocr_enhancement': {
                    'name': 'Pipeline de OCR para Imagens',
                    'description': 'Extrair e indexar texto de imagens para busca completa',
                    'components': {
                        'ocr_processor': {
                            'libraries': ['pytesseract', 'easyocr', 'paddleocr'],
                            'preprocessing': [
                                'Conversão para escala de cinza',
                                'Ajuste de contraste e brilho',
                                'Remoção de ruído',
                                'Detecção de orientação'
                            ]
                        },
                        'text_integration': {
                            'description': 'Integrar texto de imagem com texto extraído',
                            'approach': [
                                'Identificar regiões de texto vs gráficos',
                                'Mesclar com texto principal quando apropriado',
                                'Manter separação para gráficos/diagramas',
                                'Indexar para busca full-text'
                            ]
                        }
                    }
                },
                'solution_3_pdf_native_rendering': {
                    'name': 'Renderização Nativa de PDF',
                    'description': 'Renderizar questões completas como imagens de alta qualidade',
                    'approach': {
                        'concept': 'Renderizar seções específicas do PDF como imagens',
                        'advantages': [
                            'Mantém formatação original exata',
                            'Preserva posicionamento de elementos',
                            'Não requer parsing complexo',
                            'Funciona com qualquer conteúdo'
                        ],
                        'implementation': [
                            'Identificar bbox de cada questão',
                            'Renderizar região como imagem PNG/SVG',
                            'Otimizar para diferentes resoluções',
                            'Gerar versões responsivas'
                        ]
                    }
                }
            },
            'recommended_approach': {
                'strategy': 'Híbrido Progressivo',
                'phases': [
                    {
                        'phase': 1,
                        'name': 'Melhorar Extração de Texto',
                        'tasks': [
                            'Implementar normalização de encoding',
                            'Melhorar parsing de alternativas',
                            'Adicionar validação de qualidade'
                        ],
                        'effort': 'Baixo',
                        'impact': 'Alto'
                    },
                    {
                        'phase': 2, 
                        'name': 'Sistema Híbrido Básico',
                        'tasks': [
                            'Mapear posições de imagem no texto',
                            'Criar placeholders {{IMAGE_N}}',
                            'Desenvolver componente de renderização'
                        ],
                        'effort': 'Médio',
                        'impact': 'Alto'
                    },
                    {
                        'phase': 3,
                        'name': 'OCR e Renderização Avançada',
                        'tasks': [
                            'Implementar pipeline de OCR',
                            'Renderização nativa de PDF como fallback',
                            'Otimização para diferentes dispositivos'
                        ],
                        'effort': 'Alto',
                        'impact': 'Muito Alto'
                    }
                ]
            }
        }
    
    def generate_implementation_plan(self) -> Dict:
        """Gera plano de implementação detalhado."""
        return {
            'immediate_improvements': {
                'priority': 'Alta',
                'time_estimate': '1-2 semanas',
                'tasks': [
                    {
                        'task': 'Correção de Encoding',
                        'file': 'src/enem_ingestion/parser.py',
                        'changes': 'Adicionar normalize_text_encoding() na função _clean_question_text'
                    },
                    {
                        'task': 'Melhorar Parsing de Alternativas', 
                        'file': 'src/enem_ingestion/parser.py',
                        'changes': 'Refatorar _extract_alternatives() com múltiplos padrões'
                    },
                    {
                        'task': 'Associar Imagens ao Contexto',
                        'file': 'src/enem_ingestion/image_extractor.py',
                        'changes': 'Adicionar mapeamento de posição de imagens no texto'
                    }
                ]
            },
            'medium_term_enhancements': {
                'priority': 'Média',
                'time_estimate': '3-4 semanas',
                'tasks': [
                    {
                        'task': 'GraphQL Schema Enhancement',
                        'file': 'api/graphql_types.py',
                        'changes': 'Adicionar campos de imagem com placeholder mapping'
                    },
                    {
                        'task': 'Frontend Component',
                        'file': 'frontend/components/QuestionRenderer.tsx',
                        'changes': 'Criar componente de renderização híbrida'
                    },
                    {
                        'task': 'Image Optimization',
                        'file': 'api/image_service.py', 
                        'changes': 'Serviço de redimensionamento e otimização'
                    }
                ]
            },
            'advanced_features': {
                'priority': 'Baixa',
                'time_estimate': '6-8 semanas',
                'tasks': [
                    {
                        'task': 'OCR Pipeline',
                        'file': 'src/enem_ingestion/ocr_processor.py',
                        'changes': 'Pipeline completo de OCR com múltiplas engines'
                    },
                    {
                        'task': 'PDF Native Rendering',
                        'file': 'src/enem_ingestion/pdf_renderer.py',
                        'changes': 'Renderização de regiões específicas como imagem'
                    },
                    {
                        'task': 'Search Enhancement',
                        'file': 'api/search_service.py',
                        'changes': 'Busca full-text incluindo texto de imagens'
                    }
                ]
            }
        }


def print_improvement_report(solutions: ExtractionImprovementSolutions):
    """Imprime relatório completo de melhorias."""
    
    print("🏗️ ARCHITECT - RELATÓRIO DE MELHORIAS PARA EXTRAÇÃO ENEM")
    print("="*70)
    
    # Análise atual
    current_analysis = solutions.analyze_current_data_quality()
    print(f"\n📊 ANÁLISE DA SITUAÇÃO ATUAL:")
    print(f"  • Questões com imagens: {current_analysis.get('questions_with_images', 'N/A')}")
    
    if current_analysis.get('sample_image_questions'):
        print(f"\n  🔍 Exemplos de questões com imagens:")
        for sample in current_analysis['sample_image_questions']:
            print(f"    - Questão #{sample['number']}: {sample['image_count']} imagem(s)")
    
    # Soluções propostas
    text_solutions = solutions.propose_text_extraction_improvements()
    print(f"\n🛠️  PROBLEMAS IDENTIFICADOS:")
    
    for issue in text_solutions['current_issues']:
        print(f"  ❌ {issue}")
    
    print(f"\n💡 MELHORIAS PROPOSTAS:")
    for sol_key, solution in text_solutions['proposed_solutions'].items():
        print(f"  ✅ {solution['description']}")
    
    # Soluções de renderização
    image_solutions = solutions.propose_image_rendering_solutions()
    print(f"\n🖼️  SOLUÇÕES PARA RENDERIZAÇÃO DE IMAGENS:")
    
    recommended = image_solutions['recommended_approach']
    print(f"\n📋 ESTRATÉGIA RECOMENDADA: {recommended['strategy']}")
    
    for phase in recommended['phases']:
        print(f"\n  FASE {phase['phase']}: {phase['name']} (Esforço: {phase['effort']}, Impacto: {phase['impact']})")
        for task in phase['tasks']:
            print(f"    • {task}")
    
    # Plano de implementação
    impl_plan = solutions.generate_implementation_plan()
    print(f"\n🚀 PLANO DE IMPLEMENTAÇÃO:")
    
    for category, details in impl_plan.items():
        print(f"\n  📅 {category.replace('_', ' ').upper()}:")
        print(f"    Prioridade: {details['priority']}")
        print(f"    Estimativa: {details['time_estimate']}")
        print(f"    Tarefas:")
        for task in details['tasks']:
            print(f"      • {task['task']} ({task['file']})")


if __name__ == "__main__":
    solutions = ExtractionImprovementSolutions()
    print_improvement_report(solutions)