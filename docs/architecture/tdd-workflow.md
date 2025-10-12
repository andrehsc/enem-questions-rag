# TDD Workflow para Agentes Desenvolvedores

## Visão Geral

O Test-Driven Development (TDD) é uma metodologia de desenvolvimento que segue o ciclo **Red-Green-Blue** (Vermelho-Verde-Azul), garantindo código de alta qualidade, testável e bem estruturado.

## Ciclo TDD: Red-Green-Blue

```
��� RED     →    ��� GREEN    →    ��� BLUE
(Falha)         (Sucesso)        (Refactor)
   ↑               ↓               ↓
   ←───────────────←───────────────←
```

### ��� **FASE VERMELHA** (Red)
- **Objetivo**: Escrever um teste que falha
- **Mentalidade**: "O que eu quero que este código faça?"
- **Resultado**: Teste executado com falha (comportamento não implementado)

### ��� **FASE VERDE** (Green)
- **Objetivo**: Fazer o teste passar com o mínimo de código necessário
- **Mentalidade**: "Qual é a implementação mais simples que faz este teste passar?"
- **Resultado**: Teste executado com sucesso (funcionalidade básica funcionando)

### ��� **FASE AZUL** (Blue/Refactor)
- **Objetivo**: Melhorar a qualidade do código sem alterar comportamento
- **Mentalidade**: "Como posso tornar este código melhor mantendo os testes passando?"
- **Resultado**: Código limpo, otimizado e todos os testes ainda passando

## Fluxo Detalhado de TDD

### **Etapa 1: Criação de Interfaces**
**Objetivo**: Definir contratos e abstrações antes da implementação

```python
# 1. Definir interface/protocolo
from abc import ABC, abstractmethod
from typing import List, Optional

class QuestionRepositoryInterface(ABC):
    """Interface para repositório de questões"""
    
    @abstractmethod
    def get_by_id(self, question_id: str) -> Optional['Question']:
        """Recupera questão por ID"""
        pass
    
    @abstractmethod
    def get_by_filters(self, year: int = None, subject: str = None) -> List['Question']:
        """Recupera questões com filtros"""
        pass
    
    @abstractmethod
    def save(self, question: 'Question') -> bool:
        """Salva questão"""
        pass
```

### **Etapa 2: Criação do Componente Vazio**
**Objetivo**: Criar estrutura básica da classe sem implementação

```python
# 2. Criar classe vazia que implementa a interface
class QuestionRepository(QuestionRepositoryInterface):
    """Implementação concreta do repositório de questões"""
    
    def get_by_id(self, question_id: str) -> Optional['Question']:
        # TODO: Implementar via TDD
        raise NotImplementedError("Implementar via TDD")
    
    def get_by_filters(self, year: int = None, subject: str = None) -> List['Question']:
        # TODO: Implementar via TDD
        raise NotImplementedError("Implementar via TDD")
    
    def save(self, question: 'Question') -> bool:
        # TODO: Implementar via TDD
        raise NotImplementedError("Implementar via TDD")
```

### **Etapa 3: Adição de Imports, Construtores e Dependências**
**Objetivo**: Configurar dependências e estrutura necessária

```python
# 3. Adicionar imports e dependências
from typing import List, Optional, Dict
import uuid
from dataclasses import dataclass
from database import DatabaseConnection

@dataclass
class Question:
    """Modelo de questão"""
    id: str
    text: str
    subject: str
    year: int

class QuestionRepository(QuestionRepositoryInterface):
    """Repositório de questões com dependências configuradas"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self._db = db_connection
        self._questions: Dict[str, Question] = {}  # Cache temporário para TDD
    
    def get_by_id(self, question_id: str) -> Optional[Question]:
        raise NotImplementedError("Implementar via TDD")
    
    # ... outros métodos
```

### **Etapa 4: Implementação de Classe de Teste**
**Objetivo**: Criar estrutura de testes com fixtures e setup

```python
# 4. Criar classe de teste
import pytest
from unittest.mock import Mock, MagicMock
from question_repository import QuestionRepository, Question

class TestQuestionRepository:
    """Testes para QuestionRepository seguindo TDD"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock da conexão de banco para testes"""
        return Mock()
    
    @pytest.fixture
    def repository(self, mock_db_connection):
        """Instância do repositório para testes"""
        return QuestionRepository(mock_db_connection)
    
    @pytest.fixture
    def sample_question(self):
        """Questão de exemplo para testes"""
        return Question(
            id="123e4567-e89b-12d3-a456-426614174000",
            text="Qual é a capital do Brasil?",
            subject="GEOGRAFIA",
            year=2024
        )
```

### **Etapa 5: ��� FASE VERMELHA - Teste Quebrado com Comportamento Esperado**
**Objetivo**: Escrever teste que define o comportamento desejado (e falha)

