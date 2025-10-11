#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Simples para ENEM Questions - Demo
"""

import json
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

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
        }
    },
    {
        "id": 2,
        "exam_year": 2023,
        "exam_type": "ENEM",
        "number": 2,
        "statement": "A função quadrática f(x) = ax² + bx + c tem seu vértice no ponto (2, -1) e passa pelo ponto (0, 3). Determine o valor de 'a'.",
        "alternatives": [
            {"id": 6, "letter": "A", "text": "a = 1", "order": 1},
            {"id": 7, "letter": "B", "text": "a = 2", "order": 2},
            {"id": 8, "letter": "C", "text": "a = -1", "order": 3},
            {"id": 9, "letter": "D", "text": "a = 3", "order": 4},
            {"id": 10, "letter": "E", "text": "a = -2", "order": 5}
        ],
        "answer_key": {
            "id": 2,
            "correct_answer": "A", 
            "subject": "Matemática",
            "language_option": None
        }
    }
]

class EnemAPIHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        params = parse_qs(parsed_path.query)
        
        try:
            if path == "/":
                self.serve_homepage()
            elif path == "/questions":
                self.serve_questions(params)
            elif path.startswith("/questions/"):
                question_id = int(path.split("/")[-1])
                self.serve_question_by_id(question_id)
            elif path == "/search":
                query = params.get("q", [""])[0]
                self.serve_search(query, params)
            elif path == "/stats":
                self.serve_stats()
            elif path == "/health":
                self.serve_health()
            else:
                self.send_error(404, "Endpoint não encontrado")
        except Exception as e:
            self.send_error(500, f"Erro interno: {str(e)}")
    
    def serve_homepage(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <title>ENEM Questions API - Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .method { color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
        .get { background: #61affe; }
        a { color: #61affe; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>��� ENEM Questions API - Demo</h1>
    <p>API navegável para questões do ENEM com dados simulados</p>
    
    <h2>��� Endpoints Disponíveis</h2>
    
    <div class="endpoint">
        <span class="method get">GET</span> <strong>/questions</strong>
        <p>Lista questões com paginação. Parâmetros: page, size, year, subject</p>
        <a href="/questions?page=1&size=5">Exemplo: /questions?page=1&size=5</a>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <strong>/questions/{id}</strong>
        <p>Obtém questão completa por ID</p>
        <a href="/questions/1">Exemplo: /questions/1</a>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <strong>/search</strong>
        <p>Busca questões por texto. Parâmetro: q</p>
        <a href="/search?q=democrática">Exemplo: /search?q=democrática</a>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <strong>/stats</strong>
        <p>Estatísticas gerais do sistema</p>
        <a href="/stats">Ver estatísticas</a>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span> <strong>/health</strong>
        <p>Status da API</p>
        <a href="/health">Verificar saúde</a>
    </div>
    
    <h2>��� Dados Disponíveis</h2>
    <ul>
        <li><strong>Total de questões:</strong> 2 (demo)</li>
        <li><strong>Anos:</strong> 2023</li>
        <li><strong>Matérias:</strong> Ciências Humanas, Matemática</li>
    </ul>
    
    <h2>��� Exemplos de Uso</h2>
    <ul>
        <li><a href="/questions?year=2023">Questões de 2023</a></li>
        <li><a href="/questions?subject=Matemática">Questões de Matemática</a></li>
        <li><a href="/search?q=função">Buscar por "função"</a></li>
    </ul>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def serve_questions(self, params):
        page = int(params.get("page", [1])[0])
        size = int(params.get("size", [10])[0])
        year = params.get("year", [None])[0]
        subject = params.get("subject", [None])[0]
        
        filtered_questions = sample_questions
        
        if year:
            filtered_questions = [q for q in filtered_questions if q["exam_year"] == int(year)]
        if subject:
            filtered_questions = [q for q in filtered_questions if q["answer_key"]["subject"] == subject]
        
        total = len(filtered_questions)
        start = (page - 1) * size
        end = start + size
        page_questions = filtered_questions[start:end]
        
        result = {
            "items": page_questions,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 1
        }
        
        self.send_json_response(result)
    
    def serve_question_by_id(self, question_id):
        question = next((q for q in sample_questions if q["id"] == question_id), None)
        
        if not question:
            self.send_error(404, "Questão não encontrada")
            return
        
        self.send_json_response(question)
    
    def serve_search(self, query, params):
        page = int(params.get("page", [1])[0])
        size = int(params.get("size", [10])[0])
        
        if not query:
            self.send_error(400, "Parâmetro 'q' é obrigatório")
            return
        
        filtered_questions = [
            q for q in sample_questions 
            if query.lower() in q["statement"].lower()
        ]
        
        total = len(filtered_questions)
        start = (page - 1) * size
        end = start + size
        page_questions = filtered_questions[start:end]
        
        result = {
            "items": page_questions,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 1,
            "query": query
        }
        
        self.send_json_response(result)
    
    def serve_stats(self):
        stats = {
            "total_questions": len(sample_questions),
            "total_alternatives": sum(len(q["alternatives"]) for q in sample_questions),
            "total_answer_keys": len([q for q in sample_questions if q["answer_key"]]),
            "years_available": list(set(q["exam_year"] for q in sample_questions)),
            "exam_types": list(set(q["exam_type"] for q in sample_questions)),
            "subjects": list(set(q["answer_key"]["subject"] for q in sample_questions if q["answer_key"]))
        }
        self.send_json_response(stats)
    
    def serve_health(self):
        health = {
            "status": "healthy",
            "database_connected": True,
            "total_questions": len(sample_questions),
            "timestamp": "2024-10-11T02:15:00Z"
        }
        self.send_json_response(health)
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(json_data.encode("utf-8"))

if __name__ == "__main__":
    PORT = 8000
    Handler = EnemAPIHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"��� ENEM Questions API Demo rodando em http://localhost:{PORT}")
        print("��� Acesse http://localhost:8000 para ver a documentação")
        print("��� Endpoints disponíveis:")
        print("   - GET /questions - Lista questões")  
        print("   - GET /questions/{id} - Questão por ID")
        print("   - GET /search?q=termo - Busca questões")
        print("   - GET /stats - Estatísticas")
        print("   - GET /health - Status da API")
        print("\n��� Pressione Ctrl+C para parar o servidor")
        httpd.serve_forever()
