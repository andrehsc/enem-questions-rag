# Story EQ-006: Implementar Placeholders de Imagem

## ��� Resumo

**Como** desenvolvedor frontend e usuário da API,
**Eu quero** que o texto das questões contenha placeholders para imagens,
**Para que** eu possa renderizar questões com imagens no local correto e proporcionar uma experiência visual completa.

---

## ��� Informações da Story

| Campo | Valor |
|-------|-------|
| **Story ID** | EQ-006 |
| **Epic** | EQ-001 - Melhoria da Qualidade de Extração |
| **Prioridade** | Alta |
| **Estimativa** | 5 Story Points |
| **Sprint** | 2 |
| **Assignee** | Backend Developer |

---

## ��� Objetivo

Implementar sistema de placeholders que:

1. **Insere** marcadores de imagem no texto das questões (`[IMAGEM_1]`, `[FIGURA_A]`)
2. **Identifica** tipo e contexto de cada imagem (gráfico, foto, diagrama)
3. **Ordena** imagens sequencialmente dentro de cada contexto
4. **Disponibiliza** metadata rica via API para renderização frontend

---

## ��� Contexto Técnico

### Problema Atual:
```
❌ Texto das questões sem indicação de onde inserir imagens
❌ Frontend não sabe posicionamento correto das imagens
❌ Usuário vê texto incompleto sem contexto visual
❌ Experiência de leitura degradada
```

### Cenários de Uso Real:

#### **Caso 1: Imagem no Enunciado**
```
Texto Original: "Analise o gráfico apresentado. Com base nos dados..."

Texto com Placeholder: "Analise o gráfico apresentado [IMAGEM_1]. Com base nos dados..."

Metadata: {
  "IMAGEM_1": {
    "id": "img_uuid_123",
    "type": "grafico",
    "description": "Gráfico de barras mostrando dados econômicos",
    "position": "enunciado"
  }
}
```

#### **Caso 2: Imagens nas Alternativas**
```
Texto Original:
A) mostra a evolução temporal
B) representa a distribuição espacial  
C) ilustra a correlação entre variáveis

Texto com Placeholder:
A) [FIGURA_A] mostra a evolução temporal
B) [FIGURA_B] representa a distribuição espacial
C) [FIGURA_C] ilustra a correlação entre variáveis

Metadata: {
  "FIGURA_A": {"id": "img_uuid_456", "type": "grafico_linha", "position": "alternativa_A"},
  "FIGURA_B": {"id": "img_uuid_789", "type": "mapa", "position": "alternativa_B"},
  "FIGURA_C": {"id": "img_uuid_012", "type": "diagrama", "position": "alternativa_C"}
}
```

#### **Caso 3: Múltiplas Imagens no Enunciado**
```
Texto com Placeholder: 
"Observe o fenômeno representado na [IMAGEM_1] e compare com o processo mostrado na [IMAGEM_2]. A diferença fundamental entre os dois casos..."

Metadata: {
  "IMAGEM_1": {"sequence": 1, "type": "foto", "description": "Processo A"},
  "IMAGEM_2": {"sequence": 2, "type": "foto", "description": "Processo B"}
}
```

---

## ��� Especificação Técnica

### Sistema de Placeholders:

