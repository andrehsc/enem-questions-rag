#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM Questions API - FastAPI com Swagger e PostgreSQL
API completa para questões do ENEM com documentação automática
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import psycopg2
import psycopg2.extras
import os
from contextlib import contextmanager

# Importar documentação adicional
try:
    from swagger_docs import EXAMPLES, TAGS_METADATA, OPENAPI_EXTRA
except ImportError:
    EXAMPLES = {}
    TAGS_METADATA = []
    OPENAPI_EXTRA = {}

# Modelos Pydantic para documentação Swagger
class Alternative(BaseModel):
    id: int = Field(..., description="ID da alternativa")
    letter: str = Field(..., description="Letra da alternativa (A, B, C, D, E)")
    text: str = Field(..., description="Texto da alternativa")
    order: int = Field(..., description="Ordem da alternativa")

class AnswerKey(BaseModel):
    id: int = Field(..., description="ID do gabarito")
    correct_answer: str = Field(..., description="Resposta correta (A, B, C, D, E)")
    subject: str = Field(..., description="Matéria da questão")
    language_option: Optional[str] = Field(None, description="Opção de idioma")

class ExamMetadata(BaseModel):
    exam_year: int = Field(..., description="Ano do exame")
    exam_type: str = Field(..., description="Tipo do exame (ENEM)")
    application_type: str = Field(..., description="Tipo de aplicação")
    language: str = Field(..., description="Idioma da prova")

class Question(BaseModel):
    id: str = Field(..., description="ID único da questão (UUID)")
    exam_year: int = Field(..., description="Ano do exame")
    exam_type: str = Field(..., description="Tipo do exame")
    number: int = Field(..., description="Número da questão")
    statement: str = Field(..., description="Enunciado da questão")
    alternatives: List[Alternative] = Field(..., description="Lista de alternativas")
    answer_key: Optional[AnswerKey] = Field(None, description="Gabarito da questão")
    metadata: ExamMetadata = Field(..., description="Metadados do exame")

class QuestionSummary(BaseModel):
    id: str = Field(..., description="ID da questão (UUID)")
    exam_year: int = Field(..., description="Ano do exame")
    exam_type: str = Field(..., description="Tipo do exame")
    number: int = Field(..., description="Número da questão")
    subject: Optional[str] = Field(None, description="Matéria")
    correct_answer: Optional[str] = Field(None, description="Resposta correta")
    statement_preview: str = Field(..., description="Prévia do enunciado")

class PaginatedResponse(BaseModel):
    items: List[QuestionSummary] = Field(..., description="Lista de questões")
    total: int = Field(..., description="Total de questões encontradas")
    page: int = Field(..., description="Página atual")
    size: int = Field(..., description="Itens por página")
    pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Há próxima página")
    has_prev: bool = Field(..., description="Há página anterior")

class Stats(BaseModel):
    total_questions: int = Field(..., description="Total de questões")
    total_alternatives: int = Field(..., description="Total de alternativas")
    total_answer_keys: int = Field(..., description="Total de gabaritos")
    years_available: List[int] = Field(..., description="Anos disponíveis")
    exam_types: List[str] = Field(..., description="Tipos de exame")
    subjects: List[str] = Field(..., description="Matérias disponíveis")

# Configuração de banco de dados
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': int(os.getenv('DB_PORT', '5432')), 
    'database': os.getenv('DB_NAME', 'enem_rag'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres123')
}

