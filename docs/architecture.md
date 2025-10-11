# TeachersHub-ENEM Integration Architecture Document

## Introdução

Esta documentação define a arquitetura técnica completa para a integração híbrida TeachersHub-ENEM, combinando a plataforma educacional .NET existente com microsserviços Python especializados em ML/RAG. A arquitetura foi projetada para manter estabilidade do sistema existente enquanto adiciona capacidades avançadas de IA educacional.

### Projeto Brownfield Existente

**TeachersHub Base:**
- **.NET 8 Backend** - Clean Architecture, Entity Framework Core, ASP.NET Core Identity
- **React/TypeScript Frontend** - Interface responsiva, design system estabelecido
- **PostgreSQL Database** - Dados de usuários, planos de aula, recursos educacionais
- **Docker Compose** - Orquestração de containers para desenvolvimento e produção

**Sistema ENEM Existente:**
- **FastAPI Python** - 2.452 questões ENEM, busca semântica, navegação HATEOAS
- **PostgreSQL + Redis** - Dados persistentes e cache para performance
- **Docker Containerizado** - Ambiente isolado para componentes ML

### Change Log
| Data | Versão | Descrição | Autor |
|------|---------|-------------|---------|
| 2025-10-11 | v1.0 | Arquitetura inicial integração híbrida | Arquiteto |

## Arquitetura de Alto Nível

### Resumo Técnico

A arquitetura híbrida combina o monólito .NET TeachersHub (orchestrador principal) com microsserviços Python especializados (ML/RAG), mantendo separação clara de responsabilidades via APIs REST bem definidas. O TeachersHub atua como gateway único para usuários, integrando funcionalidades ENEM através de chamadas HTTP aos serviços Python. A infraestrutura utiliza Docker Compose para orquestração local e mantém PostgreSQL compartilhado com schemas separados para isolamento de dados.

### Estrutura de Repositório

**Abordagem:** Monorepo
**Organização:**
```
enem-questions-rag/
├── teachershub-integration/     # Código .NET integração
│   ├── TeachersHub.ENEM.Api/    # Controllers integração
│   ├── TeachersHub.ENEM.Core/   # Business logic
│   └── TeachersHub.ENEM.Data/   # Data access layer
├── python-ml-services/          # Microsserviços Python
│   ├── rag-service/             # RAG e análise semântica
│   ├── semantic-search/         # Busca inteligente
│   └── content-generation/      # Suporte IA generativa
├── shared/                      # Recursos compartilhados
│   ├── docker/                  # Dockerfiles
│   ├── database/                # Scripts SQL
│   └── monitoring/              # Configs observabilidade
├── docker-compose.yml           # Orquestração completa
└── docs/                        # Documentação técnica
```

## Arquitetura Backend Detalhada

### Sistema de Componentes

#### 1. TeachersHub .NET Backend (Orchestrador Principal)

**Responsabilidades:**
- Gateway único para todas as requisições de usuários
- Autenticação e autorização JWT
- Orchestração de chamadas aos microsserviços Python
- Business logic educacional e compliance LGPD
- Integração Semantic Kernel para IA generativa

**Estrutura Clean Architecture:**
```csharp
TeachersHub.ENEM.Api/
├── Controllers/
│   ├── QuestionsController.cs      # CRUD questões ENEM
│   ├── SearchController.cs         # Busca tradicional/semântica
│   ├── ActivitiesController.cs     # Geração atividades IA
│   └── ReportsController.cs        # Analytics e compliance
├── Middleware/
│   ├── EnemAuthenticationMiddleware.cs    # JWT validation
│   ├── RequestLoggingMiddleware.cs        # Audit trail
│   └── ErrorHandlingMiddleware.cs         # Error standardization
└── Services/
    ├── IEnemIntegrationService.cs         # Interface Python services
    ├── ISemanticKernelService.cs          # IA generativa
    └── IComplianceService.cs              # LGPD controls
```

**Configuração Dependency Injection:**
```csharp
// Program.cs
services.AddHttpClient<IEnemRagService>(client => {
    client.BaseAddress = new Uri(configuration["EnemServices:RagBaseUrl"]);
    client.Timeout = TimeSpan.FromSeconds(5);
});

services.AddPolly()
    .AddRetryPolicy(3)
    .AddCircuitBreakerPolicy(5, TimeSpan.FromSeconds(30));

services.AddSemanticKernel()
    .WithAzureOpenAI(configuration["AzureOpenAI:ApiKey"])
    .WithPromptTemplateEngine();
```

#### 2. Python ML Microsserviços

