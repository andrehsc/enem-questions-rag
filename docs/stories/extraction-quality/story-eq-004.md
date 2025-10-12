# Story EQ-004: Adicionar Validação de Qualidade Automática

## 📋 Resumo

**Como** desenvolvedor do sistema ENEM RAG,  
**Eu quero** implementar validação automática de qualidade de extração,  
**Para que** problemas sejam detectados proativamente e métricas de qualidade sejam monitoradas continuamente.

---

## 📊 Informações da Story

| Campo | Valor |
|-------|-------|
| **Story ID** | EQ-004 |
| **Epic** | EQ-001 - Melhoria da Qualidade de Extração |
| **Prioridade** | Alta |
| **Estimativa** | 5 Story Points |
| **Sprint** | 1 |
| **Assignee** | Backend Developer |

---

## 🎯 Objetivo

Implementar sistema de validação automática que:

1. **Detecta** problemas de qualidade em tempo real
2. **Calcula** métricas de qualidade por questão e batch
3. **Alerta** quando qualidade degrada abaixo do threshold
4. **Relatórios** executivos para monitoramento contínuo

---

## 🔍 Contexto Técnico

### Problema Atual:
```
❌ Sem validação automática de qualidade
❌ Problemas descobertos manualmente ou pelos usuários
❌ Nenhuma métrica de monitoramento
❌ Difícil identificar regressões no pipeline
```

### Solução Proposta:
```
✅ Validação integrada ao pipeline de extração
✅ Métricas de qualidade em tempo real
✅ Alertas automáticos para degradação
✅ Dashboard de qualidade para stakeholders
```

### Tipos de Validação Necessária:

1. **Validação de Texto**:
   - Encoding correto (sem mojibake)
   - Comprimento adequado
   - Caracteres válidos para português
   - Estrutura de questão reconhecível

2. **Validação de Alternativas**:
   - Exatamente 5 alternativas (A-E)
   - Comprimento mínimo por alternativa
   - Ordem alfabética correta
   - Conteúdo não vazio

3. **Validação de Metadata**:
   - Campos obrigatórios preenchidos
   - Ano válido (2009-2030)
   - Caderno válido (1-8)
   - Número de questão em range válido

4. **Validação de Imagens**:
   - Imagens associadas quando esperado
   - Formato e tamanho válidos
   - Integridade dos dados

---

## 🛠️ Implementação Técnica

### Arquitetura do Sistema:

