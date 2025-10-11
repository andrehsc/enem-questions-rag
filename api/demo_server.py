#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENEM Questions API - FastAPI com Swagger
API navegável para questões do ENEM com documentação automática
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn

# Modelos Pydantic para documentação Swagger
class Alternative(BaseModel):
    letter: str = Field(..., description="Letra da alternativa (A, B, C, D, E)")
    text: str = Field(..., description="Texto da alternativa")

class Question(BaseModel):
    id: int = Field(..., description="ID único da questão")
    year: int = Field(..., description="Ano do exame")
    type: str = Field(..., description="Tipo do exame (ENEM)")
    number: int = Field(..., description="Número da questão")
    statement: str = Field(..., description="Enunciado da questão")
    alternatives: List[Alternative] = Field(..., description="Lista de alternativas")
    answer: str = Field(..., description="Resposta correta (A, B, C, D, E)")
    subject: str = Field(..., description="Matéria da questão")

class QuestionList(BaseModel):
    items: List[Question] = Field(..., description="Lista de questões")
    total: int = Field(..., description="Total de questões encontradas")

class SearchResult(BaseModel):
    items: List[Question] = Field(..., description="Questões encontradas")
    total: int = Field(..., description="Total de questões encontradas")
    query: str = Field(..., description="Termo pesquisado")

class Stats(BaseModel):
    total_questions: int = Field(..., description="Total de questões disponíveis")
    years: List[int] = Field(..., description="Anos disponíveis")
    subjects: List[str] = Field(..., description="Matérias disponíveis")

# Dados de demonstração
questions_data = [
    {
        "id": 1,
        "year": 2023,
        "type": "ENEM",
        "number": 1,
        "statement": "Em uma sociedade democratica, a participacao politica dos cidadaos e fundamental. Qual alternativa representa melhor o conceito de cidadania ativa?",
        "alternatives": [
            {"letter": "A", "text": "Apenas votar nas eleicoes presidenciais."},
            {"letter": "B", "text": "Participar ativamente de movimentos sociais e politicos."},
            {"letter": "C", "text": "Criticar o governo nas redes sociais."},
            {"letter": "D", "text": "Pagar impostos em dia."},
            {"letter": "E", "text": "Obedecer as leis sem questionamento."}
        ],
        "answer": "B",
        "subject": "Ciencias Humanas"
    },
    {
        "id": 2,
        "year": 2023,
        "type": "ENEM", 
        "number": 2,
        "statement": "A funcao quadratica f(x) = ax² + bx + c tem seu vertice no ponto (2, -1) e passa pelo ponto (0, 3). Determine o valor de a.",
        "alternatives": [
            {"letter": "A", "text": "a = 1"},
            {"letter": "B", "text": "a = 2"},
            {"letter": "C", "text": "a = -1"},
            {"letter": "D", "text": "a = 3"},
            {"letter": "E", "text": "a = -2"}
        ],
        "answer": "A",
        "subject": "Matematica"
    }
]

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        
        if path == "/":
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """<!DOCTYPE html>
<html><head><title>ENEM API Demo</title></head>
<body>
<h1>ENEM Questions API Demo</h1>
<h2>Endpoints:</h2>
<ul>
<li><a href="/questions">/questions</a> - Lista questoes</li>
<li><a href="/questions/1">/questions/1</a> - Questao por ID</li>
<li><a href="/search?q=democratica">/search?q=democratica</a> - Busca</li>
<li><a href="/stats">/stats</a> - Estatisticas</li>
</ul>
<h2>Exemplos:</h2>
<ul>
<li><a href="/questions?subject=Matematica">Questoes de Matematica</a></li>
<li><a href="/questions?year=2023">Questoes de 2023</a></li>
</ul>
</body></html>"""
            self.wfile.write(html.encode())
            
        elif path == "/questions":
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            filtered = questions
            if "subject" in params:
                subject = params["subject"][0]
                filtered = [q for q in filtered if q["subject"] == subject]
            if "year" in params:
                year = int(params["year"][0])
                filtered = [q for q in filtered if q["year"] == year]
                
            result = {"items": filtered, "total": len(filtered)}
            self.wfile.write(json.dumps(result, indent=2).encode())
            
        elif path.startswith("/questions/"):
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            try:
                qid = int(path.split("/")[-1])
                question = next((q for q in questions if q["id"] == qid), None)
                if question:
                    self.wfile.write(json.dumps(question, indent=2).encode())
                else:
                    self.wfile.write(json.dumps({"error": "Questao nao encontrada"}).encode())
            except:
                self.wfile.write(json.dumps({"error": "ID invalido"}).encode())
                
        elif path == "/search":
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            query = params.get("q", [""])[0].lower()
            if query:
                filtered = [q for q in questions if query in q["statement"].lower()]
                result = {"items": filtered, "total": len(filtered), "query": query}
            else:
                result = {"error": "Parametro q obrigatorio"}
            self.wfile.write(json.dumps(result, indent=2).encode())
            
        elif path == "/stats":
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            stats = {
                "total_questions": len(questions),
                "years": list(set(q["year"] for q in questions)),
                "subjects": list(set(q["subject"] for q in questions))
            }
            self.wfile.write(json.dumps(stats, indent=2).encode())
            
        else:
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint nao encontrado"}).encode())

if __name__ == "__main__":
    PORT = 8000
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Servidor rodando em http://localhost:{PORT}")
        print("Acesse http://localhost:8000 para documentacao")
        print("Pressione Ctrl+C para parar")
        httpd.serve_forever()