```python
# 5. ��� RED: Escrever teste que falha
def test_get_by_id_existing_question_returns_question(self, repository, sample_question):
    """
    ��� RED: Teste que define comportamento esperado
    DEVE falhar inicialmente pois não há implementação
    """
    # Arrange
    question_id = sample_question.id
    # Simular que questão existe no "banco"
    repository._questions[question_id] = sample_question
    
    # Act
    result = repository.get_by_id(question_id)
    
    # Assert
    assert result is not None
    assert result.id == question_id
    assert result.text == sample_question.text
    assert result.subject == sample_question.subject
    assert result.year == sample_question.year

def test_get_by_id_nonexistent_question_returns_none(self, repository):
    """
    ��� RED: Teste para caso de questão não encontrada
    """
    # Arrange
    nonexistent_id = "999e9999-e99b-99d9-a999-999999999999"
    
    # Act
    result = repository.get_by_id(nonexistent_id)
    
    # Assert
    assert result is None
```

### **Etapa 6: Execução do Teste Quebrado**
**Objetivo**: Confirmar que teste falha conforme esperado

```bash
# 6. Executar teste e verificar falha
pytest tests/test_question_repository.py::TestQuestionRepository::test_get_by_id_existing_question_returns_question -v

# Resultado esperado:
# FAILED - NotImplementedError: Implementar via TDD
# ✅ Teste falha conforme esperado (RED phase)
```

### **Etapa 7: ��� FASE VERDE - Implementação Mínima**
**Objetivo**: Implementar o mínimo necessário para fazer o teste passar

```python
# 7. ��� GREEN: Implementação mínima que faz o teste passar
def get_by_id(self, question_id: str) -> Optional[Question]:
    """
    ��� GREEN: Implementação mínima para fazer teste passar
    """
    # Implementação mais simples possível
    if question_id in self._questions:
        return self._questions[question_id]
    return None
```

### **Etapa 8: Execução do Teste**
**Objetivo**: Verificar que teste agora passa

```bash
# 8. Executar teste e verificar sucesso
pytest tests/test_question_repository.py::TestQuestionRepository::test_get_by_id_existing_question_returns_question -v

# Resultado esperado:
# PASSED ✅
# ✅ Teste passa (GREEN phase alcançada)
```

### **Etapa 9: Iteração - Repetir Etapas 7 e 8**
**Objetivo**: Adicionar mais comportamentos seguindo Red-Green

```python
# 9. Adicionar mais testes (RED) e implementações (GREEN)

# ��� RED: Novo teste para filtros
def test_get_by_filters_by_year_returns_matching_questions(self, repository):
    """��� RED: Teste para filtro por ano"""
    # Arrange
    questions_2024 = [
        Question("1", "Questão 1", "MATH", 2024),
        Question("2", "Questão 2", "GEOG", 2024)
    ]
    questions_2023 = [
        Question("3", "Questão 3", "HIST", 2023)
    ]
    
    for q in questions_2024 + questions_2023:
        repository._questions[q.id] = q
    
    # Act
    result = repository.get_by_filters(year=2024)
    
    # Assert
    assert len(result) == 2
    assert all(q.year == 2024 for q in result)

# ��� GREEN: Implementação mínima
def get_by_filters(self, year: int = None, subject: str = None) -> List[Question]:
    """��� GREEN: Implementação para filtros"""
    questions = list(self._questions.values())
    
    if year is not None:
        questions = [q for q in questions if q.year == year]
    
    if subject is not None:
        questions = [q for q in questions if q.subject == subject]
    
    return questions
```

### **Etapa 10: ��� FASE AZUL - Refactoring**
**Objetivo**: Melhorar qualidade do código mantendo testes passando

```python
# 10. ��� BLUE: Refactoring para melhorar qualidade
class QuestionRepository(QuestionRepositoryInterface):
    """Repositório refatorado com melhor estrutura"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self._db = db_connection
        self._questions: Dict[str, Question] = {}
    
    def get_by_id(self, question_id: str) -> Optional[Question]:
        """
        ��� BLUE: Versão refatorada com validação e logging
        """
        if not self._is_valid_uuid(question_id):
            return None
            
        question = self._questions.get(question_id)
        if question:
            self._log_access(question_id)
        return question
    
    def get_by_filters(self, year: int = None, subject: str = None) -> List[Question]:
        """
        ��� BLUE: Versão refatorada com validação e otimização
        """
        filters = self._build_filters(year=year, subject=subject)
        return self._apply_filters(list(self._questions.values()), filters)
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Helper para validação de UUID"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    def _build_filters(self, **kwargs) -> Dict:
        """Helper para construir filtros dinâmicos"""
        return {k: v for k, v in kwargs.items() if v is not None}
    
    def _apply_filters(self, questions: List[Question], filters: Dict) -> List[Question]:
        """Helper para aplicar filtros de forma otimizada"""
        for filter_name, filter_value in filters.items():
            questions = [q for q in questions if getattr(q, filter_name) == filter_value]
        return questions
    
    def _log_access(self, question_id: str) -> None:
        """Helper para logging de acesso"""
        # Implementar logging se necessário
        pass
```