```python
@dataclass
class QualityMetrics:
    """Métricas de qualidade para uma questão."""
    question_id: str
    overall_score: float  # 0.0-1.0
    text_quality: float
    alternatives_quality: float  
    metadata_quality: float
    image_quality: float
    issues: List[str]
    warnings: List[str]
    processing_time: float


class QualityValidator:
    """Validador principal de qualidade."""
    
    def __init__(self, config: ValidationConfig):
        self.text_validator = TextQualityValidator()
        self.alternatives_validator = AlternativesValidator()
        self.metadata_validator = MetadataValidator()
        self.image_validator = ImageQualityValidator()
        self.config = config
    
    def validate_question(self, question: Question) -> QualityMetrics:
        """Validar uma questão completa."""
        start_time = time.time()
        
        # Validações individuais
        text_result = self.text_validator.validate(question.text)
        alt_result = self.alternatives_validator.validate(question.alternatives)
        meta_result = self.metadata_validator.validate(question.metadata)
        img_result = self.image_validator.validate(question.images)
        
        # Score composto
        overall_score = self._calculate_overall_score(
            text_result, alt_result, meta_result, img_result
        )
        
        # Coletar issues
        all_issues = []
        all_warnings = []
        
        return QualityMetrics(
            question_id=str(question.id),
            overall_score=overall_score,
            text_quality=text_result.score,
            alternatives_quality=alt_result.score,
            metadata_quality=meta_result.score,
            image_quality=img_result.score,
            issues=all_issues,
            warnings=all_warnings,
            processing_time=time.time() - start_time
        )
    
    def validate_batch(self, questions: List[Question]) -> BatchQualityReport:
        """Validar lote de questões."""
        individual_metrics = []
        
        for question in questions:
            metrics = self.validate_question(question)
            individual_metrics.append(metrics)
        
        return BatchQualityReport(
            total_questions=len(questions),
            metrics=individual_metrics,
            aggregate_scores=self._calculate_aggregates(individual_metrics),
            quality_distribution=self._calculate_distribution(individual_metrics),
            recommendations=self._generate_recommendations(individual_metrics)
        )


class TextQualityValidator:
    """Validador específico para qualidade de texto."""
    
    def validate(self, text: str) -> ValidationResult:
        issues = []
        score = 1.0
        
        # Verificar encoding
        if self._has_mojibake(text):
            issues.append("Mojibake detected in text")
            score -= 0.3
        
        # Verificar comprimento
        if len(text) < 50:
            issues.append("Text too short")
            score -= 0.2
        elif len(text) > 10000:
            issues.append("Text suspiciously long")
            score -= 0.1
        
        # Verificar caracteres válidos
        invalid_chars = self._find_invalid_characters(text)
        if invalid_chars:
            issues.append(f"Invalid characters found: {invalid_chars[:5]}")
            score -= 0.2
        
        # Verificar estrutura básica
        if not self._has_question_structure(text):
            issues.append("No recognizable question structure")
            score -= 0.4
        
        return ValidationResult(
            score=max(0.0, score),
            issues=issues,
            details={'text_length': len(text), 'char_analysis': invalid_chars}
        )


class AlternativesValidator:
    """Validador para alternativas de questão."""
    
    def validate(self, alternatives: List[str]) -> ValidationResult:
        issues = []
        score = 1.0
        
        # Verificar quantidade
        if len(alternatives) != 5:
            issues.append(f"Expected 5 alternatives, found {len(alternatives)}")
            score -= 0.4
        
        # Verificar ordem alfabética
        expected_order = ['A', 'B', 'C', 'D', 'E']
        actual_letters = [alt[0] if alt and len(alt) > 0 else '?' for alt in alternatives]
        
        if actual_letters != expected_order[:len(alternatives)]:
            issues.append(f"Alternative order wrong: {actual_letters}")
            score -= 0.3
        
        # Verificar conteúdo das alternativas
        for i, alt in enumerate(alternatives):
            if not alt or len(alt.strip()) < 3:
                issues.append(f"Alternative {chr(65+i)} is empty or too short")
                score -= 0.1
            elif len(alt) > 1000:
                issues.append(f"Alternative {chr(65+i)} is suspiciously long")
                score -= 0.05
        
        return ValidationResult(
            score=max(0.0, score),
            issues=issues,
            details={'count': len(alternatives), 'lengths': [len(alt) for alt in alternatives]}
        )
```

### Integração com Pipeline:

```python
class EnemPDFParser:
    def __init__(self):
        self.quality_validator = QualityValidator(ValidationConfig())
    
    def parse_questions(self, pdf_path: Union[str, Path]) -> List[Question]:
        """Parse com validação integrada."""
        questions = self._extract_questions_from_pdf(pdf_path)
        
        # Validar qualidade
        batch_report = self.quality_validator.validate_batch(questions)
        
        # Log métricas
        logger.info(f"Batch quality: {batch_report.aggregate_scores.overall_avg:.2f}")
        
        # Alertar se qualidade baixa
        if batch_report.aggregate_scores.overall_avg < 0.7:
            logger.warning(f"Low quality batch detected: {pdf_path}")
            self._send_quality_alert(pdf_path, batch_report)
        
        # Filtrar questões com qualidade muito baixa (opcional)
        if self.config.filter_low_quality:
            questions = self._filter_by_quality(questions, batch_report)
        
        return questions
```

### Sistema de Alertas:

```python
class QualityAlertSystem:
    """Sistema de alertas para degradação de qualidade."""
    
    def __init__(self, config: AlertConfig):
        self.thresholds = config.thresholds
        self.alert_channels = config.channels  # email, slack, etc
    
    def check_and_alert(self, batch_report: BatchQualityReport):
        """Verificar se alertas devem ser enviados."""
        
        # Alerta por qualidade geral baixa
        if batch_report.aggregate_scores.overall_avg < self.thresholds.critical:
            self._send_critical_alert(batch_report)
        elif batch_report.aggregate_scores.overall_avg < self.thresholds.warning:
            self._send_warning_alert(batch_report)
        
        # Alerta por muitas questões rejeitadas
        low_quality_count = sum(1 for m in batch_report.metrics if m.overall_score < 0.5)
        if low_quality_count > self.thresholds.max_rejected:
            self._send_rejection_alert(batch_report, low_quality_count)
        
        # Alerta por tipos específicos de problema
        common_issues = self._analyze_common_issues(batch_report)
        for issue, count in common_issues.items():
            if count > self.thresholds.issue_frequency:
                self._send_issue_alert(issue, count, batch_report)
```