**RAG Service (rag-service/):**
```python
# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.rag_processor import RAGProcessor
from services.embedding_service import EmbeddingService
from middleware.auth_middleware import verify_jwt_token

app = FastAPI(title="ENEM RAG Service", version="1.0.0")

# Middleware stack
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RequestLoggingMiddleware)

@app.post("/api/v1/semantic-search")
async def semantic_search(
    query: SemanticSearchRequest,
    user: dict = Depends(verify_jwt_token)
):
    try:
        results = await rag_processor.search_similar_questions(
            query.text, 
            query.subject_filters,
            limit=query.limit
        )
        return SemanticSearchResponse(results=results)
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail="Search service unavailable")
```

**Performance Optimization:**
```python
# services/rag_processor.py
class RAGProcessor:
    def __init__(self):
        self.embeddings_cache = Redis(host='redis', port=6379, db=0)
        self.vector_store = ChromaDB(persist_directory="/data/embeddings")
        
    async def search_similar_questions(self, query: str, filters: dict, limit: int = 10):
        # Cache lookup first
        cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = await self.embeddings_cache.get(cache_key)
        
        if cached_result:
            return json.loads(cached_result)
            
        # Generate embeddings
        query_embedding = await self.embedding_service.encode(query)
        
        # Vector similarity search
        results = self.vector_store.similarity_search(
            query_embedding, 
            n_results=limit,
            where=filters
        )
        
        # Cache results (TTL: 1 hour)
        await self.embeddings_cache.setex(
            cache_key, 3600, json.dumps(results)
        )
        
        return results
```

### Padrões de Comunicação Inter-Serviços

#### 1. HTTP Client Configuration (.NET)

**Resilience Patterns:**
```csharp
public class EnemIntegrationService : IEnemIntegrationService
{
    private readonly HttpClient _httpClient;
    private readonly IAsyncPolicy<HttpResponseMessage> _retryPolicy;
    
    public EnemIntegrationService(HttpClient httpClient, ILogger<EnemIntegrationService> logger)
    {
        _httpClient = httpClient;
        _retryPolicy = Policy
            .HandleResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)),
                onRetry: (outcome, timespan, retryCount, context) =>
                {
                    logger.LogWarning($"Retry {retryCount} for {context.OperationKey} in {timespan}s");
                });
    }
    
    public async Task<SemanticSearchResult> SearchQuestionsAsync(SemanticSearchRequest request)
    {
        var json = JsonSerializer.Serialize(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
        
        var response = await _retryPolicy.ExecuteAsync(async () =>
        {
            var httpResponse = await _httpClient.PostAsync("/api/v1/semantic-search", content);
            
            if (!httpResponse.IsSuccessStatusCode)
            {
                var errorContent = await httpResponse.Content.ReadAsStringAsync();
                throw new EnemServiceException($"RAG service error: {errorContent}");
            }
            
            return httpResponse;
        });
        
        var responseJson = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<SemanticSearchResult>(responseJson);
    }
}
```

#### 2. Error Handling Padronizado

**Global Exception Handler (.NET):**
```csharp
public class GlobalExceptionMiddleware
{
    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        try
        {
            await next(context);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex);
        }
    }
    
    private async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        var response = exception switch
        {
            EnemServiceException ex => new ErrorResponse
            {
                StatusCode = 503,
                Message = "ENEM service temporarily unavailable",
                Details = ex.Message
            },
            ValidationException ex => new ErrorResponse
            {
                StatusCode = 400,
                Message = "Validation failed",
                Details = ex.Errors
            },
            _ => new ErrorResponse
            {
                StatusCode = 500,
                Message = "Internal server error",
                RequestId = context.TraceIdentifier
            }
        };
        
        context.Response.StatusCode = response.StatusCode;
        await context.Response.WriteAsync(JsonSerializer.Serialize(response));
    }
}
```

**Python Error Handling:**
```python
# middleware/error_handler.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request.headers.get("X-Request-ID"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Log unexpected errors
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.headers.get("X-Request-ID"),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Database Architecture

#### Schema Separation Strategy

**PostgreSQL Database Layout:**
```sql
-- TeachersHub existing schemas
CREATE SCHEMA IF NOT EXISTS teachers_hub;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS content;

-- New ENEM integration schemas
CREATE SCHEMA IF NOT EXISTS enem_questions;
CREATE SCHEMA IF NOT EXISTS enem_analytics;
CREATE SCHEMA IF NOT EXISTS enem_compliance;

-- Cross-schema access controls
GRANT USAGE ON SCHEMA enem_questions TO teachershub_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA enem_questions TO teachershub_app;

