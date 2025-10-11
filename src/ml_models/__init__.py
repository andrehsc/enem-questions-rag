#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo ML Models - Modelos de Machine Learning para questões ENEM

Este módulo contém modelos de ML especializados para:
- Predição de dificuldade de questões
- Classificação de matérias/temas
- Análise de padrões em questões
- Recomendação de conteúdo
"""

from .difficulty_predictor import EnemDifficultyPredictor, difficulty_predictor
from .subject_classifier import EnemSubjectClassifier, subject_classifier

__version__ = "1.0.0"
__author__ = "ENEM RAG System - ML Team"

# Interfaces principais do módulo
__all__ = [
    # Classes principais
    "EnemDifficultyPredictor",
    "EnemSubjectClassifier",
    
    # Instâncias globais prontas para uso
    "difficulty_predictor",
    "subject_classifier"
]

# Configurações padrão dos modelos
ML_CONFIG = {
    "difficulty_predictor": {
        "default_model": "random_forest",
        "test_size": 0.2,
        "cross_validation_folds": 5,
        "feature_selection": True
    },
    "subject_classifier": {
        "default_model": "naive_bayes",
        "test_size": 0.2,
        "use_grid_search": False,
        "max_features": 1000
    },
    "general": {
        "random_state": 42,
        "n_jobs": -1,
        "verbose": 1
    }
}

def get_ml_info():
    """Retorna informações sobre os modelos ML disponíveis"""
    return {
        "name": "ENEM ML Models",
        "version": __version__,
        "models": {
            "difficulty_predictor": {
                "description": "Prediz dificuldade de questões ENEM",
                "algorithms": ["Random Forest", "Gradient Boosting"],
                "features": ["texto", "estrutura", "metadados", "linguística"],
                "output": "classes de dificuldade + probabilidades"
            },
            "subject_classifier": {
                "description": "Classifica matérias/temas de questões",
                "algorithms": ["Naive Bayes", "SVM", "Random Forest"],
                "features": ["TF-IDF", "palavras-chave", "padrões específicos"],
                "output": "matéria/tema + confiança"
            }
        },
        "dependencies": [
            "scikit-learn>=1.1.0",
            "pandas>=1.5.0",
            "numpy>=1.21.0",
            "joblib>=1.2.0"
        ],
        "capabilities": [
            "Predição de dificuldade automática",
            "Classificação automática de matérias",
            "Análise de features importantes",
            "Validação cruzada",
            "Otimização de hiperparâmetros",
            "Salvamento/carregamento de modelos"
        ]
    }

def train_all_models(questions_data, difficulty_field='dificuldade', subject_field='materia'):
    """
    Treina todos os modelos disponíveis
    
    Args:
        questions_data: Lista de questões com labels
        difficulty_field: Campo de dificuldade
        subject_field: Campo de matéria
    
    Returns:
        dict: Resultados de treinamento de todos os modelos
    """
    results = {
        "training_started": True,
        "models_trained": {},
        "errors": []
    }
    
    # Treinar preditor de dificuldade
    try:
        difficulty_metrics = difficulty_predictor.train(
            questions=questions_data,
            difficulty_field=difficulty_field,
            test_size=ML_CONFIG["difficulty_predictor"]["test_size"]
        )
        results["models_trained"]["difficulty_predictor"] = difficulty_metrics
    except Exception as e:
        results["errors"].append({
            "model": "difficulty_predictor",
            "error": str(e)
        })
    
    # Treinar classificador de matérias
    try:
        subject_metrics = subject_classifier.train(
            questions=questions_data,
            subject_field=subject_field,
            test_size=ML_CONFIG["subject_classifier"]["test_size"],
            use_grid_search=ML_CONFIG["subject_classifier"]["use_grid_search"]
        )
        results["models_trained"]["subject_classifier"] = subject_metrics
    except Exception as e:
        results["errors"].append({
            "model": "subject_classifier", 
            "error": str(e)
        })
    
    return results

def predict_all(questions_data):
    """
    Executa todas as predições disponíveis
    
    Args:
        questions_data: Lista de questões
    
    Returns:
        dict: Predições de todos os modelos
    """
    results = {
        "predictions": {},
        "errors": []
    }
    
    # Predição de dificuldade
    try:
        difficulty_predictions = difficulty_predictor.predict_difficulty(
            questions=questions_data,
            return_probabilities=True
        )
        results["predictions"]["difficulty"] = difficulty_predictions
    except Exception as e:
        results["errors"].append({
            "model": "difficulty_predictor",
            "error": str(e)
        })
    
    # Classificação de matéria
    try:
        subject_predictions = subject_classifier.predict_subject(
            questions=questions_data,
            return_probabilities=True
        )
        results["predictions"]["subject"] = subject_predictions
    except Exception as e:
        results["errors"].append({
            "model": "subject_classifier",
            "error": str(e)
        })
    
    return results

def get_models_status():
    """Retorna status de todos os modelos"""
    status = {
        "difficulty_predictor": {
            "trained": difficulty_predictor.pipeline is not None,
            "metrics": difficulty_predictor.model_metrics,
            "type": difficulty_predictor.model_type
        },
        "subject_classifier": {
            "trained": subject_classifier.pipeline is not None,
            "metrics": subject_classifier.model_metrics,
            "type": subject_classifier.classifier_type
        }
    }
    
    return status

def quick_start_guide():
    """Retorna guia rápido de uso dos modelos ML"""
    return """
    === ENEM ML Models - Guia Rápido ===
    
    1. Treinar Preditor de Dificuldade:
       from src.ml_models import difficulty_predictor
       metrics = difficulty_predictor.train(questions_with_difficulty)
    
    2. Predizer Dificuldade:
       predictions = difficulty_predictor.predict_difficulty(
           questions=new_questions,
           return_probabilities=True
       )
    
    3. Treinar Classificador de Matérias:
       from src.ml_models import subject_classifier
       metrics = subject_classifier.train(questions_with_subjects)
    
    4. Classificar Matérias:
       classifications = subject_classifier.predict_subject(
           questions=new_questions,
           return_probabilities=True
       )
    
    5. Treinar Todos os Modelos:
       from src.ml_models import train_all_models
       results = train_all_models(labeled_questions)
    
    6. Executar Todas as Predições:
       from src.ml_models import predict_all
       all_predictions = predict_all(questions)
    
    7. Verificar Status dos Modelos:
       from src.ml_models import get_models_status
       status = get_models_status()
    
    8. Salvar/Carregar Modelos:
       difficulty_predictor.save_model("difficulty_model.pkl")
       difficulty_predictor.load_model("difficulty_model.pkl")
    """

# Configuração de logging para os modelos
import logging
logging.getLogger('src.ml_models').setLevel(logging.INFO)
