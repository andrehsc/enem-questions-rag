# Story EQ-002: Implementar Normalizador de Texto

## 📋 Resumo

**Como** desenvolvedor do sistema ENEM RAG,  
**Eu quero** implementar um normalizador de texto robusto,  
**Para que** problemas de encoding (mojibake) sejam automaticamente corrigidos em todas as questões extraídas.

---

## 📊 Informações da Story

| Campo | Valor |
|-------|-------|
| **Story ID** | EQ-002 |
| **Epic** | EQ-001 - Melhoria da Qualidade de Extração |
| **Prioridade** | Alta |
| **Estimativa** | 5 Story Points |
| **Sprint** | 1 |
| **Assignee** | Backend Developer |

---

## 🎯 Objetivo

Eliminar 100% dos problemas de encoding mojibake identificados na análise de qualidade, implementando um sistema de normalização que:

1. **Detecta** problemas de encoding automaticamente
2. **Corrige** caracteres corrompidos (Ã¡ → á, â€™ → ')
3. **Valida** a qualidade do texto normalizado
4. **Integra** ao pipeline existente sem breaking changes

---

## 🔍 Contexto Técnico

### Problemas Identificados:
```
Problemas de Mojibake Comuns:
- Ã¡ → á  (á mal codificado)
- Ã© → é  (é mal codificado) 
- â€™ → '  (aspas smart mal codificadas)
- â€œ → "  (aspas de abertura)
- Â° → °  (símbolo de grau)
```

### Situação Atual:
- **Arquivo atual**: `src/enem_ingestion/parser.py` tem função `_clean_question_text()`
- **Problema**: Limpeza básica, sem correção de encoding
- **Impacto**: ~15% das questões têm caracteres corrompidos

### Solução Proposta:
- **Novo módulo**: `src/enem_ingestion/text_normalizer.py`
- **Integração**: Na função `_clean_question_text()` do parser
- **Abordagem**: Normalização progressiva com validação

---

## 🛠️ Implementação Técnica

### Arquitetura do Componente:

```python
class EnemTextNormalizer:
    """Normalizador específico para textos ENEM"""
    
    def __init__(self):
        self.mojibake_corrections = {...}  # Mapeamento de correções
        self.character_replacements = {...}  # Caracteres problemáticos
        self.cleanup_patterns = [...]  # Regex para limpeza
    
    def normalize_full(self, text: str) -> Dict:
        """Normalização completa com métricas"""
        # 1. Correção de encoding
        # 2. Limpeza de artifacts PDF  
        # 3. Normalização Unicode
        # 4. Validação final
        return {
            'original': text,
            'normalized': text_clean,
            'changes_applied': [...],
            'improvement_score': 0.95
        }
```

### Pontos de Integração:

1. **Parser Principal** (`parser.py`):
```python
def _clean_question_text(self, text: str) -> str:
    """Clean and normalize question text."""
    from .text_normalizer import normalize_enem_text
    
    # Aplicar normalização antes da limpeza existente
    text = normalize_enem_text(text)
    
    # Limpeza existente (preservar)
    # ... resto do código atual
    
    return text
```

2. **Pipeline de Validação**:
```python
def validate_extraction_quality(questions: List[Question]) -> Dict:
    """Validar qualidade após normalização"""
    quality_metrics = {}
    for question in questions:
        result = normalizer.validate_portuguese_text(question.text)
        # Coletar métricas...
    return quality_metrics
```

---

## ✅ Critérios de Aceite

### Funcionais:

1. **Correção de Mojibake**:
   - [ ] Classe `EnemTextNormalizer` implementada com mapeamentos completos
   - [ ] Método `normalize_encoding()` corrige todos os patterns identificados
   - [ ] Teste com amostra de 100 questões: 0% com mojibake após processamento

2. **Integração ao Pipeline**:
   - [ ] Função `normalize_enem_text()` integrada em `_clean_question_text()`
   - [ ] Pipeline existente continua funcionando (backward compatibility)
   - [ ] Processo de normalização é idempotente (rodar 2x = mesmo resultado)

3. **Validação de Qualidade**:
   - [ ] Método `validate_portuguese_text()` detecta problemas residuais
   - [ ] Score de melhoria calculado corretamente (0.0-1.0)
   - [ ] Relatório de qualidade gerado com métricas antes/depois

### Técnicos:

4. **Performance**:
   - [ ] Normalização não adiciona mais que 20% ao tempo de processamento
   - [ ] Memória adicional < 50MB para processamento de lote completo
   - [ ] Processo pode ser executado em batches (não memory intensive)

5. **Testabilidade**:
   - [ ] 95%+ cobertura de testes unitários
   - [ ] Testes de integração com dados reais
   - [ ] Testes de regressão com questões existentes

6. **Observabilidade**:
   - [ ] Logs estruturados com métricas de qualidade
   - [ ] Alertas para degradação de performance
   - [ ] Métricas expostas para monitoramento

---

## 🧪 Casos de Teste

### Cenário 1: Correção de Mojibake Básico
```python
def test_basic_mojibake_correction():
    normalizer = EnemTextNormalizer()
    input_text = "Questão sobre Ã¡rea e perÃ­metro"
    result = normalizer.normalize_full(input_text)
    
    assert result['normalized'] == "Questão sobre área e perímetro"
    assert 'encoding_correction' in result['changes_applied']
    assert result['improvement_score'] > 0.8
```

### Cenário 2: Integração com Parser
```python  
def test_parser_integration():
    parser = EnemPDFParser()
    
    # Simular texto corrompido do PDF
    corrupted_text = "O grÃ¡fico mostra â€œdados importantesâ€"
    
    clean_text = parser._clean_question_text(corrupted_text)
    
    # Deve estar limpo após processamento
    assert "Ã¡" not in clean_text
    assert "â€œ" not in clean_text
    assert "gráfico" in clean_text
```

### Cenário 3: Performance com Volume Real
```python
def test_performance_with_real_data():
    normalizer = EnemTextNormalizer()
    
    # Carregar 1000 questões reais
    questions = load_sample_questions(1000)
    
    start_time = time.time()
    
    normalized_questions = []
    for q in questions:
        result = normalizer.normalize_full(q.text)
        normalized_questions.append(result)
    
    processing_time = time.time() - start_time
    
    # Performance aceitável: < 2 segundos para 1000 questões
    assert processing_time < 2.0
    assert len(normalized_questions) == 1000
```

---

## 📂 Arquivos Afetados

### Novos Arquivos:
- `src/enem_ingestion/text_normalizer.py` - Implementação principal
- `tests/test_text_normalizer.py` - Testes unitários
- `tests/integration/test_parser_normalization.py` - Testes integração

### Arquivos Modificados:
- `src/enem_ingestion/parser.py` - Integração do normalizador
- `requirements.txt` - Dependências adicionais (chardet, etc)
- `README.md` - Documentação de uso

### Arquivos de Configuração:
- `pyproject.toml` - Coverage e lint configs
- `.github/workflows/ci.yml` - CI pipeline updates

---

## 🔗 Dependências

### Técnicas:
- **Biblioteca chardet**: Para detecção automática de encoding
- **unicodedata**: Normalização Unicode (Python stdlib)
- **Sistema existente**: Parser e pipeline funcionando

### Stories:
- **Bloqueante**: Nenhuma (pode ser desenvolvida independentemente)
- **Relacionadas**: EQ-003 (melhor parsing se beneficia de texto limpo)

---

## 🎛️ Configuração e Deploy

### Variáveis de Ambiente:
```bash
# Opcional: Configurar nível de validação
TEXT_NORMALIZATION_STRICT_MODE=true

# Opcional: Log level para debugging
TEXT_NORMALIZER_LOG_LEVEL=INFO
```

### Processo de Deploy:
1. **Desenvolvimento**: Implementar e testar localmente
2. **Staging**: Processar amostra de questões e validar qualidade
3. **Produção**: Deploy gradual com monitoramento

### Rollback Plan:
- **Flag feature**: Permitir desabilitar normalização via config
- **Backup**: Manter versões originais para comparação
- **Revert**: Simples remoção da chamada no parser

---

## 📊 Métricas de Sucesso

### Antes da Implementação:
- **Questões com mojibake**: ~15% (estimativa)
- **Tempo médio de processamento**: X segundos/questão
- **Qualidade de busca**: Baseline atual

### Após Implementação:
- **Questões com mojibake**: 0%
- **Tempo de processamento**: < 1.2x tempo original
- **Score de qualidade**: > 0.9 para 95% das questões
- **Regressões**: 0 (todos os testes passando)

---

## 📝 Notas de Desenvolvimento

### Considerações Importantes:
1. **Preservar semântica**: Normalizar sem alterar significado
2. **Idempotência**: Rodar múltiplas vezes deve gerar mesmo resultado
3. **Performance**: Otimizar para processamento em lote
4. **Logging**: Registrar transformações para debugging

### Casos Edge:
- Textos muito corrompidos (fallback graceful)
- Caracteres matemáticos específicos (preservar)
- Códigos e URLs (não normalizar)

---

**Criado em**: 12/10/2025  
**Status**: Ready for Development  
**Reviewers**: [@architect, @tech-lead]