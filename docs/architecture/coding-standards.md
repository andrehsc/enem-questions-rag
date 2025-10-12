# Padrões de Codificação - ENEM Questions RAG

## Princípios Fundamentais

### SOLID

#### Single Responsibility Principle (SRP)
- **Regra**: Cada classe deve ter apenas uma razão para mudar
- **Aplicação**: 
  - `DatabaseService` responsável apenas por operações de banco
  - `Question` model responsável apenas por representar questões
  - Controllers FastAPI responsáveis apenas por HTTP handling

```python
# ✅ BOM: Responsabilidade única
class QuestionRepository:
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        pass
    
    def get_questions_by_filters(self, filters: dict) -> List[Question]:
        pass

# ❌ RUIM: Múltiplas responsabilidades
class QuestionService:
    def get_question(self, id): pass
    def format_html_response(self, question): pass  # Responsabilidade de apresentação
    def send_email_notification(self, question): pass  # Responsabilidade de notificação
```

#### Open/Closed Principle (OCP)
- **Regra**: Aberto para extensão, fechado para modificação
- **Aplicação**: Use abstrações e interfaces para permitir extensibilidade

```python
# ✅ BOM: Extensível através de herança
from abc import ABC, abstractmethod

class QuestionProcessor(ABC):
    @abstractmethod
    def process(self, question: Question) -> ProcessedQuestion:
        pass

class ENEMQuestionProcessor(QuestionProcessor):
    def process(self, question: Question) -> ProcessedQuestion:
        # Implementação específica para ENEM
        pass
```

#### Liskov Substitution Principle (LSP)
- **Regra**: Objetos de uma superclasse devem ser substituíveis por objetos de suas subclasses
- **Aplicação**: Subclasses devem manter o contrato da classe pai

#### Interface Segregation Principle (ISP)
- **Regra**: Clientes não devem depender de interfaces que não usam
- **Aplicação**: Interfaces específicas e coesas

```python
# ✅ BOM: Interfaces específicas
class Readable(Protocol):
    def read(self) -> str: pass

class Writable(Protocol):
    def write(self, data: str) -> None: pass

# ❌ RUIM: Interface gorda
class FileHandler(Protocol):
    def read(self) -> str: pass
    def write(self, data: str) -> None: pass
    def compress(self) -> None: pass  # Nem todos precisam
    def encrypt(self) -> None: pass   # Nem todos precisam
```

#### Dependency Inversion Principle (DIP)
- **Regra**: Dependa de abstrações, não de concretizações
- **Aplicação**: Use injeção de dependência

```python
# ✅ BOM: Depende de abstração
class QuestionService:
    def __init__(self, repository: QuestionRepository):
        self._repository = repository
    
    def get_question(self, question_id: str) -> Question:
        return self._repository.get_by_id(question_id)

# ❌ RUIM: Depende de implementação concreta
class QuestionService:
    def __init__(self):
        self._db = PostgreSQLDatabase()  # Acoplamento rígido
```

### DRY (Don't Repeat Yourself)

- **Regra**: Cada pedaço de conhecimento deve ter uma representação única
- **Aplicação**: Extrair lógica comum em funções/classes reutilizáveis

```python
# ✅ BOM: Lógica de validação centralizada
class QuestionValidator:
    @staticmethod
    def validate_question_id(question_id: str) -> bool:
        return bool(question_id and len(question_id) == 36)

# ❌ RUIM: Validação duplicada
def get_question(question_id: str):
    if not question_id or len(question_id) != 36:  # Duplicação
        raise ValueError("Invalid ID")

def update_question(question_id: str):
    if not question_id or len(question_id) != 36:  # Duplicação
        raise ValueError("Invalid ID")
```

### DIR (Duplication Improves Readability)

- **Regra**: Em casos específicos, duplicação controlada pode melhorar a legibilidade
- **Aplicação**: Balance DRY com clareza quando abstração prejudicaria a compreensão

```python
# ✅ BOM: Duplicação que melhora legibilidade
def validate_enem_question_format(question_text: str) -> bool:
    if not question_text:
        return False
    if len(question_text) < 10:
        return False
    return True

def validate_enem_alternative_format(alternative_text: str) -> bool:
    if not alternative_text:
        return False
    if len(alternative_text) < 5:
        return False
    return True

# ❌ RUIM: Over-abstração que prejudica clareza
def validate_text_format(text: str, min_length: int, context: str) -> bool:
    """Abstração genérica que obscurece a intenção específica"""
    if not text:
        return False
    if len(text) < min_length:
        return False
    return True
```

