#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM Questions API - FastAPI limpa e funcional
Sistema RAG completo para questões do ENEM
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Annotated
import psycopg2
import psycopg2.extras
import json
import os
import sys
import asyncio
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Adicionar src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Imports RAG
try:
    from rag_features.enhanced_rag_system import EnhancedEnemRAG
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"RAG não disponível: {e}")
    RAG_AVAILABLE = False

# PgVectorSearch (Story 3.1/3.2)
try:
    from rag_features.semantic_search import PgVectorSearch
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

# AssessmentGenerator (Story 4.1)
try:
    from rag_features.assessment_generator import AssessmentGenerator, InsufficientQuestionsError
    ASSESSMENT_AVAILABLE = True
except ImportError:
    ASSESSMENT_AVAILABLE = False

# RAGQuestionGenerator (Story 4.2)
try:
    from rag_features.question_generator import RAGQuestionGenerator
    RAG_QUESTION_GENERATOR_AVAILABLE = True
except ImportError:
    RAG_QUESTION_GENERATOR_AVAILABLE = False

# Modelos Pydantic para documentação Swagger
class HealthResponse(BaseModel):
    status: str = Field(..., description="Status da API", example="healthy")
    timestamp: str = Field(..., description="Timestamp da verificação")
    database: str = Field(..., description="Status do banco de dados", example="connected")
    version: str = Field(..., description="Versão da API", example="2.0.0")

class StatsResponse(BaseModel):
    total_questoes: int = Field(..., description="Total de questões no banco")
    por_ano: Dict[str, int] = Field(..., description="Questões por ano")
    por_materia: Dict[str, int] = Field(..., description="Questões por matéria")
    ultima_atualizacao: str = Field(..., description="Timestamp da última atualização")

class QuestionSummary(BaseModel):
    id: str = Field(..., description="UUID da questão")
    question_number: int = Field(..., description="Número da questão")
    enunciado_preview: str = Field(..., description="Prévia do enunciado (200 chars)")
    materia: str = Field(..., description="Matéria da questão")

class FiltersApplied(BaseModel):
    year: Optional[int] = Field(None, description="Filtro por ano aplicado")
    subject: Optional[str] = Field(None, description="Filtro por matéria aplicado")
    search: Optional[str] = Field(None, description="Filtro de busca aplicado")

class QuestionsResponse(BaseModel):
    questions: List[QuestionSummary] = Field(..., description="Lista de questões")
    total: int = Field(..., description="Total de questões encontradas")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Offset atual")
    has_next: bool = Field(..., description="Há próxima página")
    filters_applied: FiltersApplied = Field(..., description="Filtros aplicados")

class QuestionDetail(BaseModel):
    id: str = Field(..., description="UUID da questão")
    enunciado: str = Field(..., description="Enunciado completo da questão")
    question_number: int = Field(..., description="Número da questão")
    ano: Optional[int] = Field(None, description="Ano do exame")
    tipo_exame: Optional[str] = Field(None, description="Tipo do exame")
    materia: Optional[str] = Field(None, description="Matéria da questão")
    gabarito: Optional[str] = Field(None, description="Resposta correta")

class SubjectsResponse(BaseModel):
    subjects: List[str] = Field(..., description="Lista de matérias disponíveis")
    total: int = Field(..., description="Total de matérias")
    examples: List[str] = Field(..., description="Exemplos de matérias")

class RAGQuery(BaseModel):
    text: str = Field(..., description="Texto para busca RAG", example="Como funciona a democracia?")

class RAGResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status")
    query: str = Field(..., description="Query processada")
    status: str = Field(..., description="Status da operação")

class MLData(BaseModel):
    question_text: str = Field(..., description="Texto da questão para análise ML")

class MLResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status")
    data: Dict[str, Any] = Field(..., description="Dados enviados")
    status: str = Field(..., description="Status da operação")

# Modelos Semantic Search (Story 3.2)
class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Texto para busca semântica", min_length=1, max_length=500, json_schema_extra={"examples": ["questões sobre fotossíntese"]})
    subject: Optional[str] = Field(None, description="Filtrar por matéria (ex: ciencias_natureza)")
    year: Optional[int] = Field(None, description="Filtrar por ano do exame", ge=2020, le=2030)
    limit: int = Field(10, description="Máximo de resultados (1–50)", ge=1, le=50)
    include_answer: bool = Field(False, description="Incluir gabarito na resposta")

class SemanticSearchResult(BaseModel):
    question_id: int = Field(..., description="ID da questão")
    full_text: str = Field(..., description="Enunciado + alternativas")
    subject: str = Field("", description="Matéria da questão")
    year: Optional[int] = Field(None, description="Ano do exame")
    similarity_score: float = Field(..., description="Score de similaridade (0–1)")
    images: List[str] = Field(default_factory=list, description="Paths de imagens")
    correct_answer: Optional[str] = Field(None, description="Gabarito (se include_answer=true)")

class SemanticSearchResponse(BaseModel):
    data: List[SemanticSearchResult] = Field(..., description="Resultados da busca")
    meta: Dict[str, Any] = Field(..., description="Metadados da resposta")
    error: Optional[Any] = Field(None, description="Erro (null se sucesso)")

