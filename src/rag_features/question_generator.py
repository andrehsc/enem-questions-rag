#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de questões estilo ENEM usando LLM

Contains:
- EnemQuestionGenerator: Legacy generator (deprecated, uses old OpenAI API)
- RAGQuestionGenerator: New RAG-based generator using pgvector context + GPT-4o (Story 4.2)
"""

import openai
from typing import List, Dict, Any, Optional
import asyncio
import json
import re
import random
import logging
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── RAG Question Generator (Story 4.2) ───────────────────────────────────────

SYSTEM_PROMPT = """Você é um especialista em elaboração de questões no padrão ENEM (Exame Nacional do Ensino Médio do Brasil).
Você recebe textos-base reais de questões ENEM como referência de estilo e contexto.
Sua tarefa é gerar questões INÉDITAS que sigam rigorosamente o formato ENEM.

Regras obrigatórias:
1. Cada questão deve ter um enunciado claro e contextualizado
2. Quando relevante ao tema, inclua um texto-base (trecho, gráfico descrito, situação-problema)
3. Exatamente 5 alternativas: A, B, C, D, E
4. Exatamente 1 alternativa correta
5. Alternativas incorretas devem ser plausíveis (distratores bem construídos)
6. Forneça explicação detalhada de por que a alternativa correta é a certa
7. Mantenha o nível de dificuldade solicitado

Responda EXCLUSIVAMENTE em JSON válido, sem markdown, sem backticks."""

USER_PROMPT_TEMPLATE = """Gere {count} questão(ões) no estilo ENEM sobre o assunto abaixo.

**Matéria:** {subject}
**Tópico:** {topic}
**Dificuldade:** {difficulty}

### Contexto de referência (textos-base reais do ENEM):
{context_chunks_text}

### Formato de resposta (JSON array):
[
  {{
    "stem": "Enunciado completo da questão com contextualização",
    "context_text": "Texto-base da questão (ou null se não aplicável)",
    "alternatives": {{
      "A": "Texto da alternativa A",
      "B": "Texto da alternativa B",
      "C": "Texto da alternativa C",
      "D": "Texto da alternativa D",
      "E": "Texto da alternativa E"
    }},
    "answer": "LETRA_CORRETA",
    "explanation": "Explicação detalhada de por que esta é a resposta correta"
  }}
]"""


class RAGQuestionGenerator:
    """Generates ENEM-style questions using RAG context from pgvector + GPT-4o."""

    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        pgvector_search=None,
        model: str = "gpt-4o",
    ) -> None:
        self.engine: Engine = create_engine(database_url)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.pgvector_search = pgvector_search

    async def _fetch_context_chunks(
        self, subject: str, topic: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetches context chunks from ENEM corpus via semantic search."""
        if self.pgvector_search is None:
            return []
        results = await self.pgvector_search.search_questions(
            query=f"{subject} {topic}",
            limit=limit,
            subject=subject,
        )
        return results

    def _build_generation_prompt(
        self, topic, subject, difficulty, count, style, context_chunks
    ) -> List[Dict[str, str]]:
        """Builds system + user messages with RAG context."""
        context_text = "\n\n---\n\n".join(
            [c.get("full_text", c.get("chunk_content", "")) for c in context_chunks]
        ) or "(Nenhum contexto encontrado no corpus)"

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                count=count,
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                context_chunks_text=context_text,
            )},
        ]

    async def generate_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str = "medium",
        count: int = 1,
        style: str = "enem",
    ) -> List[Dict[str, Any]]:
        """Generates new questions using RAG context + GPT-4o."""
        # 1. Fetch RAG context
        context_chunks = await self._fetch_context_chunks(subject, topic)
        source_context_ids = [
            str(c.get("chunk_id", c.get("question_id", "")))
            for c in context_chunks
        ]

        # 2. Build prompt
        messages = self._build_generation_prompt(
            topic=topic,
            subject=subject,
            difficulty=difficulty,
            count=count,
            style=style,
            context_chunks=context_chunks,
        )

        # 3. Call GPT-4o
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=3000 * count,
        )

        content = response.choices[0].message.content

        # 4. Parse response
        questions = self._parse_llm_response(content)

        # 5. Attach source_context_ids
        for q in questions:
            q["source_context_ids"] = source_context_ids

        # 6. Persist to generated_questions table
        ids = self._persist_generated(questions, subject, topic, difficulty)
        for q, qid in zip(questions, ids):
            q["id"] = str(qid)

        return questions[:count]

    def _parse_llm_response(self, content: str) -> List[Dict[str, Any]]:
        """Extracts JSON from GPT-4o response with robust fallback."""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = [parsed]
            return parsed
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError("Resposta do LLM não contém JSON válido")

    def _persist_generated(
        self, questions: List[Dict], subject: str, topic: str, difficulty: str
    ) -> List[str]:
        """Persists generated questions to the generated_questions table."""
        ids = []
        sql = text("""
            INSERT INTO enem_questions.generated_questions
                (subject, topic, difficulty, stem, context_text, alternatives, answer, explanation, source_context_ids, model_used)
            VALUES
                (:subject, :topic, :difficulty, :stem, :context_text, :alternatives::jsonb, :answer, :explanation, :source_context_ids, :model_used)
            RETURNING id
        """)
        with self.engine.begin() as conn:
            for q in questions:
                row = conn.execute(sql, {
                    "subject": subject,
                    "topic": topic,
                    "difficulty": difficulty,
                    "stem": q.get("stem", ""),
                    "context_text": q.get("context_text"),
                    "alternatives": json.dumps(q.get("alternatives", {})),
                    "answer": q.get("answer", "A"),
                    "explanation": q.get("explanation", ""),
                    "source_context_ids": q.get("source_context_ids", []),
                    "model_used": self.model,
                }).fetchone()
                ids.append(str(row[0]))
        return ids


# ── Legacy Generator (deprecated) ────────────────────────────────────────────

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