**Casos onde DIR é apropriado**:
- **Configurações específicas por contexto**: Diferentes validações para diferentes domínios
- **Logs contextuais**: Mensagens específicas são mais úteis que genéricas
- **Testes**: Cenários específicos são mais claros que helpers genéricos
- **Constants locais**: Valores específicos do contexto vs constantes globais

```python
# ✅ BOM: Constants específicas melhoram contexto
class QuestionLimits:
    MAX_QUESTION_LENGTH = 5000
    MIN_QUESTION_LENGTH = 10

class AlternativeLimits:
    MAX_ALTERNATIVE_LENGTH = 500
    MIN_ALTERNATIVE_LENGTH = 1

# Versus abstração que pode confundir:
# GENERIC_TEXT_LIMITS = {"question": (10, 5000), "alternative": (1, 500)}
```

### KISS (Keep It Simple, Stupid)

- **Regra**: Soluções simples são preferíveis
- **Aplicação**: Evitar over-engineering

```python
# ✅ BOM: Simples e direto
def calculate_score(correct_answers: int, total_questions: int) -> float:
    return (correct_answers / total_questions) * 100

# ❌ RUIM: Over-engineered
class AdvancedScoreCalculationEngineFactory:
    def create_calculator(self) -> IScoreCalculator:
        return StandardScoreCalculatorImplementation()
```

### YAGNI (You Aren't Gonna Need It)

- **Regra**: Não implemente funcionalidades que não são necessárias agora
- **Aplicação**: Desenvolva apenas o que é requerido

### Clean Architecture

#### Camadas Definidas
1. **Domain/Entities**: Modelos de negócio (`Question`, `ExamMetadata`)
2. **Use Cases/Services**: Lógica de aplicação (`QuestionService`)
3. **Interface Adapters**: Controllers, Repositories
4. **Infrastructure**: Database, External APIs

```
┌─────────────────┐
│   Controllers   │ ← Interface Layer
├─────────────────┤
│    Services     │ ← Application Layer  
├─────────────────┤
│   Repositories  │ ← Domain Layer
├─────────────────┤
│    Database     │ ← Infrastructure Layer
└─────────────────┘
```

### Alta Coesão

- **Regra**: Elementos de um módulo devem trabalhar juntos para um objetivo comum
- **Aplicação**: Agrupe funcionalidades relacionadas

```python
# ✅ BOM: Alta coesão - todas as operações relacionadas a questões
class QuestionService:
    def get_question(self, id: str) -> Question: pass
    def search_questions(self, query: str) -> List[Question]: pass
    def validate_question(self, question: Question) -> bool: pass

# ❌ RUIM: Baixa coesão - responsabilidades não relacionadas
class MixedService:
    def get_question(self, id: str) -> Question: pass
    def send_email(self, to: str, body: str) -> None: pass  # Não relacionado
    def log_activity(self, message: str) -> None: pass      # Não relacionado
```

### Baixo Acoplamento

- **Regra**: Minimize dependências entre módulos
- **Aplicação**: Use interfaces, injeção de dependência, eventos

```python
# ✅ BOM: Baixo acoplamento via interface
class QuestionService:
    def __init__(self, repository: QuestionRepositoryInterface):
        self._repository = repository

# ❌ RUIM: Alto acoplamento direto
class QuestionService:
    def __init__(self):
        self._db = PostgreSQLConnection()  # Acoplamento direto
        self._cache = RedisCache()         # Acoplamento direto
```

## Padrões de Nomenclatura

### Python
- **Classes**: PascalCase (`QuestionService`, `DatabaseConnection`)
- **Funções/Métodos**: snake_case (`get_question_by_id`, `validate_input`)
- **Variáveis**: snake_case (`question_id`, `total_count`)
- **Constantes**: UPPER_SNAKE_CASE (`MAX_QUESTIONS_PER_PAGE`, `DEFAULT_TIMEOUT`)
- **Módulos**: snake_case (`question_service.py`, `database_models.py`)

### SQL
- **Tabelas**: snake_case (`enem_questions`, `exam_metadata`)
- **Colunas**: snake_case (`question_id`, `created_at`)
- **Índices**: `idx_table_column` (`idx_questions_year`, `idx_metadata_subject`)