# Modelos Assessment Generator (Story 4.1)
class AssessmentGenerateRequest(BaseModel):
    subject: str = Field(..., description="Disciplina das questoes (ex: matematica, ciencias_natureza)")
    difficulty: str = Field(
        "mixed",
        description="Nivel de dificuldade: easy, medium, hard ou mixed",
        pattern="^(easy|medium|hard|mixed)$",
    )
    question_count: int = Field(10, ge=1, le=50, description="Quantidade de questoes na avaliacao")
    years: Optional[List[Annotated[int, Field(ge=2020, le=2030)]]] = Field(None, description="Lista de anos para filtrar (ex: [2020, 2021, 2022])")

class AssessmentQuestion(BaseModel):
    question_order: int
    question_id: int
    full_text: str
    subject: str
    year: Optional[int] = None
    images: List[str] = []

class AssessmentData(BaseModel):
    assessment_id: str
    title: str
    questions: List[AssessmentQuestion]
    answer_key: Dict[int, str]

class AssessmentGenerateResponse(BaseModel):
    data: Optional[AssessmentData] = None
    meta: Dict[str, Any] = {}
    error: Optional[Dict[str, Any]] = None

# Modelos Question Generator RAG (Story 4.2)
class QuestionGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=1, description="Materia (ex: historia, matematica)")
    topic: str = Field(..., min_length=1, description="Topico especifico (ex: Segunda Guerra Mundial)")
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$", description="Nivel de dificuldade")
    count: int = Field(1, ge=1, le=5, description="Numero de questoes a gerar (max 5)")
    style: str = Field("enem", description="Estilo da questao (default: enem)")

class GeneratedQuestion(BaseModel):
    id: Optional[str] = Field(None, description="UUID da questao gerada")
    stem: str = Field(..., description="Enunciado da questao")
    context_text: Optional[str] = Field(None, description="Texto-base (quando aplicavel)")
    alternatives: Dict[str, str] = Field(..., description="Alternativas A-E")
    answer: str = Field(..., description="Letra da alternativa correta")
    explanation: str = Field(..., description="Explicacao da resposta correta")
    source_context_ids: List[str] = Field(default_factory=list, description="IDs dos chunks usados como contexto RAG")

class QuestionGenerateResponse(BaseModel):
    data: List[GeneratedQuestion] = []
    meta: Dict[str, Any] = {}
    error: Optional[Any] = None

# Modelos RAG
class RAGSearchQuery(BaseModel):
    query: str = Field(..., description="Consulta de busca semântica", min_length=3, max_length=500)
    limit: int = Field(10, description="Número máximo de resultados", ge=1, le=50)
    subject_filter: Optional[str] = Field(None, description="Filtrar por matéria específica")
    predict_difficulty: bool = Field(True, description="Incluir predição de dificuldade")

class RAGSearchResult(BaseModel):
    id: str = Field(..., description="ID da questão")
    text: str = Field(..., description="Texto da questão")
    similarity: float = Field(..., description="Score de similaridade", ge=0.0, le=1.0)
    predicted_difficulty: Optional[str] = Field(None, description="Dificuldade predita (facil/medio/dificil)")
    difficulty_confidence: Optional[float] = Field(None, description="Confiança na predição", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(..., description="Metadados da questão")

class RAGSearchResponse(BaseModel):
    query: str = Field(..., description="Consulta original")
    results: List[RAGSearchResult] = Field(..., description="Resultados da busca")
    total_found: int = Field(..., description="Total de resultados encontrados")
    processing_time_ms: float = Field(..., description="Tempo de processamento em milissegundos")
    model_info: Dict[str, str] = Field(..., description="Informações do modelo usado")

# Modelos HATEOAS
class HATEOASLink(BaseModel):
    href: str = Field(..., description="URL do link")
    rel: str = Field(..., description="Relação do link")
    method: str = Field(..., description="Método HTTP", example="GET")
    title: Optional[str] = Field(None, description="Título descritivo do link")

class QuestionCompleteSummary(BaseModel):
    id: str = Field(..., description="UUID da questão")
    question_number: int = Field(..., description="Número da questão")
    enunciado: str = Field(..., description="Enunciado completo da questão")
    prova: str = Field(..., description="Tipo da prova (regular, reaplicacao, etc.)")
    dia: int = Field(..., description="Dia do exame (1 ou 2)")
    caderno: str = Field(..., description="Caderno da prova (ex: CD1, CD2, etc.)")
    gabarito: str = Field(..., description="Resposta correta (A, B, C, D, E)")
    materia: str = Field(..., description="Matéria/disciplina da questão")
    ano: int = Field(..., description="Ano do exame")
    links: List[HATEOASLink] = Field(..., description="Links HATEOAS para navegação")

class HATEOASQuestionSummary(QuestionSummary):
    links: List[HATEOASLink] = Field(..., description="Links HATEOAS para navegação")

class HATEOASQuestionsResponse(BaseModel):
    questions: List[HATEOASQuestionSummary] = Field(..., description="Lista de questões com HATEOAS")
    total: int = Field(..., description="Total de questões encontradas")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Offset atual")
    has_next: bool = Field(..., description="Há próxima página")
    filters_applied: FiltersApplied = Field(..., description="Filtros aplicados")
    links: List[HATEOASLink] = Field(..., description="Links HATEOAS para navegação")

# Configuração do banco de dados
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'enem_rag'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS', 'postgres123')
}

