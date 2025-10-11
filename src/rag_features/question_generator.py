#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de questões estilo ENEM usando LLM
"""

import openai
from typing import List, Dict, Any, Optional
import asyncio
import json
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnemQuestionGenerator:
    """Gerador de questões no estilo ENEM usando LLM"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        """
        Inicializa o gerador de questões
        
        Args:
            api_key: Chave da API OpenAI
            model: Modelo a ser usado
        """
        if api_key:
            openai.api_key = api_key
        self.model = model
        
        # Templates de prompt para diferentes tipos de questão
        self.prompt_templates = {
            "multiple_choice": """
Você é um especialista em criar questões no estilo ENEM. 
Crie uma questão de múltipla escolha sobre o tema: {topic}

Características obrigatórias:
- Contextualização clara e realista
- 5 alternativas (A, B, C, D, E)
- Apenas uma alternativa correta
- Nível de dificuldade: {difficulty}
- Área: {subject}
- Competência ENEM aplicável

Formato de resposta JSON:
{
    "enunciado": "texto da questão com contexto",
    "alternativas": {
        "A": "texto alternativa A",
        "B": "texto alternativa B", 
        "C": "texto alternativa C",
        "D": "texto alternativa D",
        "E": "texto alternativa E"
    },
    "gabarito": "letra_correta",
    "explicacao": "explicação detalhada da resposta",
    "competencia": "competência ENEM relacionada",
    "tema": "{topic}",
    "dificuldade": "{difficulty}"
}
""",
            
            "essay_prompt": """
Você é um especialista em redação ENEM.
Crie uma proposta de redação sobre o tema: {topic}

Características obrigatórias:
- Tema atual e relevante
- Textos motivadores (2-3 textos)
- Comando claro
- Tipo: dissertativo-argumentativo
- Seguir estrutura oficial do ENEM

Formato de resposta JSON:
{
    "tema": "{topic}",
    "titulo": "título da proposta",
    "instrucoes": "instruções para o candidato",
    "textos_motivadores": [
        {
            "numero": 1,
            "tipo": "texto/grafico/imagem",
            "conteudo": "conteúdo do texto motivador",
            "fonte": "fonte do texto"
        }
    ],
    "comando": "comando da redação",
    "criterios": ["critério 1", "critério 2", "critério 3"]
}
""",
            
            "analytical": """
Você é um especialista em questões analíticas ENEM.
Crie uma questão que exija análise e interpretação sobre: {topic}

Características obrigatórias:
- Apresente dados, gráficos ou situação complexa
- Exija análise crítica e interpretação
- 5 alternativas com diferentes níveis de análise
- Área: {subject}
- Dificuldade: {difficulty}

Formato similar ao multiple_choice mas com foco analítico.
"""
        }
    
    async def generate_question(
        self,
        topic: str,
        question_type: str = "multiple_choice",
        subject: str = "Ciências Humanas",
        difficulty: str = "médio",
        style_reference: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Gera uma questão no estilo ENEM
        
        Args:
            topic: Tema da questão
            question_type: Tipo da questão (multiple_choice, essay_prompt, analytical)
            subject: Área do conhecimento
            difficulty: Nível de dificuldade
            style_reference: Questão de referência para manter o estilo
        
        Returns:
            Questão gerada no formato especificado
        """
        try:
            prompt = self.prompt_templates[question_type].format(
                topic=topic,
                subject=subject,
                difficulty=difficulty
            )
            
            # Adicionar referência de estilo se fornecida
            if style_reference:
                prompt += f"\n\nReferência de estilo:\n{json.dumps(style_reference, indent=2, ensure_ascii=False)}"
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em criar questões educacionais no padrão ENEM."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Tentar extrair JSON da resposta
            try:
                question_data = json.loads(content)
            except json.JSONDecodeError:
                # Se não for JSON válido, tentar extrair
                question_data = self._extract_question_from_text(content, question_type)
            
            # Adicionar metadados
            question_data.update({
                "generated_at": datetime.now().isoformat(),
                "generator_model": self.model,
                "type": question_type,
                "subject": subject
            })
            
            return question_data
            
        except Exception as e:
            logger.error(f"Erro ao gerar questão: {str(e)}")
            return {"error": str(e)}
    
    async def generate_similar_question(
        self,
        reference_question: Dict[str, Any],
        topic_variation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera questão similar a uma de referência
        
        Args:
            reference_question: Questão de referência
            topic_variation: Variação do tema (opcional)
        
        Returns:
            Nova questão similar
        """
        original_topic = reference_question.get("tema", "tema geral")
        topic = topic_variation or f"variação de {original_topic}"
        
        return await self.generate_question(
            topic=topic,
            question_type=reference_question.get("type", "multiple_choice"),
            subject=reference_question.get("subject", "Geral"),
            difficulty=reference_question.get("dificuldade", "médio"),
            style_reference=reference_question
        )
    
    async def generate_question_set(
        self,
        topics: List[str],
        questions_per_topic: int = 3,
        question_types: List[str] = None,
        subjects: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Gera conjunto de questões sobre múltiplos temas
        
        Args:
            topics: Lista de temas
            questions_per_topic: Quantas questões por tema
            question_types: Tipos de questão desejados
            subjects: Áreas do conhecimento
        
        Returns:
            Lista de questões geradas
        """
        if not question_types:
            question_types = ["multiple_choice"]
        if not subjects:
            subjects = ["Geral"]
        
        questions = []
        
        for topic in topics:
            for i in range(questions_per_topic):
                question_type = random.choice(question_types)
                subject = random.choice(subjects)
                difficulty = random.choice(["fácil", "médio", "difícil"])
                
                question = await self.generate_question(
                    topic=topic,
                    question_type=question_type,
                    subject=subject,
                    difficulty=difficulty
                )
                
                if "error" not in question:
                    questions.append(question)
                
                # Pequeno delay para não sobrecarregar a API
                await asyncio.sleep(1)
        
        return questions
    
    def _extract_question_from_text(self, text: str, question_type: str) -> Dict[str, Any]:
        """
        Extrai dados da questão quando a resposta não é JSON válido
        
        Args:
            text: Texto da resposta
            question_type: Tipo da questão
        
        Returns:
            Dados da questão extraídos
        """
        # Implementação básica de extração
        # Em uma implementação real, usaria regex ou parsing mais sofisticado
        
        return {
            "enunciado": "Questão extraída do texto",
            "content": text,
            "extraction_method": "text_parsing",
            "type": question_type,
            "status": "needs_manual_review"
        }
    
    async def validate_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida se a questão segue padrões ENEM
        
        Args:
            question: Questão a ser validada
        
        Returns:
            Resultado da validação com sugestões
        """
        validation_prompt = f"""
Analise esta questão ENEM e forneça feedback:

{json.dumps(question, indent=2, ensure_ascii=False)}

Avalie:
1. Clareza do enunciado
2. Qualidade das alternativas
3. Adequação ao estilo ENEM
4. Nível de dificuldade apropriado
5. Contextualização adequada

Forneça nota de 0-10 e sugestões de melhoria.
"""
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um avaliador especialista em questões ENEM."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return {
                "validation_score": "pending_extraction",
                "feedback": response.choices[0].message.content,
                "validated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Erro na validação: {str(e)}"}
    
    def get_available_templates(self) -> List[str]:
        """Retorna lista de templates disponíveis"""
        return list(self.prompt_templates.keys())
    
    def add_custom_template(self, name: str, template: str):
        """Adiciona template customizado"""
        self.prompt_templates[name] = template

# Instância global
question_generator = EnemQuestionGenerator()
