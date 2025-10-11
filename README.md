# ��� ENEM Questions RAG System

Sistema RAG (Retrieval-Augmented Generation) completo para questões do ENEM com FastAPI, PostgreSQL e documentação Swagger automática.

## ��� Visão Geral

Este projeto implementa um sistema completo para processamento, armazenamento e acesso às questões do ENEM (Exame Nacional do Ensino Médio). O sistema inclui:

- **Extração automática** de questões e gabaritos de PDFs oficiais do ENEM
- **API REST** moderna com FastAPI e documentação Swagger
- **Banco de dados** PostgreSQL otimizado para busca textual
- **Interface web** interativa para exploração dos dados
- **Docker** para deployment simplificado

## ��� Funcionalidades Principais

### ��� Processamento de Dados
- ✅ **2.452 questões** processadas (2020-2024)
- ✅ **12.260 alternativas** categorizadas
- ✅ **4.633 gabaritos** com respostas corretas
- ✅ **Múltiplos anos** e tipos de aplicação
- ✅ **Metadados completos** (matérias, anos, tipos)

### ��� API REST Completa
- **Busca paginada** com filtros avançados
- **Filtros por ano, matéria, tipo** de exame
- **Estatísticas detalhadas** do conjunto de dados
- **Documentação Swagger** interativa
- **Respostas JSON** estruturadas

### ���️ Infraestrutura
- **FastAPI** para alta performance
- **PostgreSQL** com busca textual otimizada
- **Docker Compose** para orchestração
- **CORS** configurado para integração frontend
- **Health checks** para monitoramento

## ��� Dados Disponíveis

| Categoria | Quantidade | Descrição |
|-----------|------------|-----------|
| **Questões** | 2.452 | Questões completas com enunciados |
| **Alternativas** | 12.260 | Opções A, B, C, D, E categorizadas |
| **Gabaritos** | 4.633 | Respostas corretas vinculadas |
| **Anos** | 2020-2024 | 5 anos de provas do ENEM |
| **Matérias** | 2 principais | Ciências Humanas, Linguagens |

## ���️ Tecnologias Utilizadas

### Backend
- **Python 3.11+**
- **FastAPI** - Framework web moderno e rápido
- **PostgreSQL 15** - Banco de dados relacional
- **Pydantic** - Validação e serialização de dados
- **PDFPlumber** - Extração de texto de PDFs
- **psycopg2** - Driver PostgreSQL para Python

### DevOps
- **Docker & Docker Compose** - Containerização
- **Uvicorn** - Servidor ASGI para FastAPI
- **Git** - Controle de versão

### Frontend/Docs
- **Swagger UI** - Documentação interativa da API
- **ReDoc** - Documentação alternativa
- **HTML/CSS/JS** - Interface web customizada

## 🚀 Início Rápido

### 🐳 Execução com Docker (Recomendado)

#### Pré-requisitos
- Docker Desktop instalado e rodando
- Docker Compose
- Git

#### Instruções Completas para Subir a Infraestrutura

### 1. Clone o Repositório
```bash
git clone https://github.com/andrehsc/enem-questions-rag.git
cd enem-questions-rag
```

### 2. Verificar Docker
```bash
# Verificar se Docker está funcionando
docker --version
docker-compose --version

# Se houver erro, reinicie o Docker Desktop
```

### 3. Subir Infraestrutura Completa
```bash
# Subir todos os serviços (PostgreSQL + Redis + API)
docker-compose up -d

# Acompanhar logs da inicialização
docker-compose logs -f

# Verificar status dos containers
docker-compose ps
```

### 4. Aguardar Inicialização
- **PostgreSQL**: ~10-15 segundos para estar ready
- **Redis**: ~5 segundos
- **API**: ~20-30 segundos (aguarda DB + instala deps)

### 5. Acessar a Aplicação
- **API Principal**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Estatísticas**: http://localhost:8000/stats

### 6. Comandos Úteis do Docker

#### Gerenciamento de Containers
```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (limpa dados)
docker-compose down -v

# Reconstruir após mudanças no código
docker-compose up --build

# Reiniciar um serviço específico
docker-compose restart api
```

#### Logs e Debugging
```bash
# Ver logs de todos os serviços
docker-compose logs -f

# Logs de serviço específico
docker-compose logs api
docker-compose logs postgres
docker-compose logs redis

# Últimas 50 linhas de log
docker-compose logs --tail=50 api
```

#### Executar Comandos nos Containers
```bash
# Acessar container da API
docker-compose exec api bash

# Acessar PostgreSQL
docker-compose exec postgres psql -U postgres -d enem_rag

# Acessar Redis
docker-compose exec redis redis-cli

# Testar conectividade
docker-compose exec api ping postgres
docker-compose exec api ping redis
```

### 7. Troubleshooting

#### Containers não sobem
```bash
# Limpar sistema Docker
docker-compose down -v
docker system prune -f
docker-compose up --build

# Verificar espaço em disco
docker system df
```

#### API não responde
```bash
# Verificar logs da API
docker-compose logs api

# Testar conectividade com DB
docker-compose exec api python -c "
import psycopg2
try:
    conn = psycopg2.connect(host='postgres', user='postgres', password='postgres123', database='enem_rag')
    print('✅ Conectado ao PostgreSQL')
    conn.close()
except Exception as e:
    print(f'❌ Erro PostgreSQL: {e}')
"

# Verificar Redis
docker-compose exec api python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('✅ Conectado ao Redis')
except Exception as e:
    print(f'❌ Erro Redis: {e}')
"
```

#### Docker Desktop Issues
```bash
# Reiniciar Docker Desktop
# Windows: Clicar com botão direito no ícone Docker Desktop > Restart
# Ou via PowerShell (como Admin):
Restart-Service *docker*
```