```python
@dataclass
class ImagePlaceholder:
    """Placeholder de imagem com metadata rica."""
    placeholder_id: str          # 'IMAGEM_1', 'FIGURA_A', etc.
    image_id: str               # UUID da imagem no banco
    position_type: str          # 'enunciado', 'alternativa_A', etc.
    sequence: int               # Ordem dentro do contexto
    image_type: str             # 'grafico', 'foto', 'diagrama', etc.
    description: Optional[str]   # Descrição automática da imagem
    insertion_point: int        # Posição no texto onde inserir
    confidence: float           # Confiança da detecção

class ImagePlaceholderGenerator:
    """Gerador de placeholders inteligente."""
    
    def generate_placeholders(
        self, 
        question_text: str, 
        image_positions: List[ImagePosition]
    ) -> Tuple[str, Dict[str, ImagePlaceholder]]:
        """Gera texto com placeholders e metadata das imagens."""
        
        placeholders = {}
        modified_text = question_text
        
        # Agrupar imagens por contexto
        grouped_images = self._group_images_by_context(image_positions)
        
        # Gerar placeholders para enunciado
        if 'enunciado' in grouped_images:
            modified_text, enunciado_placeholders = self._insert_enunciado_placeholders(
                modified_text, grouped_images['enunciado']
            )
            placeholders.update(enunciado_placeholders)
        
        # Gerar placeholders para alternativas
        for alt_letter in ['A', 'B', 'C', 'D', 'E']:
            alt_key = f'alternativa_{alt_letter}'
            if alt_key in grouped_images:
                modified_text, alt_placeholders = self._insert_alternative_placeholders(
                    modified_text, grouped_images[alt_key], alt_letter
                )
                placeholders.update(alt_placeholders)
        
        return modified_text, placeholders
    
    def _insert_enunciado_placeholders(
        self, 
        text: str, 
        images: List[ImagePosition]
    ) -> Tuple[str, Dict[str, ImagePlaceholder]]:
        """Insere placeholders no enunciado."""
        
        placeholders = {}
        modified_text = text
        
        # Ordenar imagens por posição relativa
        sorted_images = sorted(images, key=lambda x: x.relative_position)
        
        # Inserir placeholders em ordem reversa (para não afetar posições)
        for i, img_pos in enumerate(reversed(sorted_images)):
            sequence = len(sorted_images) - i
            placeholder_id = f"IMAGEM_{sequence}"
            
            # Detectar melhor ponto de inserção
            insertion_point = self._find_insertion_point(modified_text, img_pos)
            
            # Criar placeholder
            placeholder = ImagePlaceholder(
                placeholder_id=placeholder_id,
                image_id=img_pos.image_id,
                position_type=img_pos.position_type,
                sequence=sequence,
                image_type=self._detect_image_type(img_pos),
                description=self._generate_description(img_pos),
                insertion_point=insertion_point,
                confidence=img_pos.confidence_score
            )
            
            # Inserir no texto
            placeholder_text = f"[{placeholder_id}]"
            modified_text = (
                modified_text[:insertion_point] + 
                placeholder_text + 
                modified_text[insertion_point:]
            )
            
            placeholders[placeholder_id] = placeholder
        
        return modified_text, placeholders
    
    def _insert_alternative_placeholders(
        self,
        text: str,
        images: List[ImagePosition],
        alt_letter: str
    ) -> Tuple[str, Dict[str, ImagePlaceholder]]:
        """Insere placeholders em alternativas específicas."""
        
        placeholders = {}
        modified_text = text
        
        # Encontrar posição da alternativa no texto
        alt_pattern = rf'^{alt_letter}\)\s*(.+?)(?=^[B-E]\)|$)'
        alt_match = re.search(alt_pattern, text, re.MULTILINE | re.DOTALL)
        
        if not alt_match:
            return modified_text, placeholders
        
        alt_start = alt_match.start(1)
        alt_text = alt_match.group(1)
        
        # Inserir placeholders para imagens desta alternativa
        for i, img_pos in enumerate(images):
            placeholder_id = f"FIGURA_{alt_letter}"
            if i > 0:  # Múltiplas imagens na mesma alternativa
                placeholder_id = f"FIGURA_{alt_letter}{i+1}"
            
            placeholder = ImagePlaceholder(
                placeholder_id=placeholder_id,
                image_id=img_pos.image_id,
                position_type=img_pos.position_type,
                sequence=i + 1,
                image_type=self._detect_image_type(img_pos),
                description=self._generate_description(img_pos),
                insertion_point=alt_start,
                confidence=img_pos.confidence_score
            )
            
            # Inserir no início da alternativa
            placeholder_text = f"[{placeholder_id}] "
            alt_replacement = placeholder_text + alt_text
            modified_text = modified_text.replace(alt_match.group(1), alt_replacement)
            
            placeholders[placeholder_id] = placeholder
        
        return modified_text, placeholders
    
    def _detect_image_type(self, image_position: ImagePosition) -> str:
        """Detecta tipo da imagem baseado em características."""
        # Implementar lógica de detecção baseada em:
        # - Dimensões da imagem
        # - Contexto textual ao redor
        # - Padrões visuais (futura implementação com ML)
        
        return "imagem"  # Placeholder simples por enquanto
    
    def _generate_description(self, image_position: ImagePosition) -> str:
        """Gera descrição automática da imagem."""
        # Futura implementação com Vision AI
        return f"Imagem associada à questão"
```

### Integração com Sistema Existente:

```python
@dataclass  
class QuestionWithPlaceholders:
    """Questão com placeholders de imagem inseridos."""
    id: str
    question_number: int
    question_text: str           # Texto original
    enhanced_text: str           # Texto com placeholders
    alternatives: List[str]      # Alternativas originais
    enhanced_alternatives: List[str]  # Alternativas com placeholders
    image_metadata: Dict[str, ImagePlaceholder]
    
class EnhancedQuestionProcessor:
    """Processador de questões com placeholders."""
    
    def __init__(self):
        self.placeholder_generator = ImagePlaceholderGenerator()
    
    def process_question_with_placeholders(
        self,
        question: Question,
        image_positions: List[ImagePosition]
    ) -> QuestionWithPlaceholders:
        """Processa questão inserindo placeholders de imagem."""
        
        # Gerar placeholders para o enunciado
        enhanced_text, enunciado_metadata = self.placeholder_generator.generate_placeholders(
            question.question_text, 
            [pos for pos in image_positions if pos.position_type == 'enunciado']
        )
        
        # Processar alternativas
        enhanced_alternatives = []
        alternatives_metadata = {}
        
        for i, alt_text in enumerate(question.alternatives):
            alt_letter = chr(65 + i)  # A, B, C, D, E
            alt_images = [
                pos for pos in image_positions 
                if pos.position_type == f'alternativa_{alt_letter}'
            ]
            
            if alt_images:
                enhanced_alt, alt_meta = self.placeholder_generator.generate_placeholders(
                    alt_text, alt_images
                )
                enhanced_alternatives.append(enhanced_alt)
                alternatives_metadata.update(alt_meta)
            else:
                enhanced_alternatives.append(alt_text)
        
        # Combinar metadata
        all_metadata = {**enunciado_metadata, **alternatives_metadata}
        
        return QuestionWithPlaceholders(
            id=str(question.id),
            question_number=question.question_number,
            question_text=question.question_text,
            enhanced_text=enhanced_text,
            alternatives=question.alternatives,
            enhanced_alternatives=enhanced_alternatives,
            image_metadata=all_metadata
        )
```

---

## ��� Critérios de Aceite

### AC 1: Inserção de Placeholders
- [ ] Placeholders são inseridos no local correto do texto
- [ ] Formato consistente: `[IMAGEM_N]` para enunciado, `[FIGURA_X]` para alternativas
- [ ] Múltiplas imagens são numeradas sequencialmente

### AC 2: Metadata Rica
- [ ] Cada placeholder tem metadata completa (ID, tipo, posição, sequência)
- [ ] API retorna mapping completo placeholder → imagem
- [ ] Suporte a descrições automáticas de imagens

### AC 3: Robustez
- [ ] Funciona com questões sem imagens (backward compatibility)
- [ ] Trata casos de múltiplas imagens por contexto
- [ ] Performance ≤ 2 segundos por questão

### AC 4: API Integration
- [ ] GraphQL retorna texto com placeholders
- [ ] Endpoint dedicado para metadata de imagens
- [ ] Filtros por tipo de placeholder

---

## ���️ Banco de Dados - Schema

### Nova Tabela para Placeholders:

```sql
CREATE TABLE enem_questions.question_placeholders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES enem_questions.questions(id),
    placeholder_id VARCHAR(20) NOT NULL,  -- 'IMAGEM_1', 'FIGURA_A', etc.
    image_id UUID NOT NULL REFERENCES enem_questions.question_images(id),
    position_type VARCHAR(20) NOT NULL,   -- 'enunciado', 'alternativa_A', etc.
    sequence INTEGER NOT NULL,            -- Ordem dentro do contexto
    image_type VARCHAR(50),               -- 'grafico', 'foto', 'diagrama', etc.
    description TEXT,                     -- Descrição da imagem
    insertion_point INTEGER,              -- Posição no texto original
    confidence_score FLOAT,               -- Confiança da associação
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(question_id, placeholder_id)
);

-- Índices para performance
CREATE INDEX idx_placeholders_question ON enem_questions.question_placeholders(question_id);
CREATE INDEX idx_placeholders_type ON enem_questions.question_placeholders(position_type);
CREATE INDEX idx_placeholders_sequence ON enem_questions.question_placeholders(question_id, sequence);
```

### Alteração na Tabela Questions:

```sql
-- Adicionar campos para texto com placeholders
ALTER TABLE enem_questions.questions
ADD COLUMN enhanced_question_text TEXT,  -- Texto com placeholders
ADD COLUMN has_image_placeholders BOOLEAN DEFAULT FALSE;

-- Índice para filtrar questões com placeholders
CREATE INDEX idx_questions_has_placeholders ON enem_questions.questions(has_image_placeholders);
```

