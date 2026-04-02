# Story EQ-003: Melhorar Parsing de Alternativas

## 📋 Resumo

**Como** desenvolvedor do sistema ENEM RAG,  
**Eu quero** melhorar o algoritmo de parsing de alternativas,  
**Para que** 95%+ das questões tenham todas as 5 alternativas (A, B, C, D, E) corretamente extraídas.

---

## 📊 Informações da Story

| Campo | Valor |
|-------|-------|
| **Story ID** | EQ-003 |
| **Epic** | EQ-001 - Melhoria da Qualidade de Extração |
| **Prioridade** | Alta |
| **Estimativa** | 8 Story Points |
| **Sprint** | 1 |
| **Assignee** | Backend Developer |

---

## 🎯 Objetivo

Aumentar a taxa de sucesso de parsing de alternativas de ~85% para 95%+, implementando:

1. **Múltiplos padrões** regex para captura robusta
2. **Context awareness** para diferentes layouts
3. **Validação inteligente** de alternativas encontradas
4. **Recovery mechanisms** para casos edge

---

## 🔍 Contexto Técnico

### Problemas Identificados:

**Atual**: Método `_extract_alternatives()` em `parser.py`
```python
# Problemas do algoritmo atual:
1. Regex simples demais - não captura variações
2. Quebras de linha entre alternativas não tratadas
3. Alternativas em colunas/layouts complexos
4. Texto de alternativa muito curto ou longo ignorado
5. Ordenação alfabética assumida incorretamente
```

### Análise de Falhas Atuais:
```
Tipos de Erro Encontrados:
- Question 43: Expected 5 alternatives, found 3 
- Question 82: Found only 1 alternatives. Skipping question.
- Question 89: Alternatives not in alphabetical order: ['A', 'B', 'E', 'D', 'E']

Padrões Problemáticos:
- Alternativas com quebras de linha: "A) Texto\nlongo\naqui"
- Layout em colunas: "A) ... | B) ..."  
- Espaçamento inconsistente: "A)texto" vs "A) texto"
- Alternativas com sub-itens: "A) 1. item 2. item"
```

### Solução Proposta:

**Nova implementação**: Sistema de múltiplas estratégias
1. **Strategy Pattern**: Múltiplos algoritmos de parsing
2. **Confidence Scoring**: Avaliar qual estratégia funcionou melhor
3. **Fallback Chain**: Se uma falha, tentar próxima
4. **Context Detection**: Identificar layout da página

---

## 🛠️ Implementação Técnica

### Arquitetura do Componente:

```python
class AlternativeExtractor:
    """Extrator robusto de alternativas com múltiplas estratégias."""
    
    def __init__(self):
        self.strategies = [
            StandardPatternStrategy(),
            MultilinePatternStrategy(), 
            ColumnAwareStrategy(),
            ContextualStrategy()
        ]
    
    def extract_alternatives(self, question_text: str) -> ExtractedAlternatives:
        """Extrai alternativas usando melhor estratégia disponível."""
        best_result = None
        best_confidence = 0.0
        
        for strategy in self.strategies:
            result = strategy.extract(question_text)
            if result.confidence > best_confidence:
                best_result = result
                best_confidence = result.confidence
        
        return best_result


@dataclass
class ExtractedAlternatives:
    """Resultado da extração com métricas de qualidade."""
    alternatives: List[str]  # Lista das alternativas A-E
    confidence: float       # 0.0-1.0 confiança no resultado
    strategy_used: str      # Qual estratégia funcionou
    issues: List[str]       # Problemas encontrados
    raw_matches: List[Tuple] # Dados brutos para debug
```

### Estratégias de Parsing:

#### 1. Standard Pattern Strategy:
```python
class StandardPatternStrategy:
    """Padrão atual melhorado."""
    
    def extract(self, text: str) -> ExtractedAlternatives:
        # Padrões robustos para A) B) C) D) E)
        patterns = [
            r'([A-E])\)\s*([^A-E]+?)(?=[A-E]\)|QUESTÃO|$)',
            r'([A-E])\s+([a-z][^A-E]+?)(?=[A-E]\s+[a-z]|$)',
            r'\b([A-E])\b\s*[-–]?\s*(.+?)(?=\b[A-E]\b|$)'
        ]
        # Implementação...
```