### **Etapa 11: Re-execução de Testes Após Refactoring**
**Objetivo**: Garantir que refactoring não quebrou funcionalidade

```bash
# 11. Executar todos os testes após refactoring
pytest tests/test_question_repository.py -v --cov=question_repository

# Resultado esperado:
# test_get_by_id_existing_question_returns_question PASSED ✅
# test_get_by_id_nonexistent_question_returns_none PASSED ✅
# test_get_by_filters_by_year_returns_matching_questions PASSED ✅
# Coverage: 95%+ ✅
```

## Guidelines para Agentes TDD

### **��� Instruções para Agentes Desenvolvedores**

#### **SEMPRE iniciar com:**
1. **Interface First**: Defina contratos antes de implementar
2. **Empty Implementation**: Crie estrutura vazia com NotImplementedError
3. **Test Setup**: Configure fixtures e mocks necessários

#### **Para cada funcionalidade, SIGA o ciclo:**

```
��� RED PHASE:
- Escreva teste que define comportamento desejado
- Execute teste e CONFIRME que falha
- Teste deve ser específico e focado em UM comportamento

��� GREEN PHASE:
- Implemente APENAS o mínimo para fazer teste passar
- Não optimize, não adicione funcionalidades extras
- Execute teste e CONFIRME que passa

��� BLUE PHASE:
- Refatore para melhorar qualidade (SOLID, DRY, etc)
- Extraia métodos, renomeie variáveis, otimize
- Execute TODOS os testes e CONFIRME que ainda passam
```

#### **Regras Obrigatórias:**
- **1 teste por comportamento**: Não misture múltiplas responsabilidades
- **Naming descritivo**: `test_method_scenario_expected_result`
- **AAA Pattern**: Arrange-Act-Assert sempre
- **Mock dependencies**: Isole unidade sob teste
- **Fast tests**: Testes devem executar rapidamente (<100ms cada)

#### **Red Phase Checklist:**
- [ ] Teste descreve comportamento específico
- [ ] Teste falha por razão correta (NotImplementedError ou assertion)
- [ ] Nome do teste é auto-explicativo
- [ ] Setup mínimo necessário (arrange)
- [ ] Uma única assertion (assert)

#### **Green Phase Checklist:**
- [ ] Implementação mais simples possível
- [ ] Teste passa completamente
- [ ] Não adiciona funcionalidades extras
- [ ] Não otimiza prematuramente
- [ ] Foca apenas em fazer o teste passar

#### **Blue Phase Checklist:**
- [ ] Código segue princípios SOLID
- [ ] Eliminação de duplicação (DRY)
- [ ] Nomes descritivos e claros
- [ ] Extraiu helpers/utilities quando apropriado
- [ ] TODOS os testes anteriores ainda passam
- [ ] Coverage mantido ou melhorado

### **Exemplo de Prompt para Agente:**

```
INSTRUÇÃO TDD PARA AGENTE:

Você irá implementar [FUNCIONALIDADE] seguindo rigorosamente o ciclo TDD Red-Green-Blue.

ETAPAS OBRIGATÓRIAS:
1. Criar interface [NOME_INTERFACE] com método [MÉTODO]
2. Criar classe vazia [NOME_CLASSE] implementando interface
3. Configurar dependências e imports
4. Criar classe de teste com fixtures
5. ��� RED: Escrever teste que falha para comportamento [COMPORTAMENTO_ESPECÍFICO]
6. Executar teste e CONFIRMAR falha
7. ��� GREEN: Implementar mínimo necessário para passar
8. Executar teste e CONFIRMAR sucesso
9. Repetir 5-8 para cada comportamento adicional
10. ��� BLUE: Refatorar mantendo testes passando
11. Executar TODOS os testes finais

VALIDAÇÕES OBRIGATÓRIAS:
- Cada teste deve ter nome descritivo: test_[method]_[scenario]_[expected]
- Use padrão AAA (Arrange-Act-Assert)
- Mock todas as dependências externas
- Confirme execução de cada fase antes de continuar
- Coverage deve ser >90%

NUNCA pule etapas. SEMPRE confirme execução de testes.
```

## Benefícios do TDD para Agentes

### **Qualidade Garantida:**
- Código testado desde o início
- Design emergente através dos testes
- Refactoring seguro com testes como rede de segurança

### **Desenvolvimento Focado:**
- Uma funcionalidade por vez
- Requisitos claros através dos testes
- Menos bugs em produção

### **Melhoria Contínua:**
- Código limpo através do refactoring
- Documentação viva através dos testes
- Confiança para mudanças futuras

O TDD é uma disciplina que garante código de alta qualidade, testável e maintível, essencial para agentes desenvolvedores criarem soluções robustas.
