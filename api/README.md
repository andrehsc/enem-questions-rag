# ��� ENEM Questions RAG API

API REST navegável construída com FastAPI para acessar questões do ENEM com metadados completos, alternativas e gabaritos.

## ��� Dados Disponíveis

- **2.452 questões** processadas e indexadas
- **12.260 alternativas** (5 por questão)
- **4.308 gabaritos** carregados
- **Anos:** 2020-2024
- **Matérias:** Linguagens, Ciências Humanas, Ciências da Natureza, Matemática

## ��� Executar com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Executar
```bash
# Na raiz do projeto
docker-compose up --build
```

A API estará disponível em:
- **Interface principal:** http://localhost:8000
- **Documentação Swagger:** http://localhost:8000/docs
- **Documentação ReDoc:** http://localhost:8000/redoc

## ��� Endpoints Principais

### Health Check
```http
GET /health
```
Verifica status da API e conexão com banco.

### Estatísticas
```http
GET /stats
```
Retorna estatísticas completas da base de dados.

### Listar Questões
```http
GET /questions?page=1&size=20&year=2024&subject=Linguagens&caderno=CD1
```

Parâmetros:
- `page`: Número da página (padrão: 1)
- `size`: Itens por página (1-100, padrão: 20)
- `year`: Filtrar por ano (2020-2024)
- `subject`: Filtrar por matéria
- `caderno`: Filtrar por caderno (CD1, CD2, etc.)

### Questão Específica
```http
GET /questions/{question_id}
```
Retorna questão completa com alternativas, gabarito e metadados.

### Busca Textual
```http
GET /search?q=fotossíntese&page=1&size=10
```
Busca questões por texto usando busca textual em português com ranking de relevância.

### Filtros Disponíveis
```http
GET /years        # Anos disponíveis
GET /subjects     # Matérias disponíveis
```

## ��� Exemplos de Uso

### Buscar questões de 2024
```bash
curl "http://localhost:8000/questions?year=2024&size=5"
```

### Buscar questões de Matemática
```bash
curl "http://localhost:8000/questions?subject=Matemática"
```

### Buscar por texto
```bash
curl "http://localhost:8000/search?q=meio%20ambiente&size=5"
```

### Obter questão específica
```bash
curl "http://localhost:8000/questions/123e4567-e89b-12d3-a456-426614174000"
```

## ���️ Estrutura de Resposta

### Questão Completa
```json
{
  "id": "uuid",
  "question_number": 45,
  "subject": "LINGUAGENS",
  "statement": "O enunciado completo da questão...",
  "alternatives": [
    {
      "id": "uuid",
      "letter": "A",
      "text": "Primeira alternativa...",
      "order": 1
    }
  ],
  "answer_key": {
    "id": "uuid",
    "question_number": 45,
    "correct_answer": "C",
    "subject": "linguagens",
    "language_option": "ingles"
  },
  "metadata": {
    "id": "uuid",
    "year": 2024,
    "day": 1,
    "caderno": "CD1",
    "application_type": "regular",
    "file_type": "caderno_questoes",
    "pdf_filename": "2024_PV_impresso_D1_CD1.pdf"
  }
}
```

### Lista Paginada
```json
{
  "items": [...],
  "total": 2452,
  "page": 1,
  "size": 20,
  "pages": 123
}
```

## ��� Configuração

### Variáveis de Ambiente
- `DATABASE_URL`: URL de conexão PostgreSQL (padrão: conexão local)

### Desenvolvimento Local
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## ���️ Arquitetura

- **FastAPI**: Framework web assíncrono
- **Pydantic**: Validação e serialização de dados
- **PostgreSQL**: Banco de dados com busca textual
- **Docker**: Containerização e orquestração
- **Uvicorn**: Servidor ASGI de alta performance

## ��� Recursos Avançados

- ✅ Busca textual em português com stemming
- ✅ Paginação otimizada
- ✅ Filtros múltiplos combinados
- ✅ Documentação automática (OpenAPI)
- ✅ Validação de dados com Pydantic
- ✅ CORS configurado para desenvolvimento
- ✅ Health checks para monitoramento
- ✅ Estrutura pronta para produção