@contextmanager
def get_db_connection():
    """Context manager para conexão com banco de dados"""
    conn = None
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.set_client_encoding('UTF8')
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro de banco de dados: {str(e)}")
    finally:
        if conn:
            conn.close()

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="ENEM Questions RAG API",
    description="""
    ## API completa para questões do ENEM
    
    Esta API fornece acesso completo aos dados processados do ENEM, incluindo:
    
    * **Questões completas** com enunciados, alternativas e gabaritos
    * **Metadados** dos exames (ano, tipo, aplicação)
    * **Busca textual** em português com suporte a acentos
    * **Filtros avançados** por ano, matéria, tipo de exame
    * **Paginação** para grandes volumes de dados
    * **Estatísticas** detalhadas sobre o conjunto de dados
    
    ### ��� Dados Disponíveis
    - **2.452 questões** processadas do ENEM
    - **12.260 alternativas** categorizadas
    - **4.308 gabaritos** com matérias
    - **Múltiplos anos** de provas
    
    ### ��� Tecnologias
    - FastAPI com documentação automática
    - PostgreSQL com busca textual otimizada
    - Docker para deployment
    - Swagger/OpenAPI para documentação interativa
    """,
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",
    contact={
        "name": "ENEM RAG API",
        "email": "contato@enemrag.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Página inicial com links para documentação"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ENEM Questions RAG API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
            .header { text-align: center; color: white; margin-bottom: 50px; }
            .header h1 { font-size: 3em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .header p { font-size: 1.2em; opacity: 0.9; margin: 20px 0; }
            .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
            .card { background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s ease; }
            .card:hover { transform: translateY(-5px); }
            .card h3 { color: #333; margin-top: 0; font-size: 1.5em; }
            .docs-link { display: inline-block; background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 10px 10px 0 0; transition: background 0.3s ease; }
            .docs-link:hover { background: #0056b3; }
            .swagger { background: #85ea2d; } .swagger:hover { background: #6bc91b; }
            .redoc { background: #f93; } .redoc:hover { background: #e67e22; }
            .stats { background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; }
            .stat-item { display: inline-block; margin: 10px 20px 10px 0; font-weight: 600; color: #495057; }
            .examples { margin-top: 20px; }
            .example { background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; font-family: monospace; }
            .example a { color: #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>��� ENEM Questions RAG API</h1>
                <p>API completa para questões do ENEM com documentação Swagger automática</p>
                <div style="margin-top: 30px;">
                    <a href="/docs" class="docs-link swagger">��� Swagger UI</a>
                    <a href="/redoc" class="docs-link redoc">��� ReDoc</a>
                    <a href="/openapi.json" class="docs-link">��� OpenAPI JSON</a>
                </div>
            </div>

            <div class="cards">
                <div class="card">
                    <h3>�� Questões e Filtros</h3>
                    <div class="stats">
                        <div class="stat-item">��� 2.452 questões</div>
                        <div class="stat-item">��� 12.260 alternativas</div>
                        <div class="stat-item">✅ 4.308 gabaritos</div>
                    </div>
                    <div class="examples">
                        <div class="example"><a href="/questions?page=1&size=5">/questions?page=1&size=5</a></div>
                        <div class="example"><a href="/questions?year=2023">/questions?year=2023</a></div>
                        <div class="example"><a href="/questions?subject=Matemática">/questions?subject=Matemática</a></div>
                    </div>
                </div>

                <div class="card">
                    <h3>��� Busca Textual</h3>
                    <p>Busca inteligente em português com suporte a acentos e termos complexos.</p>
                    <div class="examples">
                        <div class="example"><a href="/search?q=democracia">/search?q=democracia</a></div>
                        <div class="example"><a href="/search?q=função quadrática">/search?q=função quadrática</a></div>
                        <div class="example"><a href="/search?q=globalização">/search?q=globalização</a></div>
                    </div>
                </div>

                <div class="card">
                    <h3>��� Estatísticas e Dados</h3>
                    <p>Informações detalhadas sobre o conjunto de dados disponível.</p>
                    <div class="examples">
                        <div class="example"><a href="/stats">/stats</a> - Estatísticas gerais</div>
                        <div class="example"><a href="/years">/years</a> - Anos disponíveis</div>
                        <div class="example"><a href="/subjects">/subjects</a> - Matérias disponíveis</div>
                        <div class="example"><a href="/health">/health</a> - Status da API</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/health", summary="Health Check", description="Verifica a saúde da API e conexão com banco")
async def health_check():
    """Endpoint para verificar a saúde da API e conexão com banco de dados"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM questions")
                total_questions = cur.fetchone()[0]
                
        return {
            "status": "healthy",
            "database_connected": True,
            "total_questions": total_questions,
            "message": "ENEM Questions RAG API está funcionando"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e),
            "message": "Problemas de conectividade com banco de dados"
        }

@app.get("/stats", response_model=Stats, summary="Estatísticas gerais", description="Retorna estatísticas completas sobre o conjunto de dados")
async def get_stats():
    """
    Obtém estatísticas detalhadas sobre todas as questões disponíveis.
    
    Inclui contadores de questões, alternativas, gabaritos e listas de anos/matérias disponíveis.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Estatísticas básicas (consultas separadas para evitar problemas de JOIN)
                cur.execute("SELECT COUNT(*) as total_questions FROM questions")
                total_questions = cur.fetchone()['total_questions']
                
                cur.execute("SELECT COUNT(*) as total_alternatives FROM question_alternatives")
                total_alternatives = cur.fetchone()['total_alternatives']
                
                cur.execute("SELECT COUNT(*) as total_answer_keys FROM answer_keys")
                total_answer_keys = cur.fetchone()['total_answer_keys']
                # Anos disponíveis
                cur.execute("""
                    SELECT DISTINCT em.year 
                    FROM exam_metadata em
                    WHERE em.year IS NOT NULL
                    ORDER BY em.year DESC
                """)
                years = [row['year'] for row in cur.fetchall()]
                
                # Tipos de exame disponíveis  
                cur.execute("""
                    SELECT DISTINCT em.application_type 
                    FROM exam_metadata em
                    WHERE em.application_type IS NOT NULL
                    ORDER BY em.application_type
                """)
                exam_types = [row['application_type'] for row in cur.fetchall()]
                
                # Matérias disponíveis
                cur.execute("""
                    SELECT DISTINCT ak.subject 
                    FROM answer_keys ak 
                    WHERE ak.subject IS NOT NULL AND ak.subject != ''
                    ORDER BY ak.subject
                """)
                subjects = [row['subject'] for row in cur.fetchall()]
                
        return Stats(
            total_questions=int(total_questions or 0),
            total_alternatives=int(total_alternatives or 0),
            total_answer_keys=int(total_answer_keys or 0),
            years_available=years or [],
            exam_types=exam_types or [],
            subjects=subjects or []
        )
    except psycopg2.Error as db_error:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro de banco de dados: {str(db_error)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno do servidor: {str(e)}"
        )

@app.get("/questions", response_model=PaginatedResponse, summary="Listar questões", description="Lista questões com paginação e filtros avançados")
async def list_questions(
    page: int = Query(1, ge=1, description="Página atual (começa em 1)"),
    size: int = Query(20, ge=1, le=100, description="Itens por página (máximo 100)"),
    year: Optional[int] = Query(None, description="Filtrar por ano do exame"),
    subject: Optional[str] = Query(None, description="Filtrar por matéria"),
    exam_type: Optional[str] = Query(None, description="Filtrar por tipo de exame")
):
    """
    Lista questões com paginação e filtros opcionais.
    
    - **page**: Número da página (começa em 1)
    - **size**: Número de itens por página (1-100)
    - **year**: Filtrar por ano específico
    - **subject**: Filtrar por matéria específica
    - **exam_type**: Filtrar por tipo de exame
    
    Retorna lista paginada com resumo das questões incluindo prévia do enunciado.
    """
    try:
        offset = (page - 1) * size
        
        # Construir query com filtros
        where_conditions = []
        params = []
        
        if year:
            where_conditions.append("em.year = %s")
            params.append(year)
        if subject:
            where_conditions.append("ak.subject = %s")
            params.append(subject)
        if exam_type:
            where_conditions.append("em.application_type = %s")
            params.append(exam_type)
            
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Query para contar total
                count_query = f"""
                    SELECT COUNT(DISTINCT q.id)
                    FROM questions q
                    LEFT JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN answer_keys ak ON q.question_number = ak.question_number AND q.exam_metadata_id = ak.exam_metadata_id
                    {where_clause}
                """
                cur.execute(count_query, params)
                total = cur.fetchone()['count']
                
                # Query para buscar questões
                questions_query = f"""
                    SELECT DISTINCT
                        q.id,
                        em.year as exam_year,
                        em.application_type as exam_type,
                        q.question_number as number,
                        ak.subject,
                        ak.correct_answer,
                        LEFT(q.question_text, 150) || CASE WHEN LENGTH(q.question_text) > 150 THEN '...' ELSE '' END as statement_preview
                    FROM questions q
                    LEFT JOIN exam_metadata em ON q.exam_metadata_id = em.id
                    LEFT JOIN answer_keys ak ON q.question_number = ak.question_number AND q.exam_metadata_id = ak.exam_metadata_id
                    {where_clause}
                    ORDER BY q.id
                    LIMIT %s OFFSET %s
                """
                cur.execute(questions_query, params + [size, offset])
                questions = cur.fetchall()
                
        # Calcular informações de paginação
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1
        
        # Converter para formato esperado
        question_summaries = [
            QuestionSummary(
                id=q['id'],
                exam_year=q['exam_year'],
                exam_type=q['exam_type'] or 'ENEM',
                number=q['number'],
                subject=q['subject'],
                correct_answer=q['correct_answer'],
                statement_preview=q['statement_preview']
            ) for q in questions
        ]
        
        return PaginatedResponse(
            items=question_summaries,
            total=total,
            page=page,
            size=size,
            pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar questões: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
