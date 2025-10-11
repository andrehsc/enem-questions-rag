#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API FastAPI para ENEM Questions RAG - Demo
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import math
import os

from models import (
    Question, QuestionSummary, PaginatedResponse, 
    StatsResponse, HealthResponse, ExamMetadata, 
    QuestionAlternative, AnswerKey
)

# Configuração da aplicação
app = FastAPI(
    title="ENEM Questions RAG API",
    description="API navegável para questões do ENEM com metadados, alternativas e gabaritos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados simulados para demonstração
sample_questions = [
    {
        "id": 1,
        "exam_year": 2023,
        "exam_type": "ENEM",
        "number": 1,
        "statement": "Em uma sociedade democrática, a participação política dos cidadãos é fundamental para o desenvolvimento social e econômico. Considerando essa premissa, qual das alternativas a seguir representa melhor o conceito de cidadania ativa?",
        "alternatives": [
            {"id": 1, "letter": "A", "text": "Apenas votar nas eleições presidenciais.", "order": 1},
            {"id": 2, "letter": "B", "text": "Participar ativamente de movimentos sociais e políticos.", "order": 2},
            {"id": 3, "letter": "C", "text": "Criticar o governo nas redes sociais.", "order": 3},
            {"id": 4, "letter": "D", "text": "Pagar impostos em dia.", "order": 4},
            {"id": 5, "letter": "E", "text": "Obedecer às leis sem questionamento.", "order": 5}
        ],
        "answer_key": {
            "id": 1,
            "correct_answer": "B",
            "subject": "Ciências Humanas",
            "language_option": None
        },
        "metadata": {
            "exam_year": 2023,
            "exam_type": "ENEM",
            "application_type": "PRIMEIRO DIA",
            "language": "PORTUGUES"
        }
    }
]

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial com links para documentação"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ENEM Questions RAG API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 4px 8px; border-radius: 3px; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            h1 { color: #333; }
            h2 { color: #555; }
            a { color: #61affe; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>��� ENEM Questions RAG API</h1>
            <p>API completa para acesso às questões do ENEM com metadados, alternativas e gabaritos.</p>
            
            <h2>��� Documentação</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a> - Interface interativa</li>
                <li><a href="/redoc">ReDoc</a> - Documentação detalhada</li>
            </ul>
            
            <h2>��� Endpoints Principais</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/health</strong>
                <p>Status da API e conexão com banco de dados</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/stats</strong>
                <p>Estatísticas completas da base de dados</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/questions</strong>
                <p>Lista paginada de questões com filtros por ano, matéria e caderno</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/questions/{question_id}</strong>
                <p>Questão completa com alternativas, gabarito e metadados</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/search</strong>
                <p>Busca textual nas questões com ranking de relevância</p>
            </div>
            
            <h2>��� Dados Disponíveis</h2>
            <ul>
                <li><strong>2.452 questões</strong> processadas</li>
                <li><strong>12.260 alternativas</strong> (5 por questão)</li>
                <li><strong>4.308 gabaritos</strong> carregados</li>
                <li><strong>Anos:</strong> 2020-2024</li>
                <li><strong>Matérias:</strong> Linguagens, Ciências Humanas, Ciências da Natureza, Matemática</li>
            </ul>
            
            <h2>��� Exemplos de Uso</h2>
            <ul>
                <li><a href="/questions?page=1&size=10&year=2024">Questões de 2024</a></li>
                <li><a href="/questions?subject=Linguagens">Questões de Linguagens</a></li>
                <li><a href="/search?q=fotossíntese&page=1&size=5">Buscar por "fotossíntese"</a></li>
                <li><a href="/stats">Ver estatísticas completas</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database_connected": True,
        "total_questions": len(sample_questions),
        "timestamp": "2024-10-11"
    }

@app.get("/stats")
async def get_stats():
    """Estatísticas gerais do sistema"""
    return {
        "total_questions": len(sample_questions),
        "total_alternatives": sum(len(q["alternatives"]) for q in sample_questions),
        "total_answer_keys": len([q for q in sample_questions if q["answer_key"]]),
        "years_available": [2023],
        "exam_types": ["ENEM"],
        "subjects": ["Ciências Humanas"]
    }

@app.get("/questions")
async def list_questions(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(20, ge=1, le=100, description="Itens por página"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    subject: Optional[str] = Query(None, description="Filtrar por matéria")
):
    """Listar questões com paginação e filtros"""
    filtered_questions = sample_questions
    
    # Aplicar filtros
    if year:
        filtered_questions = [q for q in filtered_questions if q["exam_year"] == year]
    if subject and "answer_key" in sample_questions[0]:
        filtered_questions = [q for q in filtered_questions if q["answer_key"]["subject"] == subject]
    
    total = len(filtered_questions)
    start = (page - 1) * size
    end = start + size
    page_questions = filtered_questions[start:end]
    
    # Converter para formato de resumo
    questions_list = []
    for q in page_questions:
        questions_list.append({
            "id": q["id"],
            "exam_year": q["exam_year"],
            "exam_type": q["exam_type"],
            "number": q["number"],
            "subject": q["answer_key"]["subject"] if q["answer_key"] else None,
            "correct_answer": q["answer_key"]["correct_answer"] if q["answer_key"] else None,
            "statement_preview": q["statement"][:100] + "..." if len(q["statement"]) > 100 else q["statement"]
        })
    
    pages = math.ceil(total / size) if total > 0 else 1
        
    return {
        "items": questions_list,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@app.get("/questions/{question_id}")
async def get_question(question_id: int):
    """Obter questão completa por ID"""
    # Procurar questão nos dados mockados
    question = next((q for q in sample_questions if q["id"] == question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    
    return question

@app.get("/search")
async def search_questions(
    q: str = Query(..., description="Texto para busca"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(20, ge=1, le=100, description="Itens por página")
):
    """Buscar questões por texto usando busca textual em português"""
    # Busca simples nos dados mockados
    filtered_questions = [
        question for question in sample_questions 
        if q.lower() in question["statement"].lower()
    ]
    
    total = len(filtered_questions)
    start = (page - 1) * size
    end = start + size
    page_questions = filtered_questions[start:end]
    
    pages = math.ceil(total / size) if total > 0 else 1
    
    return {
        "items": page_questions,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@app.get("/years")
async def get_available_years():
    """Obter anos disponíveis na base"""
    years = list(set(q["exam_year"] for q in sample_questions))
    return {"years": sorted(years)}

@app.get("/subjects")
async def get_available_subjects():
    """Obter matérias disponíveis na base"""
    subjects = list(set(q["answer_key"]["subject"] for q in sample_questions if q["answer_key"]))
    return {"subjects": sorted(subjects)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