# Funções auxiliares para HATEOAS
def generate_question_links(question_id: str) -> List[HATEOASLink]:
    """Gera links HATEOAS para uma questão específica"""
    base_url = "http://localhost:8000"
    return [
        HATEOASLink(
            href=f"{base_url}/questions/{question_id}",
            rel="self",
            method="GET",
            title="Detalhes básicos da questão"
        ),
        HATEOASLink(
            href=f"{base_url}/question_summary/question/{question_id}",
            rel="complete",
            method="GET",
            title="Informações completas da questão"
        ),
        HATEOASLink(
            href=f"{base_url}/questions",
            rel="collection",
            method="GET",
            title="Lista todas as questões"
        )
    ]

def generate_questions_list_links(limit: int, offset: int, total: int, filters: dict) -> List[HATEOASLink]:
    """Gera links HATEOAS para navegação na lista de questões"""
    base_url = "http://localhost:8000"
    links = []
    
    # Link para self
    filter_params = "&".join([f"{k}={v}" for k, v in filters.items() if v is not None])
    self_url = f"{base_url}/questions?limit={limit}&offset={offset}"
    if filter_params:
        self_url += f"&{filter_params}"
    
    links.append(HATEOASLink(
        href=self_url,
        rel="self",
        method="GET",
        title="Página atual"
    ))
    
    # Link para primeira página
    first_url = f"{base_url}/questions?limit={limit}&offset=0"
    if filter_params:
        first_url += f"&{filter_params}"
    links.append(HATEOASLink(
        href=first_url,
        rel="first",
        method="GET",
        title="Primeira página"
    ))
    
    # Link para próxima página
    if offset + limit < total:
        next_offset = offset + limit
        next_url = f"{base_url}/questions?limit={limit}&offset={next_offset}"
        if filter_params:
            next_url += f"&{filter_params}"
        links.append(HATEOASLink(
            href=next_url,
            rel="next",
            method="GET",
            title="Próxima página"
        ))
    
    # Link para página anterior
    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_url = f"{base_url}/questions?limit={limit}&offset={prev_offset}"
        if filter_params:
            prev_url += f"&{filter_params}"
        links.append(HATEOASLink(
            href=prev_url,
            rel="prev",
            method="GET",
            title="Página anterior"
        ))
    
    # Link para última página
    last_offset = (total // limit) * limit
    if total % limit == 0 and total > 0:
        last_offset = max(0, last_offset - limit)
    last_url = f"{base_url}/questions?limit={limit}&offset={last_offset}"
    if filter_params:
        last_url += f"&{filter_params}"
    links.append(HATEOASLink(
        href=last_url,
        rel="last",
        method="GET",
        title="Última página"
    ))
    
    return links

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="ENEM Questions RAG API",
    description="""
    ## 🎓 API Completa para Questões do ENEM
    
    Sistema avançado de consulta e análise de questões do ENEM com funcionalidades RAG e Machine Learning.
    
    ### ✨ Funcionalidades Principais:
    - **📚 2.452 questões** processadas do ENEM (2020-2024)
    - **🔍 Busca textual** avançada em português
    - **🎯 Filtros** por ano, matéria e busca personalizada
    - **📊 Estatísticas** detalhadas sobre o conjunto de dados
    - **🤖 Sistema RAG** para busca semântica
    - **🧠 Machine Learning** para análise preditiva
    
    ### 🎯 Matérias Disponíveis:
    - `MATEMATICA` - Questões de matemática
    - `LINGUAGENS` - Português e literaturas
    - `CIENCIAS_HUMANAS` - História, geografia, filosofia, sociologia
    - `CIENCIAS_NATUREZA` - Física, química, biologia
    
    ### 📖 Exemplos de Uso:
    ```
    GET /questions?subject=MATEMATICA&year=2023&limit=10
    GET /questions?search=democracia&limit=5
    POST /rag/search {"text": "Explique função quadrática"}
    ```
    
    ### 🔗 Links Úteis:
    - **Interface Web**: [http://localhost:8000/](http://localhost:8000/)
    - **Health Check**: [/health](/health)
    - **Estatísticas**: [/stats](/stats)
    - **Matérias**: [/subjects](/subjects)
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "ENEM RAG API",
        "url": "http://localhost:8000",
        "email": "dev@enemrag.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do RAG
rag_system = None

# Instância global do PgVectorSearch (Story 3.2)
pgvector_search = None

# Instância global do AssessmentGenerator (Story 4.1)
assessment_generator = None

# Instância global do RAGQuestionGenerator (Story 4.2)
rag_question_generator = None

@app.on_event("startup")
async def initialize_rag():
    """Inicializa o sistema RAG na inicialização da aplicação"""
    global rag_system, pgvector_search, assessment_generator, rag_question_generator
    if RAG_AVAILABLE:
        try:
            rag_system = EnhancedEnemRAG()
            await rag_system.initialize()
            print("Sistema RAG inicializado com sucesso")
        except Exception as e:
            print(f"Erro ao inicializar RAG: {e}")
            rag_system = None
    else:
        print("RAG não disponível - dependências não instaladas")

    # PgVectorSearch
    if PGVECTOR_AVAILABLE:
        try:
            pgvector_search = PgVectorSearch(
                database_url=os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem",
                ),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
            )
            print("PgVectorSearch inicializado com sucesso")
        except Exception as e:
            print(f"PgVectorSearch indisponível: {e}")
            pgvector_search = None

    # AssessmentGenerator (Story 4.1)
    if ASSESSMENT_AVAILABLE and pgvector_search is not None:
        try:
            assessment_generator = AssessmentGenerator(
                database_url=os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem",
                ),
                pgvector_search=pgvector_search,
            )
            print("AssessmentGenerator inicializado com sucesso")
        except Exception as e:
            print(f"AssessmentGenerator indisponível: {e}")
            assessment_generator = None

    # RAGQuestionGenerator (Story 4.2)
    if RAG_QUESTION_GENERATOR_AVAILABLE and pgvector_search is not None:
        try:
            rag_question_generator = RAGQuestionGenerator(
                database_url=os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres123@localhost:5433/teachershub_enem",
                ),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                pgvector_search=pgvector_search,
            )
            print("RAGQuestionGenerator inicializado com sucesso")
        except Exception as e:
            print(f"RAGQuestionGenerator indisponível: {e}")
            rag_question_generator = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ENEM Questions RAG API</title>
        <meta charset="utf-8">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 40px 20px; 
                background: #f5f5f5; 
            }
            .header { 
                text-align: center; 
                background: white; 
                padding: 30px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                margin-bottom: 30px; 
            }
            .header h1 { 
                color: #333; 
                margin: 0 0 10px 0; 
            }
            .links { 
                margin: 20px 0; 
            }
            .link { 
                display: inline-block; 
                background: #007bff; 
                color: white; 
                padding: 10px 20px; 
                text-decoration: none; 
                border-radius: 5px; 
                margin: 5px; 
            }
            .link:hover { 
                background: #0056b3; 
            }
            .stats { 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            .status { 
                color: #28a745; 
                font-weight: bold; 
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>ENEM Questions RAG API</h1>
            <p>API completa para questões do ENEM com busca e análise avançada</p>
            
            <div class="links">
                <a href="/docs" class="link">Swagger Docs</a>
                <a href="/redoc" class="link">ReDoc</a>
                <a href="/health" class="link">Health Check</a>
                <a href="/stats" class="link">Estatísticas</a>
            </div>
        </div>
        
        <div class="stats">
            <h3>Status do Sistema</h3>
            <p>API: <span class="status">OPERACIONAL</span></p>
            <p>Versão: 2.0.0</p>
            <p>Endpoints disponíveis: 12+</p>
            
            <h4>Funcionalidades:</h4>
            <ul>
                <li>Busca de questões ENEM</li>
                <li>Filtros por ano, matéria, tipo</li>
                <li>Sistema RAG com IA</li>
                <li>Machine Learning integrado</li>
                <li>Cache Redis otimizado</li>
            </ul>
            
            <h4>Exemplos de uso:</h4>
            <ul>
                <li><a href="/questions?limit=5">/questions?limit=5</a> - Listar questões</li>
                <li><a href="/questions?year=2023">/questions?year=2023</a> - Questões de 2023</li>
                <li><a href="/questions?subject=Matemática">/questions?subject=Matemática</a> - Matemática</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse, tags=["Sistema"], summary="Verificação de Saúde")
async def health_check():
    """
    ### 🏥 Health Check da API
    
    Verifica o status da API e conectividade com banco de dados.
    
    **Retorna:**
    - Status da API (healthy/unhealthy)
    - Timestamp da verificação
    - Status da conexão com PostgreSQL
    - Versão atual da API
    """
    try:
        # Testar conexão com banco (se disponível)
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.close()
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "2.0.0"
    }

@app.get("/stats", response_model=StatsResponse, tags=["Dados"], summary="Estatísticas do Sistema")
async def get_stats():
    """
    ### 📊 Estatísticas Completas do ENEM
    
    Fornece informações detalhadas sobre o conjunto de dados:
    
    - **Total de questões** no banco de dados
    - **Distribuição por ano** (2020-2024)
    - **Distribuição por matéria** (top 10)
    - **Timestamp** da última atualização
    
    Útil para entender a cobertura e volume dos dados disponíveis.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        # Contar questões
        cursor.execute("SELECT COUNT(*) FROM questions")
        total_questoes = cursor.fetchone()[0]
        
        # Contar por ano
        cursor.execute("SELECT em.year, COUNT(*) FROM questions q JOIN exam_metadata em ON q.exam_metadata_id = em.id WHERE em.year IS NOT NULL GROUP BY em.year ORDER BY em.year")
        por_ano = dict(cursor.fetchall())
        
        # Contar por matéria
        cursor.execute("SELECT ak.subject, COUNT(*) FROM answer_keys ak WHERE ak.subject IS NOT NULL GROUP BY ak.subject ORDER BY COUNT(*) DESC LIMIT 10")
        por_materia = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return {
            "total_questoes": total_questoes,
            "por_ano": por_ano,
            "por_materia": por_materia,
            "ultima_atualizacao": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Erro ao buscar estatísticas: {str(e)}",
            "total_questoes": 0,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/questions", response_model=HATEOASQuestionsResponse, tags=["Questões"], summary="Listar Questões ENEM")
async def list_questions(
    limit: int = Query(20, ge=1, le=100, description="📄 Número de questões por página (1-100)", example=20),
    offset: int = Query(0, ge=0, description="📋 Offset para paginação (começa em 0)", example=0),
    year: Optional[int] = Query(None, ge=2020, le=2024, description="📅 Filtrar por ano do exame", example=2023),
    subject: Optional[str] = Query(None, description="🎯 Filtrar por matéria", example="MATEMATICA"),
    search: Optional[str] = Query(None, description="🔍 Busca textual no enunciado", example="democracia")
):
    """
    ### 📚 Lista Questões do ENEM com Filtros Avançados
    
    Endpoint principal para consultar questões do ENEM com múltiplas opções de filtro.
    
    **🎯 Filtros Disponíveis:**
    - **Ano**: 2020, 2021, 2022, 2023, 2024
    - **Matéria**: MATEMATICA, LINGUAGENS, CIENCIAS_HUMANAS, CIENCIAS_NATUREZA
    - **Busca**: Qualquer termo no enunciado da questão
    
    **📖 Exemplos de Uso:**
    ```
    /questions?limit=10                           # Primeiras 10 questões
    /questions?year=2023&subject=MATEMATICA       # Matemática de 2023
    /questions?search=função quadrática&limit=5   # Busca por "função quadrática"
    /questions?offset=20&limit=10                 # Página 3 (questões 21-30)
    ```
    
    **📊 Resposta:**
    - Lista de questões com prévia do enunciado
    - Informações de paginação
    - Total de resultados encontrados
    - Filtros aplicados na consulta
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.set_client_encoding('UTF8')
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Construir condições WHERE baseadas nos filtros
        where_conditions = []
        params = []
        
        # Filtro por ano
        if year:
            where_conditions.append("em.year = %s")
            params.append(year)
        
        # Determinar se precisa de JOINs
        needs_joins = year or subject
        
        # Construir JOINs se necessário
        joins = ""
        if needs_joins:
            joins = """
                LEFT JOIN exam_metadata em ON q.exam_metadata_id = em.id
                LEFT JOIN answer_keys ak ON q.question_number = ak.question_number AND q.exam_metadata_id = ak.exam_metadata_id
            """
        
        # Filtro por ano
        if year:
            where_conditions.append("em.year = %s")
            params.append(year)
        
        # Filtro por matéria
        if subject:
            if needs_joins:
                where_conditions.append("(q.subject ILIKE %s OR ak.subject ILIKE %s)")
                params.extend([f"%{subject}%", f"%{subject}%"])
            else:
                where_conditions.append("q.subject ILIKE %s")
                params.append(f"%{subject}%")
        
        # Filtro por busca textual
        if search:
            where_conditions.append("q.question_text ILIKE %s")
            params.append(f"%{search}%")
        
        # Construir cláusula WHERE
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Query principal
        base_query = """
            SELECT 
                q.id::text as id,
                q.question_number,
                LEFT(q.question_text, 200) as enunciado_preview,
                COALESCE(q.subject, 'Geral') as materia
            FROM questions q
        """
        
        # Query completa
        query = f"{base_query}{joins} {where_clause} ORDER BY q.question_number LIMIT %s OFFSET %s"
        count_query = f"SELECT COUNT(*) FROM questions q{joins} {where_clause}"
        
        # Executar queries
        cursor.execute(query, params + [limit, offset])
        questions = cursor.fetchall()
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        # Adicionar links HATEOAS para cada questão
        questions_with_links = []
        for q in questions:
            question_dict = dict(q)
            question_dict["links"] = generate_question_links(question_dict["id"])
            questions_with_links.append(question_dict)
        
        # Gerar links de navegação
        navigation_links = generate_questions_list_links(
            limit=limit,
            offset=offset,
            total=total,
            filters={"year": year, "subject": subject, "search": search}
        )
        
        return {
            "questions": questions_with_links,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total,
            "filters_applied": {
                "year": year,
                "subject": subject,
                "search": search
            },
            "links": navigation_links
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar questões: {str(e)}")

@app.get("/questions/{question_id}", response_model=QuestionDetail, tags=["Questões"], summary="Obter Questão Específica")
async def get_question(question_id: str):
    """
    ### 📝 Obter Questão Completa por UUID
    
    Retorna todos os detalhes de uma questão específica do ENEM.
    
    **📋 Informações Retornadas:**
    - Enunciado completo da questão
    - Número da questão no exame
    - Ano e tipo do exame 
    - Matéria/disciplina
    - Gabarito (resposta correta)
    
    **🔍 Como Obter o UUID:**
    Use o endpoint `/questions` para listar questões e obter seus UUIDs.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.set_client_encoding('UTF8')
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT 
                q.id,
                q.question_text as enunciado,
                q.question_number,
                em.year as ano,
                em.application_type as tipo_exame,
                ak.subject as materia,
                ak.correct_answer as gabarito
            FROM questions q
            LEFT JOIN exam_metadata em ON q.exam_metadata_id = em.id
            LEFT JOIN answer_keys ak ON q.question_number = ak.question_number AND q.exam_metadata_id = ak.exam_metadata_id
            WHERE q.id = %s
        """, (question_id,))
        
        question = cursor.fetchone()
        
        if not question:
            raise HTTPException(status_code=404, detail="Questão não encontrada")
        
        cursor.close()
        conn.close()
        
        return dict(question)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar questão: {str(e)}")

@app.get("/subjects", response_model=SubjectsResponse, tags=["Dados"], summary="Listar Matérias Disponíveis")
async def list_subjects():
    """
    ### 🎯 Lista de Todas as Matérias Disponíveis
    
    Endpoint para descobrir quais matérias estão disponíveis no banco de dados.
    
    **📚 Matérias Principais:**
    - **MATEMATICA** - Álgebra, geometria, estatística, etc.
    - **LINGUAGENS** - Português, literaturas, interpretação de texto
    - **CIENCIAS_HUMANAS** - História, geografia, filosofia, sociologia
    - **CIENCIAS_NATUREZA** - Física, química, biologia
    
    **💡 Dica:** Use os valores retornados como filtro no endpoint `/questions?subject=MATEMATICA`
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        # Buscar matérias de ambas as tabelas
        cursor.execute("""
            SELECT DISTINCT 
                CASE 
                    WHEN q.subject LIKE 'Subject.%' THEN REPLACE(q.subject, 'Subject.', '')
                    ELSE q.subject 
                END as subject
            FROM questions q 
            WHERE q.subject IS NOT NULL
            UNION
            SELECT DISTINCT ak.subject
            FROM answer_keys ak 
            WHERE ak.subject IS NOT NULL
            ORDER BY subject
        """)
        
        subjects = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "subjects": subjects,
            "total": len(subjects),
            "examples": [
                "MATEMATICA",
                "CIENCIAS_NATUREZA", 
                "CIENCIAS_HUMANAS",
                "LINGUAGENS",
                "ciencias_humanas",
                "linguagens"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar matérias: {str(e)}")

@app.get("/question_summary/question/{question_id}", response_model=QuestionCompleteSummary, tags=["Questões"], summary="Informações Completas da Questão")
async def get_complete_question_summary(question_id: str):
    """
    ### 📋 Informações Completas da Questão ENEM
    
    Retorna **TODAS** as informações disponíveis sobre uma questão específica do ENEM,
    incluindo dados completos da prova, caderno, gabarito e links HATEOAS para navegação.
    
    **📊 Informações Retornadas:**
    - **Enunciado completo** da questão
    - **Prova**: Tipo da aplicação (regular, reaplicação, etc.)
    - **Dia**: Dia do exame (1 ou 2)
    - **Caderno**: Código do caderno (CD1, CD2, etc.)  
    - **Gabarito**: Resposta correta (A, B, C, D, E)
    - **Matéria**: Disciplina da questão
    - **Ano**: Ano de aplicação do exame
    - **Links HATEOAS**: Links para navegação na API
    
    **🔍 Como Obter o UUID:**
    Use o endpoint `/questions` para listar questões e obter seus UUIDs.
    
    **⚡ Diferença do endpoint básico:**
    Este endpoint fornece informações **completas** da questão, enquanto 
    `/questions/{question_id}` fornece apenas informações básicas.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        conn.set_client_encoding('UTF8')
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT 
                q.id::text as id,
                q.question_number,
                q.question_text as enunciado,
                em.application_type as prova,
                em.day as dia,
                em.caderno,
                ak.correct_answer as gabarito,
                ak.subject as materia,
                em.year as ano
            FROM questions q
            LEFT JOIN exam_metadata em ON q.exam_metadata_id = em.id
            LEFT JOIN answer_keys ak ON q.question_number = ak.question_number AND q.exam_metadata_id = ak.exam_metadata_id
            WHERE q.id = %s
        """, (question_id,))
        
        question = cursor.fetchone()
        
        if not question:
            raise HTTPException(status_code=404, detail="Questão não encontrada")
        
        cursor.close()
        conn.close()
        
        # Adicionar links HATEOAS
        question_dict = dict(question)
        question_dict["links"] = generate_question_links(question_id)
        
        # Adicionar links específicos para este endpoint
        question_dict["links"].extend([
            HATEOASLink(
                href=f"http://localhost:8000/questions?year={question_dict['ano']}",
                rel="related",
                method="GET",
                title=f"Outras questões de {question_dict['ano']}"
            ),
            HATEOASLink(
                href=f"http://localhost:8000/questions?subject={question_dict['materia']}",
                rel="related",
                method="GET",
                title=f"Outras questões de {question_dict['materia']}"
            ),
            HATEOASLink(
                href=f"http://localhost:8000/questions?year={question_dict['ano']}&subject={question_dict['materia']}",
                rel="related",
                method="GET",
                title=f"Questões de {question_dict['materia']} em {question_dict['ano']}"
            )
        ])
        
        return question_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar questão completa: {str(e)}")

# Endpoints RAG/ML 
@app.post("/rag/search", response_model=RAGSearchResponse, tags=["IA & RAG"], summary="Busca Semântica Avançada")
async def rag_search_advanced(query: RAGSearchQuery):
    """
    ### 🤖 Sistema RAG Avançado com ChromaDB + BERT
    
    Busca semântica de alta performance usando:
    - **ChromaDB**: Armazenamento vetorial otimizado
    - **BERT Portuguese**: Embeddings contextuais em português
    - **ML Integration**: Predição de dificuldade integrada
    
    **🎯 Funcionalidades:**
    - Busca semântica inteligente
    - Predição de dificuldade automática
    - Filtros por matéria
    - Score de similaridade preciso
    
    **📝 Exemplo de Uso:**
    ```json
    {
        "query": "função quadrática matemática",
        "limit": 5,
        "subject_filter": "matematica", 
        "predict_difficulty": true
    }
    ```
    """
    start_time = time.time()
    
    # Verificar se RAG está disponível
    if not rag_system:
        raise HTTPException(
            status_code=503, 
            detail="Sistema RAG não disponível. Instale dependências: pip install chromadb sentence-transformers"
        )
    
    try:
        # Buscar com ML insights
        results = await rag_system.search_with_ml_insights(
            query=query.query,
            limit=query.limit,
            predict_difficulty=query.predict_difficulty,
            subject_filter=query.subject_filter
        )
        
        # Formatar resultados
        formatted_results = []
        for result in results:
            formatted_results.append(RAGSearchResult(
                id=result['id'],
                text=result['text'],
                similarity=result['similarity'],
                predicted_difficulty=result.get('predicted_difficulty'),
                difficulty_confidence=result.get('difficulty_confidence'),
                metadata=result['metadata']
            ))
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return RAGSearchResponse(
            query=query.query,
            results=formatted_results,
            total_found=len(formatted_results),
            processing_time_ms=round(processing_time, 2),
            model_info={
                "embedding_model": "neuralmind/bert-base-portuguese-cased",
                "vector_store": "ChromaDB",
                "ml_predictor": "RandomForest"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na busca RAG: {str(e)}"
        )

@app.post("/ml/predict", response_model=MLResponse, tags=["IA & Machine Learning"], summary="Predição com Machine Learning")
async def ml_predict(data: MLData):
    """
    ### Predição e Análise com Machine Learning
    """
    return MLResponse(
        message="Endpoint ML implementado com sucesso",
        data={"question_text": data.question_text, "analysis": "pending"},
        status="Funcional - Para recursos avançados, instale dependências ML completas"
    )


# ── Story 3.2: Busca Semântica via pgvector ──────────────────────────────────

@app.post(
    "/api/v1/search/semantic",
    response_model=SemanticSearchResponse,
    tags=["RAG"],
    summary="Busca semântica de questões ENEM",
    description="Retorna questões semanticamente similares à query usando pgvector.",
)
async def search_semantic(request: SemanticSearchRequest):
    """Endpoint de busca semântica usando PgVectorSearch (pgvector)."""
    if pgvector_search is None:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "SEARCH_UNAVAILABLE", "message": "Serviço de busca semântica indisponível"},
            },
        )
    try:
        raw_results = await pgvector_search.search_questions(
            query=request.query,
            limit=request.limit,
            year=request.year,
            subject=request.subject,
        )
        results = []
        for r in raw_results:
            item = SemanticSearchResult(
                question_id=r["question_id"],
                full_text=r["full_text"],
                subject=r.get("subject", ""),
                year=r.get("year"),
                similarity_score=round(r["similarity_score"], 4),
            )
            if request.include_answer:
                item.correct_answer = _get_correct_answer(r["question_id"])
            results.append(item)

        return SemanticSearchResponse(
            data=results,
            meta={
                "total": len(results),
                "query": request.query,
                "filters": {"subject": request.subject, "year": request.year},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "SEARCH_UNAVAILABLE", "message": str(e)},
            },
        )