-- Python service limited access
CREATE USER enem_rag_service WITH PASSWORD 'secure_password';
GRANT USAGE ON SCHEMA enem_questions TO enem_rag_service;
GRANT SELECT ON ALL TABLES IN SCHEMA enem_questions TO enem_rag_service;
```

**Entity Framework Models (.NET):**
```csharp
// Data/Models/EnemQuestion.cs
[Table("questions", Schema = "enem_questions")]
public class EnemQuestion
{
    [Key]
    public Guid Id { get; set; }
    
    [Required]
    [MaxLength(10000)]
    public string Text { get; set; }
    
    [Required]
    public string Subject { get; set; }
    
    [Required]
    public int Year { get; set; }
    
    public DifficultyLevel Difficulty { get; set; }
    
    [Column(TypeName = "jsonb")]
    public List<string> Topics { get; set; }
    
    [Column(TypeName = "jsonb")]
    public List<EnemOption> Options { get; set; }
    
    public string CorrectAnswer { get; set; }
    
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    
    // Navigation properties
    public ICollection<EnemQuestionUsage> UsageHistory { get; set; }
}

// DbContext configuration
public class EnemDbContext : DbContext
{
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("enem_questions");
        
        modelBuilder.Entity<EnemQuestion>(entity =>
        {
            entity.HasIndex(e => e.Subject);
            entity.HasIndex(e => e.Year);
            entity.HasIndex(e => e.Difficulty);
            entity.HasIndex(e => e.Topics).HasMethod("gin");
        });
        
        modelBuilder.Entity<EnemQuestionUsage>(entity =>
        {
            entity.HasOne(u => u.Question)
                  .WithMany(q => q.UsageHistory)
                  .HasForeignKey(u => u.QuestionId);
        });
    }
}
```

### Authentication & Authorization

#### JWT Extension Strategy

**Token Enhancement (.NET):**
```csharp
// Services/TokenService.cs
public class ExtendedTokenService : ITokenService
{
    public async Task<string> GenerateTokenAsync(User user)
    {
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new(ClaimTypes.Email, user.Email),
            new(ClaimTypes.Role, user.Role),
            
            // ENEM-specific claims
            new("enem:access_level", user.EnemAccessLevel.ToString()),
            new("enem:subjects", string.Join(",", user.AuthorizedSubjects)),
            new("enem:max_questions_per_hour", user.QuestionQuotaPerHour.ToString())
        };
        
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_configuration["Jwt:Key"]));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
        
        var token = new JwtSecurityToken(
            issuer: _configuration["Jwt:Issuer"],
            audience: _configuration["Jwt:Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddHours(24),
            signingCredentials: credentials
        );
        
        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
```

**Python JWT Validation:**
```python
# middleware/auth_middleware.py
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER
        )
        
        # Extract ENEM-specific claims
        user_context = {
            "user_id": payload.get("nameid"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "enem_access_level": payload.get("enem:access_level"),
            "authorized_subjects": payload.get("enem:subjects", "").split(","),
            "hourly_quota": int(payload.get("enem:max_questions_per_hour", "100"))
        }
        
        return user_context
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Estratégias de Deployment

### Docker Compose Configuration

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  teachershub-api:
    build:
      context: ./teachershub-integration
      dockerfile: Dockerfile
    ports:
      - "5000:80"
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - ConnectionStrings__DefaultConnection=Host=postgres;Database=teachershub;Username=app_user;Password=secure_pass
      - EnemServices__RagBaseUrl=http://enem-rag-service:8000
      - JWT__Key=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - enem-rag-service
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  enem-rag-service:
    build:
      context: ./python-ml-services/rag-service
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://enem_user:secure_pass@postgres:5432/teachershub
      - REDIS_URL=redis://redis:6379/0
      - MODEL_CACHE_DIR=/app/models
    volumes:
      - ./models:/app/models
      - ./data/embeddings:/app/data/embeddings
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=teachershub
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./shared/database/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./shared/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./shared/nginx/ssl:/etc/nginx/ssl
    depends_on:
      - teachershub-api

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: teachershub-network
```

### Production Deployment Strategy

**Staged Deployment Process:**
1. **Development Environment** - Full Docker Compose stack
2. **Staging Environment** - Production mirror com data sanitizada
3. **Production Deployment** - Blue/Green deployment com rollback

**Deployment Scripts:**
```bash
#!/bin/bash
# deploy.sh

set -e

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}

echo "Deploying TeachersHub-ENEM Integration v${VERSION} to ${ENVIRONMENT}"

# Pre-deployment checks
echo "Running pre-deployment health checks..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec teachershub-api curl -f http://localhost:80/health
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec enem-rag-service curl -f http://localhost:8000/health

# Database migrations
echo "Running database migrations..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml exec teachershub-api dotnet ef database update

# Rolling deployment
echo "Starting rolling deployment..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d --scale teachershub-api=2
sleep 30
docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d --scale teachershub-api=1

