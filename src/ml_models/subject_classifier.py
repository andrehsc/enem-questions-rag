#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classificador de matérias/temas para questões ENEM
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.pipeline import Pipeline
import joblib
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

class EnemSubjectClassifier:
    """Classificador de matérias/temas para questões ENEM"""
    
    def __init__(self, classifier_type: str = "naive_bayes"):
        """
        Inicializa o classificador de matérias
        
        Args:
            classifier_type: Tipo do classificador (naive_bayes, svm, random_forest)
        """
        self.classifier_type = classifier_type
        self.pipeline = None
        self.label_encoder = LabelEncoder()
        self.subject_keywords = {}
        self.model_metrics = {}
        
        # Configurar modelo base
        if classifier_type == "naive_bayes":
            self.base_model = MultinomialNB(alpha=1.0)
        elif classifier_type == "svm":
            self.base_model = SVC(kernel='linear', probability=True, random_state=42)
        elif classifier_type == "random_forest":
            self.base_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
        else:
            raise ValueError(f"Classificador não suportado: {classifier_type}")
    
    def preprocess_text(self, text: str) -> str:
        """
        Pré-processa texto para classificação
        
        Args:
            text: Texto a ser processado
        
        Returns:
            Texto processado
        """
        if not text:
            return ""
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover caracteres especiais mas manter acentos
        text = re.sub(r'[^\w\sáàâãéèêíìîõóòôúùûç]', ' ', text)
        
        # Remover espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_subject_keywords(self, questions: List[Dict[str, Any]], subject_field: str = 'materia') -> Dict[str, List[str]]:
        """
        Extrai palavras-chave características de cada matéria
        
        Args:
            questions: Lista de questões
            subject_field: Campo que contém a matéria
        
        Returns:
            Dicionário com palavras-chave por matéria
        """
        subject_texts = {}
        
        # Agrupar textos por matéria
        for question in questions:
            subject = question.get(subject_field, 'desconhecida')
            text = question.get('enunciado', '')
            
            # Incluir alternativas no texto
            alternatives = question.get('alternativas', {})
            if alternatives:
                if isinstance(alternatives, dict):
                    alt_text = ' '.join(alternatives.values())
                else:
                    alt_text = ' '.join(str(alt) for alt in alternatives)
                text += ' ' + alt_text
            
            processed_text = self.preprocess_text(text)
            
            if subject not in subject_texts:
                subject_texts[subject] = []
            subject_texts[subject].append(processed_text)
        
        # Extrair palavras-chave usando TF-IDF para cada matéria
        keywords = {}
        
        for subject, texts in subject_texts.items():
            if len(texts) < 2:
                continue
            
            # Combinar todos os textos da matéria
            combined_text = ' '.join(texts)
            
            # Usar TF-IDF para encontrar palavras características
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='portuguese' if hasattr(TfidfVectorizer(), 'PORTUGUESE_STOP_WORDS') else None,
                ngram_range=(1, 2),
                min_df=1
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform([combined_text])
                feature_names = vectorizer.get_feature_names_out()
                scores = tfidf_matrix.toarray()[0]
                
                # Pegar as top palavras
                top_indices = np.argsort(scores)[-20:][::-1]
                keywords[subject] = [feature_names[i] for i in top_indices if scores[i] > 0]
                
            except Exception as e:
                logger.warning(f"Erro ao extrair keywords para {subject}: {str(e)}")
                keywords[subject] = []
        
        self.subject_keywords = keywords
        return keywords
    
    def create_enhanced_features(self, questions: List[Dict[str, Any]]) -> Tuple[List[str], pd.DataFrame]:
        """
        Cria features aprimoradas para classificação
        
        Args:
            questions: Lista de questões
        
        Returns:
            Textos processados e features numéricas
        """
        texts = []
        features_list = []
        
        for question in questions:
            # Processar texto principal
            text = question.get('enunciado', '')
            alternatives = question.get('alternativas', {})
            
            if alternatives:
                if isinstance(alternatives, dict):
                    alt_text = ' '.join(alternatives.values())
                else:
                    alt_text = ' '.join(str(alt) for alt in alternatives)
                text += ' ' + alt_text
            
            processed_text = self.preprocess_text(text)
            texts.append(processed_text)
            
            # Features numéricas adicionais
            features = {}
            features['text_length'] = len(text)
            features['word_count'] = len(processed_text.split())
            features['year'] = question.get('ano', 0)
            
            # Features baseadas em palavras-chave de matérias
            for subject, keywords in self.subject_keywords.items():
                keyword_count = sum(1 for keyword in keywords if keyword in processed_text)
                features[f'keywords_{subject}'] = keyword_count
            
            # Features de padrões específicos
            features['has_formula'] = int(any(char in text for char in ['=', '+', '-', '*', '/', '^']))
            features['has_numbers'] = int(any(char.isdigit() for char in text))
            features['has_percentage'] = int('%' in text)
            features['has_currency'] = int(any(symbol in text for symbol in ['R$', '$', '€']))
            
            # Features de conteúdo específico
            math_keywords = ['função', 'equação', 'gráfico', 'derivada', 'integral', 'matriz']
            features['math_indicators'] = sum(1 for keyword in math_keywords if keyword in processed_text)
            
            physics_keywords = ['força', 'energia', 'velocidade', 'aceleração', 'campo', 'onda']
            features['physics_indicators'] = sum(1 for keyword in physics_keywords if keyword in processed_text)
            
            chemistry_keywords = ['átomo', 'molécula', 'reação', 'elemento', 'ligação', 'ph']
            features['chemistry_indicators'] = sum(1 for keyword in chemistry_keywords if keyword in processed_text)
            
            biology_keywords = ['célula', 'gene', 'proteína', 'evolução', 'espécie', 'organismo']
            features['biology_indicators'] = sum(1 for keyword in biology_keywords if keyword in processed_text)
            
            history_keywords = ['século', 'guerra', 'império', 'revolução', 'colonial', 'república']
            features['history_indicators'] = sum(1 for keyword in history_keywords if keyword in processed_text)
            
            geography_keywords = ['clima', 'região', 'população', 'território', 'urbano', 'rural']
            features['geography_indicators'] = sum(1 for keyword in geography_keywords if keyword in processed_text)
            
            features_list.append(features)
        
        features_df = pd.DataFrame(features_list).fillna(0)
        return texts, features_df
    
    def train(
        self,
        questions: List[Dict[str, Any]],
        subject_field: str = 'materia',
        test_size: float = 0.2,
        use_grid_search: bool = False
    ) -> Dict[str, Any]:
        """
        Treina o classificador de matérias
        
        Args:
            questions: Lista de questões com matérias conhecidas
            subject_field: Campo que contém a matéria
            test_size: Proporção para teste
            use_grid_search: Se deve usar busca em grade para otimização
        
        Returns:
            Métricas de treinamento
        """
        # Filtrar questões com matéria definida
        valid_questions = [q for q in questions if subject_field in q and q[subject_field]]
        
        if len(valid_questions) < 10:
            return {"error": "Dados insuficientes para treinamento"}
        
        # Extrair palavras-chave das matérias
        self.extract_subject_keywords(valid_questions, subject_field)
        
        # Criar features
        texts, numeric_features = self.create_enhanced_features(valid_questions)
        
        # Preparar labels
        y_raw = [q[subject_field] for q in valid_questions]
        y = self.label_encoder.fit_transform(y_raw)
        
        # Criar pipeline
        if self.classifier_type == "naive_bayes":
            # Para Naive Bayes, usar apenas features de texto
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=1000,
                    stop_words='portuguese' if hasattr(TfidfVectorizer(), 'PORTUGUESE_STOP_WORDS') else None,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )),
                ('classifier', self.base_model)
            ])
            X = texts
        else:
            # Para outros modelos, combinar features de texto e numéricas
            tfidf_vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words='portuguese' if hasattr(TfidfVectorizer(), 'PORTUGUESE_STOP_WORDS') else None,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            text_features = tfidf_vectorizer.fit_transform(texts).toarray()
            X = np.hstack([text_features, numeric_features.values])
            
            self.pipeline = Pipeline([
                ('classifier', self.base_model)
            ])
            self.tfidf_vectorizer = tfidf_vectorizer
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Otimização com Grid Search (opcional)
        if use_grid_search:
            if self.classifier_type == "naive_bayes":
                param_grid = {
                    'tfidf__max_features': [500, 1000, 1500],
                    'classifier__alpha': [0.1, 1.0, 10.0]
                }
            elif self.classifier_type == "svm":
                param_grid = {
                    'classifier__C': [0.1, 1.0, 10.0],
                    'classifier__gamma': ['scale', 'auto']
                }
            else:  # random_forest
                param_grid = {
                    'classifier__n_estimators': [50, 100, 200],
                    'classifier__max_depth': [5, 10, None]
                }
            
            grid_search = GridSearchCV(
                self.pipeline, param_grid, cv=3, scoring='accuracy', n_jobs=-1
            )
            grid_search.fit(X_train, y_train)
            self.pipeline = grid_search.best_estimator_
            best_params = grid_search.best_params_
        else:
            self.pipeline.fit(X_train, y_train)
            best_params = {}
        
        # Avaliar modelo
        train_score = self.pipeline.score(X_train, y_train)
        test_score = self.pipeline.score(X_test, y_test)
        
        # Predições para relatório detalhado
        y_pred = self.pipeline.predict(X_test)
        
        # Métricas detalhadas
        self.model_metrics = {
            "train_accuracy": float(train_score),
            "test_accuracy": float(test_score),
            "n_samples": len(valid_questions),
            "n_classes": len(self.label_encoder.classes_),
            "classes": self.label_encoder.classes_.tolist(),
            "best_params": best_params,
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "trained_at": datetime.now().isoformat()
        }
        
        logger.info(f"Classificador treinado: {test_score:.3f} de acurácia")
        
        return self.model_metrics
    
    def predict_subject(
        self,
        questions: List[Dict[str, Any]],
        return_probabilities: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Classifica matérias das questões
        
        Args:
            questions: Lista de questões
            return_probabilities: Se deve retornar probabilidades
        
        Returns:
            Lista com classificações
        """
        if not self.pipeline:
            return [{"error": "Modelo não treinado"}]
        
        # Preparar dados
        texts, numeric_features = self.create_enhanced_features(questions)
        
        if self.classifier_type == "naive_bayes":
            X = texts
        else:
            text_features = self.tfidf_vectorizer.transform(texts).toarray()
            X = np.hstack([text_features, numeric_features.values])
        
        # Predições
        predictions = self.pipeline.predict(X)
        predicted_labels = self.label_encoder.inverse_transform(predictions)
        
        results = []
        for i, question in enumerate(questions):
            result = {
                "question_id": question.get('id', i),
                "predicted_subject": predicted_labels[i],
                "confidence": "calculando..."
            }
            
            if return_probabilities and hasattr(self.pipeline.named_steps.get('classifier', self.pipeline), 'predict_proba'):
                try:
                    if self.classifier_type == "naive_bayes":
                        probabilities = self.pipeline.predict_proba([texts[i]])[0]
                    else:
                        probabilities = self.pipeline.predict_proba(X[i:i+1])[0]
                    
                    prob_dict = {}
                    for j, prob in enumerate(probabilities):
                        prob_dict[self.label_encoder.classes_[j]] = float(prob)
                    result["probabilities"] = prob_dict
                    result["confidence"] = float(max(probabilities))
                except Exception as e:
                    result["probabilities"] = {"error": str(e)}
            
            results.append(result)
        
        return results
    
    def get_subject_keywords(self, subject: str = None) -> Dict[str, List[str]]:
        """
        Retorna palavras-chave das matérias
        
        Args:
            subject: Matéria específica (opcional)
        
        Returns:
            Palavras-chave por matéria
        """
        if subject:
            return {subject: self.subject_keywords.get(subject, [])}
        return self.subject_keywords
    
    def analyze_misclassifications(
        self,
        questions: List[Dict[str, Any]],
        true_subjects: List[str]
    ) -> Dict[str, Any]:
        """
        Analisa erros de classificação
        
        Args:
            questions: Lista de questões
            true_subjects: Matérias verdadeiras
        
        Returns:
            Análise dos erros
        """
        predictions = self.predict_subject(questions)
        predicted_subjects = [p["predicted_subject"] for p in predictions]
        
        # Matriz de confusão
        confusion = confusion_matrix(true_subjects, predicted_subjects)
        
        # Erros mais comuns
        errors = []
        for i, (true, pred) in enumerate(zip(true_subjects, predicted_subjects)):
            if true != pred:
                errors.append({
                    "question_id": questions[i].get('id', i),
                    "true_subject": true,
                    "predicted_subject": pred,
                    "text_preview": questions[i].get('enunciado', '')[:100] + '...'
                })
        
        return {
            "confusion_matrix": confusion.tolist(),
            "total_errors": len(errors),
            "error_rate": len(errors) / len(questions),
            "common_errors": Counter([(e["true_subject"], e["predicted_subject"]) for e in errors]).most_common(10),
            "sample_errors": errors[:10]
        }
    
    def save_model(self, filepath: str) -> str:
        """Salva o modelo treinado"""
        if not self.pipeline:
            return "Erro: Modelo não treinado"
        
        model_data = {
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder,
            'subject_keywords': self.subject_keywords,
            'metrics': self.model_metrics,
            'classifier_type': self.classifier_type
        }
        
        if hasattr(self, 'tfidf_vectorizer'):
            model_data['tfidf_vectorizer'] = self.tfidf_vectorizer
        
        joblib.dump(model_data, filepath)
        return f"Modelo salvo em: {filepath}"
    
    def load_model(self, filepath: str) -> str:
        """Carrega modelo salvo"""
        try:
            model_data = joblib.load(filepath)
            
            self.pipeline = model_data['pipeline']
            self.label_encoder = model_data['label_encoder']
            self.subject_keywords = model_data['subject_keywords']
            self.model_metrics = model_data['metrics']
            self.classifier_type = model_data['classifier_type']
            
            if 'tfidf_vectorizer' in model_data:
                self.tfidf_vectorizer = model_data['tfidf_vectorizer']
            
            return f"Modelo carregado de: {filepath}"
        except Exception as e:
            return f"Erro ao carregar modelo: {str(e)}"

# Instância global
subject_classifier = EnemSubjectClassifier()