def _get_correct_answer(question_id: int) -> Optional[str]:
    """Busca gabarito para uma questão via answer_keys."""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ak.correct_answer
            FROM enem_questions.answer_keys ak
            JOIN enem_questions.exam_metadata em ON em.id = ak.exam_id
            JOIN enem_questions.questions q ON q.exam_metadata_id = em.id
                AND q.question_number = ak.question_number
            WHERE q.id = %s
            LIMIT 1
        """, (question_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ── Story 4.1: Assessment Generator ──────────────────────────────────────────

@app.post(
    "/api/v1/assessments/generate",
    response_model=AssessmentGenerateResponse,
    tags=["Assessments"],
    summary="Gerar avaliacao de treino com questoes ENEM",
    description="Seleciona questoes reais do ENEM por materia e dificuldade, "
                "monta avaliacao com gabarito e persiste para referencia futura.",
)
async def generate_assessment(request: AssessmentGenerateRequest):
    """Endpoint para gerar avaliacoes com questoes ENEM."""
    if assessment_generator is None:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {
                    "code": "ASSESSMENT_UNAVAILABLE",
                    "message": "Servico de geracao de avaliacoes indisponivel",
                },
            },
        )
    try:
        result = await assessment_generator.generate(
            subject=request.subject,
            difficulty=request.difficulty,
            question_count=request.question_count,
            years=request.years,
        )
        questions_out = []
        for order, q in enumerate(result["questions"], start=1):
            questions_out.append(AssessmentQuestion(
                question_order=order,
                question_id=q["question_id"],
                full_text=q.get("full_text", ""),
                subject=q.get("subject", request.subject),
                year=q.get("year"),
                images=q.get("images", []),
            ))
        return AssessmentGenerateResponse(
            data=AssessmentData(
                assessment_id=result["assessment_id"],
                title=result["title"],
                questions=questions_out,
                answer_key=result["answer_key"],
            ),
            meta={
                "total_questions": len(questions_out),
                "subject": request.subject,
                "difficulty": request.difficulty,
                "years": request.years,
                "answers_missing": result.get("answers_missing", []),
            },
        )
    except InsufficientQuestionsError as e:
        return JSONResponse(
            status_code=400,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "INSUFFICIENT_QUESTIONS", "message": str(e)},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "ASSESSMENT_UNAVAILABLE", "message": str(e)},
            },
        )


# ── Story 4.2: Question Generator RAG ────────────────────────────────────────

@app.post(
    "/api/v1/questions/generate",
    response_model=QuestionGenerateResponse,
    tags=["RAG"],
    summary="Gerar questoes ineditas no estilo ENEM",
    description="Usa RAG com contexto de questoes reais do ENEM para gerar questoes novas via GPT-4o.",
)
async def generate_questions(request: QuestionGenerateRequest):
    """Endpoint para gerar questoes ineditas estilo ENEM via RAG + GPT-4o."""
    if rag_question_generator is None:
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "GENERATION_UNAVAILABLE", "message": "Servico de geracao de questoes indisponivel"},
            },
        )
    try:
        questions, questions_meta = await rag_question_generator.generate_questions(
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            count=request.count,
            style=request.style,
        )
        return QuestionGenerateResponse(
            data=[GeneratedQuestion(**q) for q in questions],
            meta={
                "total": len(questions),
                "requested_count": request.count,
                "subject": request.subject,
                "topic": request.topic,
                "difficulty": request.difficulty,
                "style": request.style,
                "model": "gpt-4o",
                "generated_at": datetime.now().isoformat(),
                "rag_context_available": questions_meta.get("rag_context_available", True),
            },
        )
    except Exception as e:
        logger.error(f"Erro na geracao de questoes: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "GENERATION_UNAVAILABLE", "message": str(e)},
            },
        )


# ---------------------------------------------------------------------------
# Admin — Dead Letter Queue (Story 6.2)
# ---------------------------------------------------------------------------

class DeadLetterResolveRequest(BaseModel):
    resolved_by: str = Field(..., description="Username que resolveu")
    resolution_notes: str = Field("", description="Notas de resolução")


@app.get("/api/v1/admin/dead-letter", tags=["Admin"])
async def list_dead_letter(
    status: str = "pending",
    limit: int = 20,
    offset: int = 0,
):
    """List dead letter queue entries with pagination."""
    if limit > 100:
        limit = 100

    try:
        import psycopg2

        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            from src.enem_ingestion.dead_letter_queue import DeadLetterQueue

            dlq = DeadLetterQueue(conn)
            items, total = dlq.list_pending(limit=limit, offset=offset, status=status)
        finally:
            conn.close()

        return {
            "data": items,
            "meta": {"total": total, "limit": limit, "offset": offset},
        }
    except Exception as e:
        logger.error(f"Dead letter list error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "DEAD_LETTER_UNAVAILABLE", "message": str(e)},
            },
        )


@app.patch("/api/v1/admin/dead-letter/{dl_id}", tags=["Admin"])
async def resolve_dead_letter(dl_id: str, body: DeadLetterResolveRequest):
    """Mark a dead letter entry as resolved."""
    try:
        import psycopg2

        conn = psycopg2.connect(**DATABASE_CONFIG)
        try:
            from src.enem_ingestion.dead_letter_queue import DeadLetterQueue

            dlq = DeadLetterQueue(conn)
            updated = dlq.resolve(dl_id, body.resolved_by, body.resolution_notes)
        finally:
            conn.close()

        if not updated:
            return JSONResponse(
                status_code=404,
                content={
                    "data": None,
                    "meta": {},
                    "error": {"code": "NOT_FOUND", "message": f"Dead letter {dl_id} not found or already resolved"},
                },
            )

        return {"data": {"id": dl_id, "status": "resolved"}, "meta": {}}
    except Exception as e:
        logger.error(f"Dead letter resolve error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "DEAD_LETTER_UNAVAILABLE", "message": str(e)},
            },
        )


if __name__ == "__main__":
    import uvicorn
    print("Iniciando servidor ENEM RAG API...")
    print("Acesse: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    uvicorn.run("fastapi_app_clean:app", host="0.0.0.0", port=8000, reload=True)