#### 2. Multiline Pattern Strategy:
```python  
class MultilinePatternStrategy:
    """Para alternativas que quebram linhas."""
    
    def extract(self, text: str) -> ExtractedAlternatives:
        # Tratar alternativas multi-linha
        # "A) Primeira linha\n   Segunda linha\n   B) Nova alternativa"
        # Implementação...
```

#### 3. Column Aware Strategy:
```python
class ColumnAwareStrategy:
    """Para layouts em colunas."""
    
    def extract(self, text: str) -> ExtractedAlternatives:
        # Detectar layout em colunas e ajustar parsing
        # Usar coordenadas bbox se disponível
        # Implementação...
```

### Integração com Parser Atual:

```python
class EnemPDFParser:
    def __init__(self):
        self.alternative_extractor = AlternativeExtractor()
    
    def _extract_alternatives(self, question_text: str) -> List[str]:
        """Método refatorado."""
        result = self.alternative_extractor.extract_alternatives(question_text)
        
        # Log para observabilidade
        if result.confidence < 0.8:
            logger.warning(f"Low confidence alternative extraction: {result.confidence}")
        
        # Validação adicional
        if len(result.alternatives) != 5:
            logger.warning(f"Expected 5 alternatives, got {len(result.alternatives)}")
        
        return result.alternatives
```

---

## ✅ Critérios de Aceite

### Funcionais:

1. **Taxa de Sucesso Melhorada**:
   - [ ] 95%+ questões com exatamente 5 alternativas extraídas
   - [ ] Redução de questões "skipped" de 15% para <5%
   - [ ] Melhoria demonstrável em amostra de 500 questões

2. **Qualidade das Alternativas**:
   - [ ] Alternativas têm comprimento mínimo razoável (>10 chars)
   - [ ] Ordem alfabética correta (A, B, C, D, E)
   - [ ] Texto limpo sem artifacts (códigos, quebras estranhas)

3. **Robustez**:
   - [ ] Sistema funciona com diferentes layouts de PDF
   - [ ] Graceful degradation quando parsing falha
   - [ ] Múltiplas estratégias implementadas e testadas

### Técnicos:

4. **Performance**:
   - [ ] Tempo de parsing por questão não aumenta >30%
   - [ ] Memory footprint controlado para processamento em lote
   - [ ] Algoritmo escalável para volume de produção

5. **Observabilidade**:
   - [ ] Métricas de confiança por estratégia logadas
   - [ ] Dashboard de qualidade para monitoramento
   - [ ] Alertas quando confidence score < threshold

6. **Testabilidade**:
   - [ ] Testes unitários para cada estratégia
   - [ ] Testes de regressão com questões problemáticas conhecidas
   - [ ] Testes de performance com volume real

---

## 🧪 Casos de Teste

### Cenário 1: Alternativas Padrão
```python
def test_standard_alternatives_parsing():
    text = """
    Questão sobre matemática.
    
    A) Primeira alternativa correta
    B) Segunda alternativa incorreta  
    C) Terceira alternativa plausível
    D) Quarta alternativa distrator
    E) Quinta alternativa incorreta
    """
    
    extractor = AlternativeExtractor()
    result = extractor.extract_alternatives(text)
    
    assert len(result.alternatives) == 5
    assert result.alternatives[0].startswith("A)")
    assert result.confidence > 0.9
```

### Cenário 2: Alternativas Multi-linha
```python
def test_multiline_alternatives():
    text = """
    A) Este é um texto longo que
       quebra em várias linhas
       e tem conteúdo complexo
    
    B) Esta é outra alternativa
       também em múltiplas linhas
    """
    
    extractor = AlternativeExtractor()
    result = extractor.extract_alternatives(text)
    
    # Deve capturar texto completo
    assert "quebra em várias linhas" in result.alternatives[0]
    assert "também em múltiplas linhas" in result.alternatives[1]
```

### Cenário 3: Layout em Colunas
```python  
def test_column_layout_parsing():
    text = """
    A) Alt 1    |    D) Alt 4
    B) Alt 2    |    E) Alt 5  
    C) Alt 3    |
    """
    
    extractor = AlternativeExtractor()  
    result = extractor.extract_alternatives(text)
    
    assert len(result.alternatives) == 5
    assert result.strategy_used == "ColumnAwareStrategy"
```

### Cenário 4: Casos Edge - Recuperação
```python
def test_edge_case_recovery():
    # Texto mal formatado
    text = "A)Sem espaço B)  Espaço duplo C) Normal D)Problema E) Ok"
    
    extractor = AlternativeExtractor()
    result = extractor.extract_alternatives(text)
    
    # Deve conseguir extrair mesmo com formatação ruim
    assert len(result.alternatives) == 5
    assert result.confidence > 0.7  # Menor que ideal, mas aceitável
```

