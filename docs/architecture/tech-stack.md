# Stack Tecnológico - ENEM Questions RAG

## Visão Geral da Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Database      │
│   (Futuro)      │────│   FastAPI       │────│   PostgreSQL    │
│                 │    │   Python 3.11+  │    │   Vector DB     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   Infrastructure│
                       │   Docker        │
                       │   Docker Compose│
                       └─────────────────┘
```

## Core Stack

### Backend Framework
**FastAPI 0.104.0+**
- **Escolha**: Framework web moderno para Python
- **Justificativa**: 
  - Performance superior (baseado em Starlette + Pydantic)
  - Documentação automática (OpenAPI/Swagger)
  - Type hints nativos
  - Async/await support
  - Validação automática de dados
- **Uso**: API REST para questões ENEM, endpoints de busca e filtros

### Linguagem Principal
**Python 3.11+**
- **Escolha**: Linguagem principal do projeto
- **Justificativa**:
  - Ecossistema rico para ML/AI (futuro RAG)
  - Bibliotecas robustas para processamento de dados
  - Facilidade de desenvolvimento e manutenção
  - Comunidade ativa
- **Uso**: Toda lógica de backend, processamento de dados, API

### Database
**PostgreSQL 16**
- **Escolha**: Banco de dados relacional principal
- **Justificativa**:
  - ACID compliance
  - Suporte nativo a JSON/JSONB
  - Extensões para full-text search
  - Preparação para extensões de vetor (pgvector) - RAG futuro
  - Performance e confiabilidade comprovadas
- **Uso**: Armazenamento principal de questões, metadados, alternativas

**Schema Principal**: `enem_questions`
- `questions`: Questões principais
- `exam_metadata`: Metadados dos exames
- `question_alternatives`: Alternativas das questões
- `answer_keys`: Gabaritos
- `question_images`: Imagens das questões (futuro)

### ORM/Database Access
**SQLAlchemy 2.0+ com psycopg2-binary**
- **Escolha**: ORM moderno para Python
- **Justificativa**:
  - Async support
  - Type safety melhorada
  - Performance otimizada
  - Migrations suportadas
- **Uso**: Acesso ao banco, queries otimizadas

### Containerization
**Docker + Docker Compose**
- **Escolha**: Containerização completa
- **Justificativa**:
  - Ambiente consistente entre dev/prod
  - Isolamento de dependências
  - Facilita deploy e scaling
  - Networking simplificado entre serviços
- **Uso**: Containerização de API, database, cache

### Data Processing
**Pandas 2.0+ + NumPy 1.24+**
- **Escolha**: Processamento de dados científicos
- **Justificativa**:
  - Padrão da indústria para análise de dados
  - Performance otimizada
  - Integração natural com Python ML stack
- **Uso**: ETL de dados ENEM, análises estatísticas

### PDF Processing
**pdfplumber 0.9+ + PyPDF2 3.0+**
- **Escolha**: Extração de conteúdo de PDFs
- **Justificativa**:
  - pdfplumber: Melhor para extração de texto estruturado
  - PyPDF2: Backup e operações básicas
  - Complementares para diferentes tipos de PDF
- **Uso**: Processamento dos PDFs originais do ENEM

### Web Scraping
**requests 2.31+ + BeautifulSoup4 4.12+ + lxml 4.9+**
- **Escolha**: Stack completa para web scraping
- **Justificativa**:
  - requests: HTTP client confiável
  - BeautifulSoup: Parse HTML intuitivo
  - lxml: Performance para XML/HTML parsing
- **Uso**: Coleta de dados de fontes online do ENEM

### Testing
**pytest 7.4+ + pytest-cov 4.1+ + pytest-mock 3.11+**
- **Escolha**: Framework de testes moderno
- **Justificativa**:
  - Sintaxe clara e intuitiva
  - Fixtures poderosas
  - Coverage integrado
  - Mocking simplificado
- **Uso**: Testes unitários, integração, coverage

### Code Quality
**black 23.0+**
- **Escolha**: Formatador de código automático
- **Justificativa**:
  - Formatação consistente
  - Zero configuração
  - Padrão da comunidade Python
- **Uso**: Formatação automática do código

### Environment Management
**python-dotenv 1.0+**
- **Escolha**: Gestão de variáveis de ambiente
- **Justificativa**:
  - Configuração flexível por ambiente
  - Segurança (secrets fora do código)
  - Padrão da comunidade
- **Uso**: Configuração de database, API keys, etc.

### HTTP Server
**Uvicorn 0.24+ [standard]**
- **Escolha**: ASGI server para FastAPI
- **Justificativa**:
  - Performance alta
  - Suporte completo a async
  - Hot reload para desenvolvimento
  - Padrão recomendado para FastAPI
- **Uso**: Servidor HTTP para API em produção

## Stack de Infraestrutura

### Development
```yaml
# docker-compose.yml structure
services:
  - postgres: Database principal
  - redis: Cache e sessões (compartilhado)
  - enem-rag-api: API FastAPI
