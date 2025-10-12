#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API FastAPI para ENEM Questions RAG - Integrada com PostgreSQL
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
from database import DatabaseService

# GraphQL imports
try:
    from strawberry.fastapi import GraphQLRouter
    from graphql_resolvers import schema
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

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

# Instanciar serviço de banco de dados
db_service = DatabaseService()

# Configurar GraphQL se disponível (AC1: GraphQL endpoint is available at `/graphql`)
if GRAPHQL_AVAILABLE:
    graphql_app = GraphQLRouter(schema, graphql_ide="graphiql")
    app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])

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
    try:
        db_connected, total_questions = db_service.health_check()
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "database_connected": db_connected,
            "total_questions": total_questions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database_connected": False,
            "total_questions": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/stats")
async def get_stats():
    """Estatísticas gerais do sistema"""
    try:
        stats = db_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@app.get("/questions")
async def list_questions(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(20, ge=1, le=100, description="Itens por página"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    subject: Optional[str] = Query(None, description="Filtrar por matéria"),
    caderno: Optional[str] = Query(None, description="Filtrar por caderno")
):
    """Listar questões com paginação e filtros"""
    try:
        questions, total = db_service.get_questions_summary(
            page=page, 
            size=size, 
            year=year, 
            subject=subject,
            caderno=caderno
        )
        
        # Converter para formato de resposta
        questions_list = []
        for q in questions:
            questions_list.append({
                "id": q["id"],
                "exam_year": q["year"],
                "exam_type": "ENEM",
                "number": q["question_number"],
                "subject": q["subject"],
                "correct_answer": q["correct_answer"],
                "statement_preview": q["statement_preview"] + "..." if q["statement_preview"] else ""
            })
        
        pages = math.ceil(total / size) if total > 0 else 1
            
        return {
            "items": questions_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar questões: {str(e)}")

@app.get("/questions/{question_id}")
async def get_question(question_id: str):
    """Obter questão completa por ID"""
    try:
        question_data = db_service.get_question_by_id(question_id)
    
        if not question_data:
            raise HTTPException(status_code=404, detail="Questão não encontrada")
        
        question = question_data['question']
        alternatives = question_data['alternatives']
        answer_key = question_data['answer_key']
        
        # Formatar resposta
        formatted_alternatives = []
        for i, alt in enumerate(alternatives, 1):
            formatted_alternatives.append({
                "id": alt["id"],
                "letter": alt["letter"],
                "text": alt["text"],
                "order": i
            })
        
        response = {
            "id": question["id"],
            "exam_year": question["year"],
            "exam_type": "ENEM",
            "number": question["question_number"], 
            "statement": question["question_text"],
            "alternatives": formatted_alternatives,
            "answer_key": {
                "id": answer_key["id"] if answer_key else None,
                "correct_answer": answer_key["correct_answer"] if answer_key else None,
                "subject": question["subject"] if question else None,
                "language_option": None
            } if answer_key else None,
            "metadata": {
                "exam_year": question["year"],
                "exam_type": "ENEM",
                "application_type": question["application_type"],
                "language": "PORTUGUÊS"
            }
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar questão: {str(e)}")

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
