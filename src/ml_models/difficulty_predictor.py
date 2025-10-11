#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preditor de dificuldade de questões ENEM usando ML
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
import joblib
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EnemDifficultyPredictor:
    """Preditor de dificuldade de questões ENEM"""
    
    def __init__(self, model_type: str = "random_forest"):
        """
        Inicializa o preditor de dificuldade
        
        Args:
            model_type: Tipo do modelo (random_forest, gradient_boosting)
        """
        self.model_type = model_type
        self.pipeline = None
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.model_metrics = {}
        
        # Configurar modelo base
        if model_type == "random_forest":
            self.base_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
        elif model_type == "gradient_boosting":
            self.base_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=6,
                random_state=42
            )
        else:
            raise ValueError(f"Modelo não suportado: {model_type}")
    
    def extract_features(self, questions: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Extrai features das questões para predição
        
        Args:
            questions: Lista de questões
        
        Returns:
            DataFrame com features extraídas
        """
        features_list = []
        
        for question in questions:
            features = {}
            
            # Features de texto
            text = question.get('enunciado', '')
            if text:
                features['text_length'] = len(text)
                features['word_count'] = len(text.split())
                features['sentence_count'] = text.count('.') + text.count('!') + text.count('?')
                features['avg_word_length'] = np.mean([len(word) for word in text.split()]) if text.split() else 0
                
                # Features de complexidade
                features['question_marks'] = text.count('?')
                features['exclamation_marks'] = text.count('!')
                features['parentheses'] = text.count('(') + text.count(')')
                features['numbers_count'] = sum(1 for char in text if char.isdigit())
                
                # Features linguísticas
                features['uppercase_ratio'] = sum(1 for char in text if char.isupper()) / len(text) if text else 0
                features['punctuation_ratio'] = sum(1 for char in text if not char.isalnum() and not char.isspace()) / len(text) if text else 0
            
            # Features de alternativas
            alternatives = question.get('alternativas', {})
            if alternatives:
                features['num_alternatives'] = len(alternatives)
                alt_texts = list(alternatives.values()) if isinstance(alternatives, dict) else alternatives
                if alt_texts:
                    alt_lengths = [len(str(alt)) for alt in alt_texts]
                    features['avg_alternative_length'] = np.mean(alt_lengths)
                    features['max_alternative_length'] = max(alt_lengths)
                    features['min_alternative_length'] = min(alt_lengths)
                    features['alternative_length_std'] = np.std(alt_lengths)
            
            # Features de metadados
            features['year'] = question.get('ano', 0)
            features['subject'] = question.get('materia', 'desconhecida')
            features['area'] = question.get('area', 'desconhecida')
            
            # Feature de gabarito (posição da resposta)
            gabarito = question.get('gabarito', '')
            if gabarito and gabarito in ['A', 'B', 'C', 'D', 'E']:
                features['answer_position'] = ord(gabarito) - ord('A')
            else:
                features['answer_position'] = -1
            
            features_list.append(features)
        
        df = pd.DataFrame(features_list)
        
        # Encoding de variáveis categóricas
        categorical_columns = ['subject', 'area']
        for col in categorical_columns:
            if col in df.columns:
                df[f'{col}_encoded'] = pd.Categorical(df[col]).codes
                df = df.drop(columns=[col])
        
        # Preencher valores NaN
        df = df.fillna(0)
        
        return df
    
    def prepare_text_features(self, questions: List[Dict[str, Any]]) -> Tuple[np.ndarray, TfidfVectorizer]:
        """
        Prepara features de texto usando TF-IDF
        
        Args:
            questions: Lista de questões
        
        Returns:
            Matriz TF-IDF e vectorizer
        """
        texts = []
        for question in questions:
            text = question.get('enunciado', '')
            # Incluir alternativas no texto
            alternatives = question.get('alternativas', {})
            if alternatives:
                if isinstance(alternatives, dict):
                    alt_text = ' '.join(alternatives.values())
                else:
                    alt_text = ' '.join(str(alt) for alt in alternatives)
                text += ' ' + alt_text
            texts.append(text)
        
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='portuguese' if hasattr(TfidfVectorizer(), 'PORTUGUESE_STOP_WORDS') else None,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        tfidf_matrix = vectorizer.fit_transform(texts)
        return tfidf_matrix.toarray(), vectorizer
    
    def train(
        self,
        questions: List[Dict[str, Any]],
        difficulty_field: str = 'dificuldade',
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Treina o modelo de predição de dificuldade
        
        Args:
            questions: Lista de questões com dificuldade conhecida
            difficulty_field: Campo que contém a dificuldade
            test_size: Proporção para teste
        
        Returns:
            Métricas de treinamento
        """
        # Filtrar questões com dificuldade definida
        valid_questions = [q for q in questions if difficulty_field in q and q[difficulty_field]]
        
        if len(valid_questions) < 10:
            return {"error": "Dados insuficientes para treinamento"}
        
        # Extrair features numéricas
        numeric_features = self.extract_features(valid_questions)
        
        # Extrair features de texto
        text_features, text_vectorizer = self.prepare_text_features(valid_questions)
        
        # Combinar features
        X = np.hstack([numeric_features.values, text_features])
        
        # Preparar labels
        y_raw = [q[difficulty_field] for q in valid_questions]
        y = self.label_encoder.fit_transform(y_raw)
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Criar pipeline
        self.pipeline = Pipeline([
            ('classifier', self.base_model)
        ])
        
        # Treinar modelo
        self.pipeline.fit(X_train, y_train)
        
        # Avaliar modelo
        train_score = self.pipeline.score(X_train, y_train)
        test_score = self.pipeline.score(X_test, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(self.pipeline, X, y, cv=5)
        
        # Predições para relatório detalhado
        y_pred = self.pipeline.predict(X_test)
        
        # Salvar componentes
        self.text_vectorizer = text_vectorizer
        self.feature_names = list(numeric_features.columns) + [f'tfidf_{i}' for i in range(text_features.shape[1])]
        
        # Métricas
        self.model_metrics = {
            "train_accuracy": float(train_score),
            "test_accuracy": float(test_score),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "n_samples": len(valid_questions),
            "n_features": X.shape[1],
            "classes": self.label_encoder.classes_.tolist(),
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "trained_at": datetime.now().isoformat()
        }
        
        logger.info(f"Modelo treinado: {test_score:.3f} de acurácia no teste")
        
        return self.model_metrics
    
    def predict_difficulty(
        self,
        questions: List[Dict[str, Any]],
        return_probabilities: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Prediz dificuldade de questões
        
        Args:
            questions: Lista de questões
            return_probabilities: Se deve retornar probabilidades
        
        Returns:
            Lista com predições
        """
        if not self.pipeline:
            return [{"error": "Modelo não treinado"}]
        
        # Extrair features
        numeric_features = self.extract_features(questions)
        text_features, _ = self.prepare_text_features(questions)
        
        # Recriar features usando o vectorizer treinado
        texts = []
        for question in questions:
            text = question.get('enunciado', '')
            alternatives = question.get('alternativas', {})
            if alternatives:
                if isinstance(alternatives, dict):
                    alt_text = ' '.join(alternatives.values())
                else:
                    alt_text = ' '.join(str(alt) for alt in alternatives)
                text += ' ' + alt_text
            texts.append(text)
        
        text_features_transformed = self.text_vectorizer.transform(texts).toarray()
        
        # Combinar features
        X = np.hstack([numeric_features.values, text_features_transformed])
        
        # Predições
        predictions = self.pipeline.predict(X)
        predicted_labels = self.label_encoder.inverse_transform(predictions)
        
        results = []
        for i, question in enumerate(questions):
            result = {
                "question_id": question.get('id', i),
                "predicted_difficulty": predicted_labels[i],
                "confidence": "calculando..."
            }
            
            if return_probabilities:
                probabilities = self.pipeline.predict_proba(X[i:i+1])[0]
                prob_dict = {}
                for j, prob in enumerate(probabilities):
                    prob_dict[self.label_encoder.classes_[j]] = float(prob)
                result["probabilities"] = prob_dict
                result["confidence"] = float(max(probabilities))
            
            results.append(result)
        
        return results
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """
        Retorna importância das features
        
        Args:
            top_n: Número de features mais importantes
        
        Returns:
            Dicionário com importâncias
        """
        if not self.pipeline or not hasattr(self.pipeline.named_steps['classifier'], 'feature_importances_'):
            return {"error": "Modelo não suporta feature importance"}
        
        importances = self.pipeline.named_steps['classifier'].feature_importances_
        
        # Combinar com nomes das features
        feature_importance = dict(zip(self.feature_names, importances))
        
        # Ordenar por importância
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_features[:top_n])
    
    def save_model(self, filepath: str) -> str:
        """Salva o modelo treinado"""
        if not self.pipeline:
            return "Erro: Modelo não treinado"
        
        model_data = {
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder,
            'text_vectorizer': self.text_vectorizer,
            'feature_names': self.feature_names,
            'metrics': self.model_metrics,
            'model_type': self.model_type
        }
        
        joblib.dump(model_data, filepath)
        return f"Modelo salvo em: {filepath}"
    
    def load_model(self, filepath: str) -> str:
        """Carrega modelo salvo"""
        try:
            model_data = joblib.load(filepath)
            
            self.pipeline = model_data['pipeline']
            self.label_encoder = model_data['label_encoder']
            self.text_vectorizer = model_data['text_vectorizer']
            self.feature_names = model_data['feature_names']
            self.model_metrics = model_data['metrics']
            self.model_type = model_data['model_type']
            
            return f"Modelo carregado de: {filepath}"
        except Exception as e:
            return f"Erro ao carregar modelo: {str(e)}"

# Instância global
difficulty_predictor = EnemDifficultyPredictor()