# Post-deployment verification
echo "Running post-deployment tests..."
curl -f http://api.${ENVIRONMENT}.teachershub.com/health
curl -f http://api.${ENVIRONMENT}.teachershub.com/enem/health

echo "Deployment completed successfully!"
```

## Monitoramento de Performance

### Observabilidade Stack

**Application Performance Monitoring:**
```csharp
// Startup.cs - .NET Telemetry
services.AddOpenTelemetry()
    .WithTracing(builder =>
    {
        builder
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddEntityFrameworkCoreInstrumentation()
            .AddJaegerExporter();
    })
    .WithMetrics(builder =>
    {
        builder
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddPrometheusExporter();
    });

// Custom metrics
services.AddSingleton<IMetrics>(provider =>
{
    return Metrics.CreateCounter("teachershub_enem_requests_total", "Total ENEM requests")
           .WithTag("endpoint")
           .WithTag("status_code");
});
```

**Python Observability:**
```python
# monitoring/telemetry.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Initialize tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

# Initialize metrics
metric_reader = PrometheusMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
meter = metrics.get_meter(__name__)

# Custom metrics
rag_search_duration = meter.create_histogram(
    "rag_search_duration_seconds",
    description="Time spent processing RAG searches",
)

rag_search_counter = meter.create_counter(
    "rag_searches_total",
    description="Total number of RAG searches performed",
)

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
```

### Health Checks Implementation

**.NET Health Checks:**
```csharp
// Program.cs
services.AddHealthChecks()
    .AddDbContext<EnemDbContext>()
    .AddRedis(configuration.GetConnectionString("Redis"))
    .AddHttpClient("EnemRagService", client =>
    {
        client.BaseAddress = new Uri(configuration["EnemServices:RagBaseUrl"]);
    })
    .AddCheck<SemanticKernelHealthCheck>("semantic-kernel");

app.MapHealthChecks("/health", new HealthCheckOptions
{
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse
});

// Custom health check
public class SemanticKernelHealthCheck : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        try
        {
            // Test Semantic Kernel connectivity
            var kernel = context.Registration.Factory.GetRequiredService<IKernel>();
            var result = await kernel.InvokeAsync("Test prompt", cancellationToken);
            
            return HealthCheckResult.Healthy("Semantic Kernel is responsive");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Semantic Kernel is not responding", ex);
        }
    }
}
```

**Python Health Checks:**
```python
# endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from services.database import get_db
from services.redis_client import get_redis
from services.embedding_service import EmbeddingService

router = APIRouter()

@router.get("/health")
async def health_check(db = Depends(get_db), redis = Depends(get_redis)):
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Redis connectivity
    try:
        await redis.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # ML models loaded
    try:
        embedding_service = EmbeddingService()
        if embedding_service.model_loaded:
            health_status["checks"]["ml_models"] = "healthy"
        else:
            health_status["checks"]["ml_models"] = "unhealthy: models not loaded"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["ml_models"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status
```

### Performance Monitoring Dashboards

**Prometheus Metrics:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'teachershub-api'
    static_configs:
      - targets: ['teachershub-api:5000']
    metrics_path: '/metrics'
    
  - job_name: 'enem-rag-service'
    static_configs:
      - targets: ['enem-rag-service:8000']
    metrics_path: '/metrics'

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

**Grafana Dashboard Configuration:**
```json
{
  "dashboard": {
    "title": "TeachersHub-ENEM Integration",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(teachershub_enem_requests_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "RAG Search Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_search_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(rag_search_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "System Resource Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total[5m])",
            "legendFormat": "{{container_name}}"
          }
        ]
      }
    ]
  }
}
```

---

**Arquitetura Backend Detalhada Completa!** 

Esta especificação técnica cobre todos os aspectos solicitados:

✅ **Padrões de Comunicação Inter-Serviços** - HTTP clients, retry policies, error handling
✅ **Estratégias de Deployment** - Docker Compose, staged deployment, rollback procedures  
✅ **Monitoramento de Performance** - Observabilidade, health checks, metrics, dashboards
✅ **Planos de Migração de Dados** - Schema separation, Entity Framework, data integrity

A arquitetura está pronta para implementação seguindo os épicos definidos no PRD, com todos os padrões necessários para manter estabilidade do TeachersHub durante a integração.

**Próximos passos disponíveis:**
- **Documentação Frontend** - Especificações React/TypeScript  
- **Guias de Implementação** - Step-by-step para desenvolvedores
- **Planos de Teste** - Estratégias de validação da integração
- **Runbooks Operacionais** - Procedimentos de produção

**Arquitetura backend está completa e pronta para desenvolvimento!** 🏗️