---

## ✅ Critérios de Aceite

### Funcionais:

1. **Validação Integrada**:
   - [ ] Sistema de validação integrado ao pipeline de parsing
   - [ ] Métricas calculadas para cada questão processada
   - [ ] Score de qualidade geral (0.0-1.0) computado corretamente

2. **Detecção de Problemas**:
   - [ ] Mojibake detectado automaticamente
   - [ ] Alternativas incompletas identificadas
   - [ ] Metadata inválida flagged
   - [ ] Imagens corrompidas ou ausentes detectadas

3. **Relatórios e Alertas**:
   - [ ] Relatório de batch gerado com métricas agregadas
   - [ ] Alertas enviados quando qualidade < threshold
   - [ ] Dashboard de qualidade acessível para stakeholders

### Técnicos:

4. **Performance**:
   - [ ] Validação adiciona <10% ao tempo de processamento
   - [ ] Memory overhead controlado (<100MB para batch completo)
   - [ ] Pode ser executado em paralelo com parsing

5. **Configurabilidade**:
   - [ ] Thresholds de qualidade configuráveis
   - [ ] Sistema de alertas configurável (email, slack, webhook)
   - [ ] Validações podem ser habilitadas/desabilitadas individualmente

6. **Observabilidade**:
   - [ ] Métricas expostas para sistemas de monitoring
   - [ ] Logs estruturados com contexto de qualidade
   - [ ] Traces para debugging de problemas específicos

---

## 🧪 Casos de Teste

### Cenário 1: Questão com Alta Qualidade
```python
def test_high_quality_question():
    question = create_perfect_question()
    validator = QualityValidator(ValidationConfig())
    
    metrics = validator.validate_question(question)
    
    assert metrics.overall_score >= 0.95
    assert len(metrics.issues) == 0
    assert metrics.text_quality >= 0.95
    assert metrics.alternatives_quality >= 0.95
```

### Cenário 2: Detecção de Mojibake
```python
def test_mojibake_detection():
    question = create_question_with_mojibake()
    question.text = "Questão sobre Ã¡rea e perÃ­metro"
    
    validator = QualityValidator(ValidationConfig())
    metrics = validator.validate_question(question)
    
    assert metrics.text_quality < 0.8
    assert any("mojibake" in issue.lower() for issue in metrics.issues)
```

### Cenário 3: Alternativas Incompletas
```python
def test_incomplete_alternatives():
    question = create_question()
    question.alternatives = ["A) Alt 1", "B) Alt 2"]  # Só 2 alternativas
    
    validator = QualityValidator(ValidationConfig())
    metrics = validator.validate_question(question)
    
    assert metrics.alternatives_quality < 0.7
    assert any("expected 5 alternatives" in issue.lower() for issue in metrics.issues)
```

### Cenário 4: Sistema de Alertas
```python
def test_quality_alerts():
    # Simular batch com qualidade baixa
    low_quality_questions = [create_low_quality_question() for _ in range(10)]
    
    validator = QualityValidator(ValidationConfig())
    alert_system = QualityAlertSystem(AlertConfig())
    
    batch_report = validator.validate_batch(low_quality_questions)
    
    # Mock do sistema de alertas
    with patch('alert_system.send_alert') as mock_alert:
        alert_system.check_and_alert(batch_report)
        
        # Deve enviar alerta para qualidade baixa
        mock_alert.assert_called_once()
```

### Cenário 5: Performance com Volume
```python
def test_validation_performance():
    # Criar 1000 questões simuladas
    questions = [create_random_question() for _ in range(1000)]
    
    validator = QualityValidator(ValidationConfig())
    
    start_time = time.time()
    batch_report = validator.validate_batch(questions)
    end_time = time.time()
    
    # Performance aceitável
    total_time = end_time - start_time
    assert total_time < 10.0  # Menos de 10 segundos para 1000 questões
    
    # Todas as questões validadas
    assert len(batch_report.metrics) == 1000
```

---

## 📊 Dashboard e Relatórios