---

## ��� Tasks / Subtasks

### Task 1: Core Placeholder Generation (AC: 1, 2)
- [ ] Implementar `ImagePlaceholderGenerator`
- [ ] Algoritmo de detecção de pontos de inserção
- [ ] Sistema de numeração sequencial
- [ ] Testes unitários para geração de placeholders

### Task 2: Database Schema (AC: 4)
- [ ] Criar migration para tabela `question_placeholders`
- [ ] Estender tabela `questions` com campos enhanced
- [ ] Scripts de migração de dados existentes
- [ ] Testes de schema

### Task 3: API Integration (AC: 4)
- [ ] Estender GraphQL schema para placeholders
- [ ] Endpoint para metadata de imagens
- [ ] Filtros e queries por tipo de placeholder
- [ ] Documentação de API

### Task 4: Processing Pipeline (AC: 3)
- [ ] Integrar geração de placeholders no pipeline de ingestão
- [ ] Processamento batch para dados existentes
- [ ] Otimização de performance
- [ ] Testes de integração

---

## ��� Métricas de Sucesso

### Quantitativas:
- **100%** das questões com imagens têm placeholders
- **≤ 2 segundos** de processamento por questão
- **≥ 95%** precisão na inserção de placeholders
- **0** regressões em funcionalidade existente

### Qualitativas:
- **Experiência visual completa** para usuários finais
- **Facilidade de renderização** para desenvolvedores frontend
- **Metadata rica** para casos de uso avançados

---

## ��� Estratégia de Testes

### Testes Unitários:
- Geração de placeholders para diferentes cenários
- Detecção de pontos de inserção
- Formatação consistente de placeholders

### Testes de Integração:
- Pipeline completo de processamento
- Persistência e recuperação de placeholders
- API endpoints com dados reais

### Testes de Aceitação:
- Renderização de questões reais no frontend
- Validação manual de amostras
- Performance com dataset completo

---

## ��� Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| **Placeholders mal posicionados** | Alto | Algoritmo de detecção contextual + validação |
| **Performance degradada** | Médio | Processamento assíncrono + caching |
| **Complexidade de renderização** | Médio | Documentação clara + exemplos |
| **Dados inconsistentes** | Alto | Validação rigorosa + rollback automático |

---

## ��� Exemplos de Uso da API

### GraphQL Query com Placeholders:

```graphql
query GetQuestionWithImages($id: ID!) {
  question(id: $id) {
    id
    questionNumber
    questionText          # Texto original
    enhancedText          # Texto com placeholders
    alternatives          # Alternativas originais  
    enhancedAlternatives  # Alternativas com placeholders
    
    imagePlaceholders {
      placeholderId       # "IMAGEM_1", "FIGURA_A"
      imageId
      positionType        # "enunciado", "alternativa_A"
      sequence
      imageType           # "grafico", "foto"
      description
      confidence
    }
    
    images {
      id
      imageData           # Base64 ou URL
      format              # "png", "jpg"
      width
      height
    }
  }
}
```

### Response Example:

```json
{
  "data": {
    "question": {
      "id": "uuid-123",
      "questionNumber": 91,
      "questionText": "Analise o gráfico apresentado. Com base nos dados...",
      "enhancedText": "Analise o gráfico apresentado [IMAGEM_1]. Com base nos dados...",
      "alternatives": ["mostra evolução", "representa distribuição"],
      "enhancedAlternatives": ["[FIGURA_A] mostra evolução", "representa distribuição"],
      "imagePlaceholders": [
        {
          "placeholderId": "IMAGEM_1",
          "imageId": "img-uuid-456",
          "positionType": "enunciado",
          "sequence": 1,
          "imageType": "grafico",
          "description": "Gráfico de barras econômico",
          "confidence": 0.95
        }
      ],
      "images": [
        {
          "id": "img-uuid-456",
          "imageData": "data:image/png;base64,...",
          "format": "png",
          "width": 800,
          "height": 600
        }
      ]
    }
  }
}
```

---

**Status**: Ready for Development  
**Reviewers**: [@architect, @frontend-lead, @backend-lead]  
**Dependencies**: História EQ-005 (Mapear Posições) completada

---

**Criado em**: 12/10/2025  
**Última atualização**: 12/10/2025