```

### Networking
- **Rede Docker**: `teachershub-enem-network`
- **Portas Expostas**:
  - API: `8001:8000`
  - PostgreSQL: `5433:5432`
  - Redis: `6380:6379`

### Volumes
- **postgres_data**: Persistência do banco
- **Mounts**: Código fonte para desenvolvimento

## Dependências Específicas

### Core API
```python
fastapi>=0.104.0          # Framework web principal
uvicorn[standard]>=0.24.0 # ASGI server
python-multipart>=0.0.6   # Form data handling
```

### Database
```python
psycopg2-binary>=2.9.0    # PostgreSQL driver
sqlalchemy>=2.0.0         # ORM moderno
```

### Data Processing
```python
pandas>=2.0.0             # Data analysis
numpy>=1.24.0             # Numerical computing
```

### Document Processing
```python
PyPDF2>=3.0.0             # PDF manipulation
pdfplumber>=0.9.0         # Advanced PDF text extraction
```

### Web & HTTP
```python
requests>=2.31.0          # HTTP client
beautifulsoup4>=4.12.0    # HTML parsing
lxml>=4.9.0               # XML/HTML parser
```

### Development
```python
pytest>=7.4.0            # Testing framework
pytest-cov>=4.1.0        # Coverage
pytest-mock>=3.11.0      # Mocking
black>=23.0.0             # Code formatting
python-dotenv>=1.0.0      # Environment variables
```

## Arquitetura de Dados

### Modelo Relacional
```sql
enem_questions.exam_metadata
├── id (PK)
├── year
├── day
├── caderno
├── application_type
└── ...

enem_questions.questions
├── id (PK, UUID)
├── exam_metadata_id (FK)
├── question_number
├── question_text
├── subject
└── ...

enem_questions.question_alternatives
├── id (PK)
├── question_id (FK)
├── alternative_letter
├── alternative_text
└── ...

enem_questions.answer_keys
├── id (PK)
├── exam_metadata_id (FK)
├── question_number
├── correct_answer
└── ...
```

## Performance Stack

### Database Optimization
- **Índices**: Otimizados para queries frequentes
- **Conexões**: Pool de conexões via SQLAlchemy
- **Queries**: Otimizadas para evitar N+1

### API Performance
- **Async**: Operações I/O não-bloqueantes
- **Paginação**: Responses limitadas e paginadas
- **Caching**: Redis para cache de sessões

### Memory Management
- **Streaming**: Para arquivos grandes
- **Lazy Loading**: Carregamento sob demanda
- **Connection Pooling**: Reutilização de conexões

## Security Stack

### Data Validation
- **Pydantic**: Validação automática de tipos
- **SQL Injection**: Queries parametrizadas
- **Input Sanitization**: Validação de entrada

### Environment Security
- **Secrets**: Variáveis de ambiente
- **Network**: Isolamento via Docker networks
- **Database**: Credenciais não hard-coded

## Monitoring & Logging

### Logging
```python
# Configuração padrão
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Health Checks
- **Database**: Connection health
- **API**: Health endpoint
- **Docker**: Health checks automáticos

## Future Stack (Roadmap)

### RAG Enhancement
- **Vector Database**: pgvector ou Chroma
- **Embeddings**: OpenAI, Sentence Transformers
- **LLM**: GPT-4, Claude, ou local models

### Frontend
- **Framework**: React/Next.js ou Vue.js
- **State Management**: Redux/Pinia
- **UI Library**: Material-UI ou Tailwind

### Advanced Features
- **Search**: ElasticSearch para full-text search
- **Cache**: Redis avançado com TTL
- **Message Queue**: Celery + Redis para jobs
- **Monitoring**: Prometheus + Grafana

## Deployment Stack

### Current (Development)
- **Docker Compose**: Multi-container orchestration
- **Local Development**: Hot reload, debugging

### Future (Production)
- **Kubernetes**: Container orchestration
- **CI/CD**: GitHub Actions
- **Cloud**: AWS/GCP/Azure
- **Load Balancer**: Nginx ou cloud LB

## Standards & Conventions

### Version Management
- **Python**: Semantic versioning
- **Dependencies**: Pinned versions
- **Docker**: Tagged images

### Code Standards
- **Encoding**: UTF-8 obrigatório
- **Linting**: black para formatação
- **Testing**: 80%+ coverage target
- **Documentation**: Docstrings obrigatórias

### Git Workflow
- **Branches**: `feature/story-{id}-{description}`
- **Commits**: Conventional commits
- **Tags**: Semantic versioning para releases

Esta stack foi escolhida para balancear performance, maintainability, e preparação para features futuras de RAG e ML.