### 🏠 Execução Local (Desenvolvimento)

#### Para desenvolvimento sem Docker:

```bash
# 1. Instalar dependências
cd api/
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=enem_rag
export DB_USER=postgres
export DB_PASS=postgres123
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 3. Executar PostgreSQL e Redis localmente

# 4. Executar API
python fastapi_app.py
# ou
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

## ��� Uso da API

### Endpoints Principais

#### ��� Estatísticas Gerais
```bash
GET /stats
```
Retorna estatísticas completas sobre questões, alternativas e gabaritos.

#### ��� Buscar Questões
```bash
# Busca básica com paginação
GET /questions?page=1&size=10

# Filtrar por ano
GET /questions?year=2024&size=5

# Filtrar por matéria
GET /questions?subject=ciencias_humanas

# Combinar filtros
GET /questions?year=2023&subject=linguagens&size=20
```

#### ��� Status da API
```bash
GET /health
```

### Exemplos de Resposta

#### Estatísticas
```json
{
  "total_questions": 2452,
  "total_alternatives": 12260,
  "total_answer_keys": 4633,
  "years_available": [2024, 2023, 2022, 2021, 2020],
  "exam_types": ["regular", "reaplicacao_PPL"],
  "subjects": ["ciencias_humanas", "linguagens"]
}
```

#### Questões
```json
{
  "items": [
    {
      "id": "uuid-da-questao",
      "exam_year": 2024,
      "exam_type": "regular",
      "number": 123,
      "subject": "ciencias_humanas",
      "correct_answer": "C",
      "statement_preview": "Texto da questão..."
    }
  ],
  "total": 2452,
  "page": 1,
  "size": 10,
  "has_next": true
}
```

## ��� Desenvolvimento

### Estrutura do Projeto
```
enem-questions-rag/
├── api/                    # API FastAPI
│   ├── fastapi_app.py     # Aplicação principal
│   └── requirements.txt   # Dependências da API
├── database/              # Scripts SQL
│   ├── init.sql          # Schema inicial
│   └── complete-init.sql # Schema completo
├── scripts/               # Scripts de processamento
│   ├── full_ingestion_report.py    # Ingestão completa
│   ├── process_answer_keys.py      # Processamento de gabaritos
│   └── test_answer_keys.py         # Testes
├── src/                   # Código fonte Python
│   └── enem_ingestion/   # Módulo de ingestão
├── data/                  # Dados (ignorado no git)
│   └── downloads/        # PDFs do ENEM
├── docker-compose.yml     # Orchestração Docker
└── README.md             # Documentação
```

### Configuração Local

#### 1. Ambiente Python
```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

#### 2. Banco de Dados
```bash
# Iniciar PostgreSQL via Docker
docker-compose up -d postgres

# Executar migrations
psql -h localhost -U postgres -d enem_rag -f database/complete-init.sql
```

#### 3. Executar API
```bash
cd api
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

### Processamento de Dados

#### Ingestão Completa
```bash
# Processar todos os PDFs
python scripts/full_ingestion_report.py

# Processar apenas gabaritos
python scripts/process_all_answer_keys.py
```

#### Adicionar Novos PDFs
1. Coloque os PDFs em `data/downloads/YYYY/`
2. Execute o script de ingestão
3. Verifique os logs para questões processadas

## ��� Testes

```bash
# Testes unitários
python -m pytest tests/

# Teste da API
curl http://localhost:8000/health

# Teste de busca
curl "http://localhost:8000/questions?size=5"
```

## ��� Performance

- **Questões por segundo**: ~100 (processamento)
- **Consultas por segundo**: ~1000 (API)
- **Tempo de inicialização**: ~30-60 segundos
- **Uso de memória**: ~500MB (total)
- **Tamanho do banco**: ~50MB (sem PDFs)

## ��� Segurança

- Validação de entrada com Pydantic
- Sanitização de queries SQL
- CORS configurado adequadamente
- Variáveis de ambiente para credenciais
- Rate limiting disponível (não implementado)

## ��� Deploy em Produção

### Docker Compose (Recomendado)
```bash
# Produção
docker-compose -f docker-compose.prod.yml up -d

# Com load balancer
docker-compose -f docker-compose.prod.yml -f docker-compose.lb.yml up -d
```

### Variáveis de Ambiente
```bash
# .env para produção
DB_HOST=postgres-prod
DB_PASSWORD=senha-segura-aqui
API_HOST=0.0.0.0
API_PORT=8000
```

## ��� Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Padrões de Código
- Python: PEP 8
- Docstrings: Google Style
- Commits: Conventional Commits
- Testes: pytest com coverage > 80%

## ��� Changelog

### v2.0.0 (2024-10-11)
- ✅ Ingestão completa de 54 arquivos ENEM
- ✅ 2.452 questões processadas
- ✅ 4.633 gabaritos carregados
- ✅ API FastAPI com Swagger
- ✅ Docker Compose completo
- ✅ Interface web interativa

### v1.0.0 (2024-10-10)
- ✅ Sistema básico de ingestão
- ✅ API inicial
- ✅ Banco PostgreSQL

## ��� Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ��� Contato

- **Autor**: Andre Henrique
- **GitHub**: [@andrehsc](https://github.com/andrehsc)
- **Email**: contato@exemplo.com

## ��� Agradecimentos

- **INEP** - Pelos dados públicos do ENEM
- **FastAPI** - Framework web excepcional
- **PostgreSQL** - Banco de dados robusto
- **Comunidade Python** - Ferramentas e bibliotecas

---

⭐ **Se este projeto foi útil, considere dar uma estrela!** ⭐
