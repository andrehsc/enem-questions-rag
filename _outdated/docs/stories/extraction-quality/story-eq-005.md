# Story EQ-005: Mapear Posições de Imagens no Texto

## ��� Resumo

**Como** desenvolvedor do sistema ENEM RAG,
**Eu quero** mapear as posições das imagens dentro do contexto textual das questões,
**Para que** as imagens sejam associadas corretamente ao texto e possam ser renderizadas no local apropriado.

---

## ��� Informações da Story

| Campo | Valor |
|-------|-------|
| **Story ID** | EQ-005 |
| **Epic** | EQ-001 - Melhoria da Qualidade de Extração |
| **Prioridade** | Alta |
| **Estimativa** | 8 Story Points |
| **Sprint** | 2 |
| **Assignee** | Backend Developer |

---

## ��� Objetivo

Implementar sistema de mapeamento inteligente que:

1. **Detecta** posições relativas de imagens no PDF em relação ao texto
2. **Identifica** se imagens pertencem ao enunciado ou alternativas específicas
3. **Calcula** coordenadas e contexto espacial das imagens
4. **Associa** cada imagem ao elemento textual correto (questão/alternativa)

---

## ��� Contexto Técnico

### Problema Atual:
```
❌ 1,417 imagens extraídas mas desconectadas do contexto
❌ Não sabemos se imagem pertence ao enunciado ou alternativa
❌ Impossível renderizar questões com layout correto
❌ Experiência do usuário degradada
```

### Situação Atual no Sistema:
- **ImageExtractor** extrai imagens com coordenadas (bbox)
- **EnemPDFParser** extrai texto com posições das questões
- **Banco:** Tabela `question_images` sem associação contextual
- **API:** Retorna imagens sem contexto de posicionamento

### Análise dos Dados Atuais:
```sql
-- 1,417 imagens extraídas sem contexto
SELECT COUNT(*) FROM enem_questions.question_images;

-- Questões que têm imagens associadas
SELECT COUNT(DISTINCT question_id) FROM enem_questions.question_images;
```

---

## ��� Especificação Técnica

### Algoritmo de Mapeamento:

```python
@dataclass
class ImagePosition:
    """Posição contextual de uma imagem."""
    image_id: str
    question_id: str
    position_type: str  # 'enunciado', 'alternativa_A', 'alternativa_B', etc.
    relative_position: float  # 0.0-1.0 posição relativa no texto
    bbox_coordinates: Tuple[float, float, float, float]
    confidence_score: float  # Confiança da associação

class ImagePositionMapper:
    """Mapeia posições de imagens no contexto textual."""
    
    def map_images_to_text(self, pdf_path: Path, questions: List[Question]) -> List[ImagePosition]:
        """Mapeia imagens para contexto textual das questões."""
        image_positions = []
        
        # Extrair coordenadas de texto e imagens
        text_blocks = self._extract_text_blocks_with_positions(pdf_path)
        image_blocks = self._extract_image_blocks_with_positions(pdf_path)
        
        for question in questions:
            question_images = self._find_images_for_question(
                question, text_blocks, image_blocks
            )
            image_positions.extend(question_images)
        
        return image_positions
    
    def _find_images_for_question(self, question: Question, 
                                text_blocks: List[TextBlock],
                                image_blocks: List[ImageBlock]) -> List[ImagePosition]:
        """Encontra imagens pertencentes a uma questão específica."""
        
        # 1. Identificar bbox da questão inteira
        question_bbox = self._get_question_bbox(question, text_blocks)
        
        # 2. Identificar bbox de cada alternativa
        alternatives_bbox = self._get_alternatives_bbox(question, text_blocks)
        
        # 3. Para cada imagem, determinar a qual parte pertence
        question_images = []
        for img_block in image_blocks:
            if self._image_overlaps_bbox(img_block.bbox, question_bbox):
                position = self._determine_image_position(
                    img_block, question_bbox, alternatives_bbox
                )
                question_images.append(position)
        
        return question_images
    
    def _determine_image_position(self, image_block: ImageBlock,
                                question_bbox: BBox,
                                alternatives_bbox: Dict[str, BBox]) -> ImagePosition:
        """Determina se imagem pertence ao enunciado ou alternativa específica."""
        
        max_overlap = 0.0
        best_position = 'enunciado'
        
        # Verificar sobreposição com cada alternativa
        for alt_letter, alt_bbox in alternatives_bbox.items():
            overlap = self._calculate_overlap(image_block.bbox, alt_bbox)
            if overlap > max_overlap:
                max_overlap = overlap
                best_position = f'alternativa_{alt_letter}'
        
        # Calcular posição relativa no texto
        relative_pos = self._calculate_relative_position(
            image_block.bbox, question_bbox
        )
        
        return ImagePosition(
            image_id=image_block.id,
            question_id=question_bbox.question_id,
            position_type=best_position,
            relative_position=relative_pos,
            bbox_coordinates=image_block.bbox,
            confidence_score=max_overlap if max_overlap > 0.3 else 0.8
        )
```

### Integração com Sistema Existente:

```python
class EnhancedEnemPDFParser(EnemPDFParser):
    """Parser ENEM com mapeamento de imagens."""
    
    def __init__(self):
        super().__init__()
        self.image_mapper = ImagePositionMapper()
        self.image_extractor = ImageExtractor()
    
    def parse_questions_with_images(self, pdf_path: Path) -> List[QuestionWithImages]:
        """Parse questões com mapeamento completo de imagens."""
        
        # 1. Parse tradicional
        questions = super().parse_questions(pdf_path)
        
        # 2. Mapear posições das imagens
        image_positions = self.image_mapper.map_images_to_text(pdf_path, questions)
        
        # 3. Associar imagens às questões
        questions_with_images = []
        for question in questions:
            question_images = [
                pos for pos in image_positions 
                if pos.question_id == question.id
            ]
            
            enhanced_question = QuestionWithImages(
                **question.__dict__,
                image_positions=question_images
            )
            questions_with_images.append(enhanced_question)
        
        return questions_with_images
```

---

## ��� Critérios de Aceite

### AC 1: Detecção de Posição
- [ ] Sistema detecta se imagem pertence ao enunciado ou alternativa
- [ ] Calcula coordenadas relativas (bbox) corretamente
- [ ] Confiança da associação ≥ 80% para casos claros

### AC 2: Associação Correta
- [ ] Imagens são associadas à questão correta
- [ ] Imagens em alternativas são associadas à letra correta (A, B, C, D, E)
- [ ] Múltiplas imagens por questão são ordenadas corretamente

### AC 3: Robustez
- [ ] Funciona com layouts de todos os anos (2020-2024)
- [ ] Trata casos de imagens sobrepostas ou ambíguas
- [ ] Performance ≤ 5 segundos por arquivo PDF

### AC 4: Integração
- [ ] Dados são persistidos na tabela `question_images` com novo schema
- [ ] API GraphQL retorna posições das imagens
- [ ] Backward compatibility mantida

---

## ���️ Banco de Dados - Alterações

### Schema Extension:

```sql
-- Extensão da tabela question_images
ALTER TABLE enem_questions.question_images 
ADD COLUMN position_type VARCHAR(20),  -- 'enunciado', 'alternativa_A', etc.
ADD COLUMN relative_position FLOAT,    -- 0.0-1.0 posição relativa
ADD COLUMN confidence_score FLOAT,     -- Confiança da associação
ADD COLUMN bbox_x0 FLOAT,             -- Coordenadas do bounding box
ADD COLUMN bbox_y0 FLOAT,
ADD COLUMN bbox_x1 FLOAT,
ADD COLUMN bbox_y1 FLOAT;

-- Índices para performance
CREATE INDEX idx_question_images_position ON enem_questions.question_images(position_type);
CREATE INDEX idx_question_images_confidence ON enem_questions.question_images(confidence_score);
```

---

## ��� Tasks / Subtasks

### Task 1: Implementar Core Mapping Algorithm (AC: 1, 2)
- [ ] Criar classe `ImagePositionMapper`
- [ ] Implementar detecção de bbox de questões e alternativas
- [ ] Implementar algoritmo de sobreposição e associação
- [ ] Testes unitários para algoritmo de mapeamento

### Task 2: Integração com Parser Existente (AC: 3, 4)
- [ ] Estender `EnemPDFParser` com capacidades de mapeamento
- [ ] Integrar `ImageExtractor` com novo sistema
- [ ] Garantir compatibilidade com todos os anos (2020-2024)
- [ ] Testes de integração

### Task 3: Database Schema e Migration (AC: 4)
- [ ] Criar migration para extensão da tabela `question_images`
- [ ] Implementar métodos de persistência de posições
- [ ] Script de migração para dados existentes
- [ ] Testes de migração

### Task 4: API Integration (AC: 4)
- [ ] Estender GraphQL schema para retornar posições
- [ ] Adicionar filtros por tipo de posição
- [ ] Documentar novos endpoints
- [ ] Testes de API

---

## �� Métricas de Sucesso

### Quantitativas:
- **95%+** das imagens associadas corretamente
- **≤ 5 segundos** de processamento por PDF
- **≥ 80%** de confiança média das associações
- **100%** backward compatibility

### Qualitativas:
- **Mapeamento preciso** de imagens para alternativas específicas
- **Robustez** em diferentes layouts de anos
- **Performance** adequada para processamento em lote

---

## ��� Estratégia de Testes

### Testes Unitários:
- Algoritmo de detecção de bbox
- Cálculo de sobreposição
- Associação de imagens a posições

### Testes de Integração:  
- Pipeline completo de parse com mapeamento
- Persistência e recuperação de dados
- API endpoints com novos dados

### Testes de Aceitação:
- Casos reais de PDFs ENEM 2020-2024
- Validação manual de amostras
- Performance com arquivos grandes

---

## ��� Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| **Layouts inconsistentes** | Alto | Algoritmo adaptativo por ano |
| **Performance degradada** | Médio | Otimização algorítmica + caching |
| **Associações incorretas** | Alto | Sistema de confiança + validação manual |
| **Regressão sistema atual** | Alto | Testes extensivos + feature flags |

---

**Status**: Ready for Development  
**Reviewers**: [@architect, @backend-lead, @qa-engineer]  
**Dependencies**: Histórias EQ-002 e EQ-003 completadas

---

**Criado em**: 12/10/2025  
**Última atualização**: 12/10/2025