### REST API
- **Endpoints**: kebab-case (`/questions`, `/exam-metadata`)
- **Query Parameters**: snake_case (`page_size`, `sort_by`)

## Tratamento de Erros

### Hierarquia de Exceções
```python
class EnemRagException(Exception):
    """Exceção base do sistema"""
    pass

class ValidationError(EnemRagException):
    """Erro de validação de dados"""
    pass

class NotFoundError(EnemRagException):
    """Recurso não encontrado"""
    pass

class DatabaseError(EnemRagException):
    """Erro de banco de dados"""
    pass
```

### Padrão de Tratamento
```python
# ✅ BOM: Tratamento específico e logging
async def get_question(question_id: str) -> Question:
    try:
        if not QuestionValidator.validate_id(question_id):
            raise ValidationError(f"Invalid question ID: {question_id}")
        
        question = await repository.get_by_id(question_id)
        if not question:
            raise NotFoundError(f"Question not found: {question_id}")
        
        return question
    
    except ValidationError:
        logger.warning(f"Validation failed for question ID: {question_id}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting question {question_id}: {str(e)}")
        raise DatabaseError("Failed to retrieve question")
```

## Documentação de Código

### Docstrings
```python
def get_questions_by_filters(
    self, 
    year: Optional[int] = None,
    subject: Optional[str] = None,
    page: int = 1,
    size: int = 20
) -> Tuple[List[Question], int]:
    """
    Recupera questões aplicando filtros opcionais.
    
    Args:
        year: Ano do exame para filtrar (opcional)
        subject: Matéria para filtrar (opcional) 
        page: Número da página (default: 1)
        size: Itens por página (default: 20)
        
    Returns:
        Tuple contendo lista de questões e total de registros
        
    Raises:
        ValidationError: Se os parâmetros forem inválidos
        DatabaseError: Se houver erro na consulta
        
    Example:
        questions, total = service.get_questions_by_filters(
            year=2024, 
            subject="MATEMATICA",
            page=1,
            size=10
        )
    """
```

## Testes

### Estrutura de Testes
- **Unit Tests**: Testam componentes isolados
- **Integration Tests**: Testam integração entre componentes
- **E2E Tests**: Testam fluxos completos

### Convenções
```python
# Nomenclatura: test_<method>_<scenario>_<expected_result>
def test_get_question_by_id_valid_id_returns_question():
    pass

def test_get_question_by_id_invalid_id_raises_validation_error():
    pass

def test_get_question_by_id_not_found_raises_not_found_error():
    pass
```

## Logging

### Configuração
```python
import logging

# Configuração centralizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### Uso
```python
# Níveis apropriados
logger.debug("Detailed debugging information")
logger.info("General information about program execution")
logger.warning("Warning about potential issues")
logger.error("Error occurred but program continues")
logger.critical("Critical error, program may terminate")
```

## Configuração e Environment

### Variáveis de Ambiente
```python
# ✅ BOM: Configuração centralizada
class Settings:
    DATABASE_URL: str = Field(env="DATABASE_URL")
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
```

## Performance

### Database
- Use índices apropriados
- Evite N+1 queries
- Use paginação
- Implemente cache quando apropriado

### API
- Use async/await para I/O
- Implemente rate limiting
- Use compressão de resposta
- Cache respostas quando possível

## Segurança

### Validação de Input
```python
from pydantic import BaseModel, validator

class QuestionFilter(BaseModel):
    year: Optional[int] = None
    subject: Optional[str] = None
    
    @validator('year')
    def validate_year(cls, v):
        if v is not None and (v < 2020 or v > 2030):
            raise ValueError('Year must be between 2020 and 2030')
        return v
```

### SQL Injection Prevention
- Use sempre queries parametrizadas
- Nunca concatene SQL com input do usuário
- Use ORM quando possível

## Code Review Checklist

- [ ] Código segue princípios SOLID
- [ ] Não há duplicação desnecessária (DRY)
- [ ] Solução é simples e direta (KISS)
- [ ] Não há over-engineering (YAGNI)
- [ ] Alta coesão dentro dos módulos
- [ ] Baixo acoplamento entre módulos
- [ ] Nomenclatura consistente
- [ ] Tratamento de erros apropriado
- [ ] Documentação adequada
- [ ] Testes cobrem cenários importantes
- [ ] Performance considerada
- [ ] Segurança validada
- [ ] Não há emojis em código fonte
- [ ] Encoding UTF-8 utilizado