### Cenário 5: Performance - Volume Real
```python
def test_parsing_performance():
    # Carregar questões reais problemáticas
    problematic_questions = load_failed_parsing_cases()
    
    extractor = AlternativeExtractor()
    
    start_time = time.time()
    results = []
    
    for question_text in problematic_questions:
        result = extractor.extract_alternatives(question_text)
        results.append(result)
    
    end_time = time.time()
    
    # Performance aceitável
    avg_time_per_question = (end_time - start_time) / len(problematic_questions)
    assert avg_time_per_question < 0.1  # 100ms por questão max
    
    # Taxa de sucesso melhorada
    successful_extractions = sum(1 for r in results if len(r.alternatives) == 5)
    success_rate = successful_extractions / len(results)
    assert success_rate > 0.95  # 95% success rate
```

---

## 📂 Arquivos Afetados

### Novos Arquivos:
- `src/enem_ingestion/alternative_extractor.py` - Nova implementação
- `src/enem_ingestion/parsing_strategies.py` - Estratégias específicas  
- `tests/test_alternative_extractor.py` - Testes unitários
- `tests/test_parsing_strategies.py` - Testes das estratégias

### Arquivos Modificados:
- `src/enem_ingestion/parser.py` - Integração do novo extrator
- `scripts/analyze_parsing_quality.py` - Script de análise atualizado

### Dados de Teste:
- `tests/data/problematic_questions.json` - Casos edge conhecidos
- `tests/data/parsing_benchmarks.json` - Benchmarks de performance

---

## 🔗 Dependências

### Técnicas:
- **EQ-002**: Text normalizer (texto limpo facilita parsing)
- **Regex avançado**: Padrões complexos para diferentes layouts
- **Logging estruturado**: Para observabilidade

### Stories:
- **Dependente de**: EQ-002 (texto normalizado)
- **Bloqueia**: EQ-004 (validação de qualidade)

---

## 📊 Métricas de Sucesso

### Baseline Atual (Antes):
```
Taxa de Sucesso: ~85%
Questões Skipped: ~15% 
Tempo Médio: X ms/questão
Casos Edge Tratados: Poucos
```

### Meta Pós-Implementação:
```
Taxa de Sucesso: >95%
Questões Skipped: <5%
Tempo Médio: <1.3x tempo atual
Casos Edge Tratados: Múltiplas estratégias
Confidence Score: >0.8 para 90% dos casos
```

### KPIs de Monitoramento:
- **Success Rate Daily**: % questões com 5 alternativas
- **Strategy Usage**: Qual estratégia mais usada
- **Confidence Distribution**: Histograma de scores
- **Performance**: Tempo médio de parsing

---

## 📝 Notas de Implementação

### Fase 1: Estratégias Básicas
1. Implementar `StandardPatternStrategy` melhorada
2. Adicionar `MultilinePatternStrategy`
3. Sistema de confidence scoring

### Fase 2: Estratégias Avançadas  
1. `ColumnAwareStrategy` com análise de layout
2. `ContextualStrategy` usando coordenadas
3. Machine learning para padrão recognition (futuro)

### Considerações Especiais:
- **Preserve compatibility**: Sistema atual deve funcionar como fallback
- **Gradual rollout**: Feature flag para habilitar nova implementação
- **Rich logging**: Capturar dados para análise e melhoria contínua

---

## 🚀 Plano de Deploy

### Desenvolvimento:
1. **TDD**: Implementar testes primeiro com casos conhecidos
2. **Benchmark**: Medir performance atual como baseline
3. **Iterative**: Implementar uma estratégia por vez

### Testing:
1. **Unit tests**: Cada estratégia isoladamente
2. **Integration**: Com parser completo
3. **Performance**: Stress test com volume real
4. **Regression**: Garantir que casos funcionando continuem

### Produção:
1. **Feature flag**: Controle de rollout gradual
2. **Monitoring**: Dashboards de sucesso/falha
3. **Rollback**: Plano para reverter se necessário

---

**Criado em**: 12/10/2025  
**Status**: Ready for Development  
**Reviewers**: [@architect, @backend-lead]  
**Dependencies**: EQ-002 (recomendado, não bloqueante)