### Métricas em Tempo Real:
```python
class QualityDashboard:
    """Dashboard de métricas de qualidade."""
    
    def get_current_metrics(self) -> Dict:
        return {
            'overall_quality_avg': 0.87,
            'questions_processed_today': 2450,
            'questions_rejected_today': 123,
            'top_issues': [
                ('Incomplete alternatives', 45),
                ('Mojibake detected', 23),
                ('Invalid metadata', 12)
            ],
            'quality_trend_7_days': [0.85, 0.86, 0.84, 0.87, 0.88, 0.87, 0.87],
            'processing_time_avg': 1.2  # seconds per question
        }
    
    def generate_weekly_report(self) -> WeeklyQualityReport:
        """Relatório executivo semanal."""
        return WeeklyQualityReport(
            period="2025-10-06 to 2025-10-12",
            total_questions=15420,
            quality_summary=QualitySummary(
                excellent=12336,  # >0.9
                good=2459,       # 0.7-0.9
                fair=523,        # 0.5-0.7
                poor=102         # <0.5
            ),
            improvements_detected=[
                "Text encoding issues reduced by 60%",
                "Alternative parsing success rate improved to 94%"
            ],
            recommendations=[
                "Investigate recurring metadata validation issues",
                "Consider OCR enhancement for image-heavy questions"
            ]
        )
```

---

## 📂 Arquivos Afetados

### Novos Arquivos:
- `src/enem_ingestion/quality_validator.py` - Validador principal
- `src/enem_ingestion/validators/` - Validadores específicos
  - `text_validator.py`
  - `alternatives_validator.py` 
  - `metadata_validator.py`
  - `image_validator.py`
- `src/enem_ingestion/quality_alerts.py` - Sistema de alertas
- `src/enem_ingestion/quality_dashboard.py` - Dashboard e relatórios
- `tests/test_quality_validation.py` - Testes completos

### Arquivos Modificados:
- `src/enem_ingestion/parser.py` - Integração da validação
- `api/graphql_types.py` - Campos de qualidade na API
- `scripts/quality_report.py` - Scripts de relatório

### Configuração:
- `config/validation_config.yaml` - Configurações de validação
- `config/alert_thresholds.yaml` - Thresholds de alerta

---

## 🔗 Dependências

### Técnicas:
- **EQ-002**: Text normalizer (melhora validação de texto)
- **EQ-003**: Alternative parser (melhora validação de alternativas)
- **Sistema de logs**: Para alertas e métricas

### Stories:
- **Depende de**: EQ-002, EQ-003 (para validar melhorias)
- **Habilita**: Monitoramento contínuo de qualidade

---

## 🎛️ Configuração

### Validation Config:
```yaml
# config/validation_config.yaml
text_validation:
  min_length: 50
  max_length: 10000
  enable_mojibake_detection: true
  
alternatives_validation:
  required_count: 5
  min_alternative_length: 3
  max_alternative_length: 1000
  
metadata_validation:
  required_fields: [year, day, caderno, question_number]
  valid_year_range: [2009, 2030]
  
quality_thresholds:
  critical: 0.5
  warning: 0.7
  excellent: 0.9
```

### Alert Config:
```yaml
# config/alert_thresholds.yaml
thresholds:
  critical: 0.5
  warning: 0.7
  max_rejected_per_batch: 10
  issue_frequency: 5

channels:
  email: 
    enabled: true
    recipients: ["dev-team@company.com"]
  slack:
    enabled: true
    webhook: "https://hooks.slack.com/..."
  webhook:
    enabled: false
    url: ""
```

---

## 📊 Métricas de Sucesso

### Antes da Implementação:
- **Detecção de problemas**: Manual, reativa
- **Tempo para identificar issues**: Dias/semanas
- **Visibilidade de qualidade**: Baixa
- **Alertas**: Nenhum

### Após Implementação:
- **Detecção automática**: >95% problemas capturados
- **Tempo para alerta**: <1 hora após processamento
- **Visibilidade**: Dashboard em tempo real
- **Métricas históricas**: Trends de 30 dias
- **False positive rate**: <5%

### KPIs Contínuos:
- **Overall Quality Score**: Meta >0.85 diário
- **Alert Response Time**: <2 horas
- **Issue Resolution Rate**: >90% em 24h
- **Dashboard Usage**: Acessado diariamente pela equipe

---

**Criado em**: 12/10/2025  
**Status**: Ready for Development  
**Reviewers**: [@architect, @devops-lead, @quality-engineer]  
**Dependencies**: EQ-002, EQ-003