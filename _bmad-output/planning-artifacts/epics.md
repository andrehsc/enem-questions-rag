# ENEM Questions RAG — Epics & Stories

> **Projeto:** enem-questions-rag  
> **Referência arquitetural:** `_bmad-output/planning-artifacts/architecture.md`  
> **Objetivo:** Pipeline de ingestão + RAG sobre questões ENEM com 3 features principais para integração TeachersHub.

---

## Epic 1: Fundação Vetorial — pgvector + Chunk Builder

**Objetivo:** Preparar o banco de dados para armazenar embeddings e implementar a estratégia de chunking híbrido das questões ENEM.

**Critérios de aceite do epic:**
- Extensão pgvector instalada e tabelas vetoriais criadas com migration reversível
- Chunk builder produz exatamente os chunks corretos para cada tipo de questão
- Todos os testes passam

### Story 1.1: Migration pgvector e Schema Vetorial

Como desenvolvedor,  
Quero criar as tabelas e extensões necessárias no PostgreSQL para armazenar embeddings,  
Para que o sistema possa persistir e consultar vetores de questões ENEM.

**Critérios de aceite:**
- [ ] Extensão `vector` instalada via `CREATE EXTENSION IF NOT EXISTS vector`
- [ ] Tabela `question_chunks` criada com coluna `embedding vector(1536)` e índice HNSW
- [ ] Tabela `question_images` criada com campos de referência e OCR
- [ ] Colunas `ingestion_hash`, `has_images`, `embedding_status` adicionadas à tabela `questions` existente
- [ ] Migration é idempotente (pode rodar múltiplas vezes sem erro)
- [ ] Migration pode ser revertida (down migration documentada)

### Story 1.2: Chunk Builder — Estratégia Híbrida

Como desenvolvedor,  
Quero um módulo `chunk_builder.py` que produza chunks híbridos de questões ENEM,  
Para que cada questão seja representada por até 2 chunks (full + context) com metadados ricos.

**Critérios de aceite:**
- [ ] Questão com texto-base gera 2 chunks: `full` (enunciado+alternativas) e `context` (texto-base)
- [ ] Questão sem texto-base gera apenas 1 chunk: `full`
- [ ] Cada chunk inclui `content_hash` SHA-256 para idempotência
- [ ] `token_count` calculado via `tiktoken` antes de retornar o chunk
- [ ] Chunks com mais de 8000 tokens são truncados com aviso no log
- [ ] Testes unitários cobrem: questão simples, questão com texto-base, questão matemática curta, questão com imagem

### Story 1.3: Testes de Integração do Schema

Como desenvolvedor,  
Quero testes de integração que validem o schema pgvector com dados reais,  
Para garantir que a estrutura suporta inserção e consulta de embeddings corretamente.

**Critérios de aceite:**
- [ ] Teste insere chunk com embedding mock e valida recuperação por `question_id`
- [ ] Teste valida constraint UNIQUE em `content_hash` (não permite duplicata)
- [ ] Teste valida índice HNSW com busca de similaridade básica
- [ ] Teste valida cascade delete (deletar question deleta seus chunks)

---

## Epic 2: Pipeline de Embeddings — Geração e Ingestão

**Objetivo:** Implementar o pipeline completo de geração de embeddings via OpenAI e persistência no pgvector, com cache Redis para evitar chamadas desnecessárias à API.

**Critérios de aceite do epic:**
- Pipeline completo executa do PDF ao embedding armazenado
- Re-ingestão não gera duplicatas nem custos adicionais de API
- Relatório de ingestão mostra custo, erros e estatísticas

### Story 2.1: Embedding Generator com Cache Redis

Como desenvolvedor,  
Quero um módulo `embedding_generator.py` que gere embeddings via OpenAI com cache Redis,  
Para que o sistema não faça chamadas desnecessárias à API ao re-ingerir questões.

**Critérios de aceite:**
- [ ] Chama `text-embedding-3-small` em batches de até 100 chunks
- [ ] Verifica Redis cache por `content_hash` antes de chamar a API (TTL 7 dias)
- [ ] Armazena resultado no Redis após chamada bem-sucedida
- [ ] Implementa retry exponencial (3 tentativas) em caso de rate limit ou erro 5xx
- [ ] Registra tokens usados por sessão para controle de custo
- [ ] Lança `TokenLimitError` se chunk exceder 8192 tokens

### Story 2.2: pgvector Writer — Persistência de Embeddings

Como desenvolvedor,  
Quero um módulo `pgvector_writer.py` que persista embeddings na tabela `question_chunks`,  
Para que os vetores fiquem disponíveis para busca semântica.

**Critérios de aceite:**
- [ ] Insere chunks com `ON CONFLICT (content_hash) DO UPDATE SET updated_at = NOW()`
- [ ] Atualiza `embedding_status` na tabela `questions` após inserção bem-sucedida
- [ ] Suporta inserção em batch (lista de chunks)
- [ ] Registra erros por `question_id` sem interromper o batch inteiro
- [ ] Transação: falha em um chunk não reverte o batch inteiro (insert individual com try/except)

### Story 2.3: Ingestion Pipeline — Orquestrador

Como desenvolvedor,  
Quero um módulo `ingestion_pipeline.py` que orquestre todo o fluxo de ingestão,  
Para que um único comando processe PDFs do INEP até embeddings no pgvector.

**Critérios de aceite:**
- [ ] Aceita lista de arquivos PDF ou diretório como entrada
- [ ] Executa sequencialmente: parser → image_extractor → normalizer → chunk_builder → embedding_generator → pgvector_writer
- [ ] Pula questões com `embedding_status = 'done'` (idempotência)
- [ ] Gera relatório ao final: total processado, novos, pulados, erros, tokens usados, custo estimado
- [ ] Pode ser executado via CLI: `python -m enem_ingestion.ingestion_pipeline --input data/downloads/`

---

## Epic 3: Busca Semântica — Feature 1

**Objetivo:** Expor a busca vetorial via API REST para recuperação de questões ENEM por similaridade semântica, com filtros por matéria, ano e dificuldade.

**Critérios de aceite do epic:**
- Endpoint de busca retorna questões completas reconstituídas em <3 segundos
- Gabarito retornado apenas quando solicitado
- Filtros por matéria e ano funcionam em combinação com busca semântica

### Story 3.1: Atualizar Semantic Search para pgvector

Como desenvolvedor,  
Quero atualizar `src/rag_features/semantic_search.py` para usar pgvector em vez de ChromaDB,  
Para que a busca semântica use o mesmo PostgreSQL já em uso no projeto.

**Critérios de aceite:**
- [ ] Classe `PgVectorSearch` implementa a interface `SemanticSearchInterface` existente
- [ ] Busca por similaridade cosseno usando operador `<=>` do pgvector
- [ ] Suporta filtros por metadados: `year`, `subject`, `chunk_type`
- [ ] Reconstrói questão completa agrupando chunks por `question_id`
- [ ] Busca retorna no máximo `limit` questões únicas (não chunks duplicados)
- [ ] ChromaDB mantido como fallback via flag de configuração `VECTOR_STORE=pgvector|chromadb`

### Story 3.2: Endpoint POST /api/v1/search/semantic

Como professor no TeachersHub,  
Quero buscar questões ENEM por assunto ou texto,  
Para encontrar questões relevantes para minhas aulas e avaliações.

**Critérios de aceite:**
- [ ] Endpoint aceita `query`, `subject` (opcional), `year` (opcional), `limit` (default=10), `include_answer` (default=false)
- [ ] Retorna lista de questões com `similarity_score`, `full_text`, `images` (paths), metadados
- [ ] Inclui `correct_answer` apenas se `include_answer=true`
- [ ] Resposta segue formato padrão `{data: [...], meta: {...}, error: null}`
- [ ] Tempo de resposta <3 segundos para queries simples (requisito NFR3 do PRD)
- [ ] Documentado no Swagger existente

---

## Epic 4: Geração com RAG — Features 2 e 3

**Objetivo:** Implementar geração de avaliações de treino (Feature 2) e geração de novas questões no estilo ENEM (Feature 3) usando RAG com GPT-4o.

**Critérios de aceite do epic:**
- Avaliações geradas são coerentes com o corpus ENEM e os filtros solicitados
- Novas questões mantêm formato e dificuldade ENEM
- Gabarito e explicação sempre incluídos nas questões geradas

### Story 4.1: Assessment Generator — Feature 2

Como professor no TeachersHub,  
Quero gerar avaliações de treino com questões reais do ENEM filtradas por matéria e dificuldade,  
Para criar provas personalizadas para meus alunos.

**Critérios de aceite:**
- [ ] Módulo `assessment_generator.py` criado em `src/rag_features/`
- [ ] Seleciona questões via busca semântica + filtros sem repetição
- [ ] Distribui questões por dificuldade quando especificado (easy/medium/hard)
- [ ] Endpoint `POST /api/v1/assessments/generate` aceita `subject`, `difficulty`, `question_count`, `years`
- [ ] Retorna `assessment_id` (UUID), lista de questões completas e gabarito separado
- [ ] Avaliação persistida na tabela `assessments` para referência futura

### Story 4.2: Question Generator RAG — Feature 3

Como professor no TeachersHub,  
Quero gerar novas questões inéditas no estilo ENEM baseadas em um assunto e nível de dificuldade,  
Para criar material complementar além do corpus existente.

**Critérios de aceite:**
- [ ] Módulo `question_generator.py` atualizado em `src/rag_features/`
- [ ] Usa chunks `context` como contexto RAG para o GPT-4o gerar questões
- [ ] Prompt instrui GPT-4o a seguir formato ENEM: 5 alternativas (A-E), 1 correta, texto-base quando relevante
- [ ] Questão gerada inclui: enunciado, alternativas, gabarito, explicação da resposta correta
- [ ] Inclui `source_context_ids` (IDs dos chunks usados como contexto)
- [ ] Endpoint `POST /api/v1/questions/generate` aceita `subject`, `topic`, `difficulty`, `count`, `style`
- [ ] Questões geradas NÃO são persistidas no corpus principal (ficam em tabela separada `generated_questions`)

---

# Pipeline de Extração v2 — Novos Épicos

> **Contexto:** O pipeline atual (pdfplumber+regex) será substituído por uma arquitetura híbrida de 3 camadas.
> **Hardware disponível:** NVIDIA RTX 3060 (12 GB VRAM) + CPU
> **Azure credits:** R$290 disponíveis (~5.500 páginas Layout)

## Requirements Inventory

### Functional Requirements

FR-EX1: Substituir pdfplumber por pymupdf4llm como extrator primário com multi-coluna automático e OCR integrado em português
FR-EX2: Implementar confidence scoring por questão extraída (5 alternativas, texto válido, sequência numérica, comprimento mínimo)
FR-EX3: Implementar fallback para Azure DI Layout com add-on de fórmulas para questões com confidence < 0.80
FR-EX4: Criar dead letter queue para questões com confidence < 0.50 (revisão manual)
FR-EX5: Criar golden set de 50 questões verificadas manualmente para benchmark de acurácia
FR-EX6: Implementar validação Pydantic para estrutura de questões ENEM (5 alternativas A-E, número sequencial, enunciado mínimo)
FR-EX7: Extrair fórmulas matemáticas como LaTeX via Azure DI formula add-on
FR-EX8: Manter associação imagem-questão via bounding box overlap do pymupdf4llm
FR-EX9: Implementar hybrid search (pgvector + tsvector) com Reciprocal Rank Fusion em português
FR-EX10: Pipeline deve ser idempotente (hash de conteúdo como chave, sem duplicatas na re-ingestão)
FR-EX11: Implementar text sanitizer robusto que remove headers ENEM, artefatos InDesign, tokens (cid:XX), timestamps duplicados e markdown residual
FR-EX12: Corrigir extração de alternativas: eliminar cascata, merge de estratégias, remover placeholders [Alternative not found], suporte a formato 2022-2023 (AA/BB)
FR-EX13: Implementar confidence scorer v2 que detecta contaminação textual (placeholders, cid tokens, headers, InDesign) com pesos recalibrados
FR-EX14: Implementar deduplicação inteligente de cadernos com content hash, pick-best-extraction e canonical_question_id
FR-EX15: Implementar re-extração seletiva usando pymupdf4llm para anos com cid:XX (2021) e InDesign artifacts (2024)
FR-EX16: Criar pipeline de validação e relatório de qualidade com métricas automáticas e auditoria por ano/dia/caderno/extrator

### NonFunctional Requirements

NFR-EX1: Acurácia de extração > 98% (2.450/2.500 questões extraídas corretamente)
NFR-EX2: 5 alternativas extraídas em > 99% das questões
NFR-EX3: Character Error Rate (CER) < 2% contra golden set
NFR-EX4: Pipeline completo em < 30 min para 500 páginas (com RTX 3060)
NFR-EX5: Custo cloud < R$50 por execução completa (créditos Azure)
NFR-EX6: Compliance LGPD — processamento local-first, cloud apenas para fallback
NFR-EX7: Licenças Apache 2.0/MIT apenas — evitar GPL/AGPL sem licença comercial
NFR-EX8: Taxa de [Alternative not found] < 2% após sanitização (atualmente 918 ocorrências)
NFR-EX9: Zero alternativas em cascata no banco de dados (atualmente 1.782)
NFR-EX10: Zero headers/footers de página no conteúdo final (atualmente ~2.500)
NFR-EX11: Banco com ~900 questões únicas após deduplicação (atualmente ~4.700)
NFR-EX12: >90% de questões limpas e utilizáveis para RAG (atualmente ~10%)

### Additional Requirements

- pymupdf4llm mantém compatibilidade com SQLAlchemy models existentes (Question, Alternative, etc.)
- Schema pgvector existente (question_chunks) deve ser preservado e estendido
- Novos campos: confidence_score, extraction_method, extraction_errors no schema
- RTX 3060 (12 GB VRAM) disponível para pymupdf4llm layout AI module (ONNX, sem CUDA obrigatório)
- Azure DI: R$290 em créditos disponíveis (~5.500 páginas Layout)
- Golden set como fixture de teste no CI (pytest)
- Manter compatibilidade com endpoints FastAPI existentes (/api/v1/search/semantic, etc.)
- Docker Compose existente deve ser estendido (não substituído)

### FR Coverage Map

| Requisito | Epic | Story |
|-----------|------|-------|
| FR-EX1 | Epic 5 | 5.1 |
| FR-EX2 | Epic 5 | 5.2 |
| FR-EX6 | Epic 5 | 5.2 |
| FR-EX8 | Epic 5 | 5.1 |
| FR-EX10 | Epic 5 | 5.3 |
| FR-EX3 | Epic 6 | 6.1 |
| FR-EX4 | Epic 6 | 6.2 |
| FR-EX7 | Epic 6 | 6.1 |
| FR-EX5 | Epic 7 | 7.1 |
| FR-EX9 | Epic 7 | 7.2 |
| FR-EX11 | Epic 8 | 8.1 |
| FR-EX12 | Epic 8 | 8.2 |
| FR-EX13 | Epic 8 | 8.3 |
| FR-EX14 | Epic 8 | 8.4 |
| FR-EX15 | Epic 8 | 8.5 |
| FR-EX16 | Epic 8 | 8.6 |

---

## Epic 5: Extração Primária — pymupdf4llm

**Objetivo:** Substituir o extrator pdfplumber+regex pelo pymupdf4llm como camada primária de extração, com confidence scoring e validação Pydantic.

**Arquitetura:** Camada 1 (>80% das questões) — processamento 100% local, R$0.

**Critérios de aceite do epic:**
- pymupdf4llm extrai questões ENEM com multi-coluna automático e OCR em português
- Confidence scoring classifica cada questão extraída (≥0.80 = OK, <0.80 = fallback, <0.50 = dead letter)
- Validação Pydantic garante estrutura correta (5 alternativas A-E, número sequencial, enunciado)
- Pipeline idempotente via content hash

### Story 5.1: pymupdf4llm Extractor Module

Como desenvolvedor,
Quero um módulo `pymupdf4llm_extractor.py` que substitua o pdfplumber como extrator primário,
Para extrair questões ENEM com multi-coluna automático, OCR em português e associação de imagens.

**Critérios de aceite:**
- [ ] Usa `pymupdf4llm.to_markdown()` com `page_chunks=True` para extração
- [ ] Multi-coluna detectado automaticamente via layout AI module (ONNX)
- [ ] OCR ativado via `force_ocr=True, ocr_language="por"` para páginas escaneadas
- [ ] Header/footer removidos via `header=False, footer=False`
- [ ] Associação imagem-questão via bounding box overlap
- [ ] Compatível com SQLAlchemy models existentes (Question, Alternative)
- [ ] Testes unitários com PDFs de referência (pelo menos 3 tipos: texto puro, multi-coluna, com imagens)

### Story 5.2: Confidence Scoring & Validação Pydantic

Como desenvolvedor,
Quero um sistema de confidence scoring e validação Pydantic para cada questão extraída,
Para classificar automaticamente a qualidade da extração e direcionar questões para fallback ou dead letter.

**Critérios de aceite:**
- [ ] Model Pydantic `ENEMQuestion` valida: 5 alternativas (A-E), número sequencial, enunciado mínimo (50 chars)
- [ ] Confidence score (0.0-1.0) baseado em: presença de 5 alternativas, texto válido, sequência numérica, comprimento
- [ ] Score ≥ 0.80 → aceita no pipeline
- [ ] Score < 0.80 e ≥ 0.50 → envia para fallback Azure DI (Epic 6)
- [ ] Score < 0.50 → dead letter queue (Epic 6)
- [ ] Campo `confidence_score` e `extraction_method` persistidos no schema
- [ ] Testes com questões de diferentes qualidades (perfeita, parcial, corrompida)

### Story 5.3: Pipeline Idempotente v2

Como desenvolvedor,
Quero que o pipeline v2 seja idempotente usando content hash como chave,
Para que re-ingestões não gerem duplicatas nem reprocessamento desnecessário.

**Critérios de aceite:**
- [ ] Hash SHA-256 do conteúdo extraído como chave de idempotência
- [ ] `ON CONFLICT (content_hash)` atualiza apenas metadata (timestamp, confidence_score)
- [ ] Re-ingestão de PDF já processado completa em <5 segundos (skip path)
- [ ] Log diferencia: novas, atualizadas, puladas, erros
- [ ] CLI: `python -m enem_ingestion.pipeline_v2 --input data/downloads/`

---

## Epic 6: Fallback Azure DI + Dead Letter Queue

**Objetivo:** Implementar a camada de fallback com Azure Document Intelligence Layout para questões com baixa confiança, e dead letter queue para revisão manual.

**Arquitetura:**
- Camada 2 (~15% das questões) — Azure DI Layout, ~R$50 dos créditos
- Camada 3 (<2% das questões) — Dead letter, revisão manual

**Critérios de aceite do epic:**
- Azure DI Layout processa questões com confidence < 0.80 do pymupdf4llm
- Fórmulas matemáticas extraídas como LaTeX via formula add-on
- Dead letter queue persiste questões irrecuperáveis para revisão manual
- Custo Azure controlado (< R$50 por execução completa)

### Story 6.1: Azure DI Layout Fallback

Como desenvolvedor,
Quero um módulo de fallback que use Azure Document Intelligence Layout para reprocessar questões com baixa confiança,
Para recuperar questões que o pymupdf4llm não extraiu corretamente.

**Critérios de aceite:**
- [ ] Usa `DocumentIntelligenceClient` com `begin_analyze_document("prebuilt-layout")`
- [ ] Ativado automaticamente para questões com confidence < 0.80
- [ ] Add-on `DocumentAnalysisFeature.FORMULAS` ativado para extrair LaTeX
- [ ] Output em `ContentFormat.MARKDOWN` para compatibilidade com parser existente
- [ ] Re-scoring após extração Azure DI para validar melhoria de qualidade
- [ ] Controle de custo: tracking de páginas processadas vs budget R$50
- [ ] Testes com mock do Azure DI SDK (sem chamadas reais no CI)

### Story 6.2: Dead Letter Queue

Como desenvolvedor,
Quero uma dead letter queue para questões com confidence < 0.50 após todas as tentativas de extração,
Para que questões irrecuperáveis automaticamente sejam encaminhadas para revisão manual.

**Critérios de aceite:**
- [ ] Tabela `dead_letter_questions` com: question_ref, raw_content, extraction_errors, confidence_score, created_at
- [ ] Questões com confidence < 0.50 (ambas camadas) inseridas automaticamente
- [ ] Inclui diagnóstico: qual camada falhou, razão da baixa confiança, raw text extraído
- [ ] Endpoint GET `/api/v1/admin/dead-letter` para listar e gerenciar (paginated)
- [ ] Endpoint PATCH `/api/v1/admin/dead-letter/{id}` para marcar como resolvida manualmente
- [ ] Testes unitários cobrem: inserção, listagem, resolução, re-ingestão após correção

---

## Epic 7: Golden Set & Hybrid Search

**Objetivo:** Criar benchmark de qualidade (golden set) e implementar hybrid search com Reciprocal Rank Fusion para melhorar a relevância da busca semântica.

**Critérios de aceite do epic:**
- Golden set de 50 questões verificadas manualmente como fixture de teste
- Pipeline v2 atinge acurácia > 98% contra golden set
- Hybrid search (pgvector + tsvector) melhora recall em queries em português

### Story 7.1: Golden Set de Benchmark

Como desenvolvedor,
Quero um golden set de 50 questões ENEM verificadas manualmente,
Para servir como benchmark de acurácia do pipeline de extração.

**Critérios de aceite:**
- [ ] 50 questões selecionadas: 10 por área (Linguagens, Humanas, Natureza, Matemática, Redação-suporte)
- [ ] Cada questão inclui: texto-base (se presente), enunciado, 5 alternativas, gabarito, metadados
- [ ] Formato JSON como fixture pytest (`tests/fixtures/golden_set.json`)
- [ ] Script de validação compara output do pipeline vs golden set
- [ ] Métricas: acurácia, CER (Character Error Rate), completude de alternativas
- [ ] CI executa validação contra golden set em cada PR

### Story 7.2: Hybrid Search — pgvector + tsvector com RRF

Como desenvolvedor,
Quero implementar hybrid search combinando busca vetorial (pgvector) com busca textual (tsvector) usando Reciprocal Rank Fusion,
Para melhorar a relevância de busca em queries em português.

**Critérios de aceite:**
- [ ] Coluna `tsv_content tsvector` adicionada a `question_chunks` com config `portuguese`
- [ ] Busca textual usando `ts_query` com stemming em português
- [ ] Reciprocal Rank Fusion (RRF) combina rankings: `1/(k+rank_vector) + 1/(k+rank_text)` com k=60
- [ ] Parâmetro `search_mode` no endpoint: `semantic`, `text`, `hybrid` (default: `hybrid`)
- [ ] Benchmark: hybrid search melhora recall@10 em ≥5% vs busca vetorial pura
- [ ] Índice GIN em `tsv_content` para performance de busca textual
- [ ] Testes com queries em português (acentuação, sinônimos, termos técnicos)

---

## Epic 8: Melhoria da Qualidade de Extração

**Objetivo:** Elevar a qualidade dos dados extraídos de ~10% para >90% de questões limpas e utilizáveis, corrigindo headers/footers, alternativas em cascata, placeholders, contaminação textual e duplicatas entre cadernos.

**Arquitetura:** Post-processing layers sobre o pipeline v2 existente. Nenhuma dependência de cloud nova. Refactoring dos módulos text_normalizer, alternative_extractor, confidence_scorer e pipeline_v2.

**Diagnóstico base:** Análise de 4.709 entradas extraídas revelou: (cid:XX) garbled text (2.829 linhas, 2021), alternativas em cascata (1.782), [Alternative not found] (918), headers/footers no conteúdo (~2.500), artefatos InDesign (~1.200), markdown residual (1.050). Detalhes em `docs/stories/extraction-quality/PLAN-extraction-quality-improvements.md`.

**Critérios de aceite do epic:**
- Text sanitizer remove 100% dos headers ENEM, artefatos InDesign, tokens (cid:XX) e markdown residual
- Taxa de [Alternative not found] < 2% (de 918 para <20)
- Zero alternativas em cascata no banco
- Confidence scorer rejeita questões com contaminação textual
- Banco com ~900 questões únicas (deduplicação de ~4.700 entradas)
- Relatório de qualidade automático com métricas por ano/dia/caderno/extrator

### Story 8.1: Text Sanitizer Robusto

Como desenvolvedor,
Quero uma camada de sanitização pós-extração que limpe headers, footers, artefatos InDesign, tokens (cid:XX) e markdown residual,
Para que o texto armazenado no banco esteja limpo e utilizável para RAG.

**Critérios de aceite:**
- [ ] Regex remove headers ENEM em todas variantes (CADERNO X, NEM2024, Página NN, áreas temáticas)
- [ ] Regex remove artefatos InDesign (caracteres duplicados PP22__, timestamps duplicados)
- [ ] Tokens (cid:XX) substituídos por espaço e espaços múltiplos colapsados
- [ ] Artefatos markdown (## **, #) removidos do texto final
- [ ] Singleton do normalizer (não re-instanciar a cada chamada)
- [ ] Testes com exemplos reais de cada categoria de poluição

### Story 8.2: Extração de Alternativas Robusta

Como desenvolvedor,
Quero corrigir a lógica de splitting de alternativas para eliminar cascata, merge de estratégias e placeholders,
Para que todas as questões tenham 5 alternativas corretas ou sejam roteadas para fallback.

**Critérios de aceite:**
- [ ] Detecção e correção de alternativas em cascata (differencing)
- [ ] Merge de estratégias: união de resultados de múltiplas estratégias
- [ ] Placeholder [Alternative not found] nunca salvo no banco
- [ ] False-positive filter substituído por heurística baseada em comprimento/estrutura
- [ ] Suporte a formato 2022-2023 (AA, BB, CC, DD, EE)
- [ ] Testes: cascata, merge, alternativas matemáticas curtas, formato dupla-letra

### Story 8.3: Confidence Scorer v2

Como desenvolvedor,
Quero que o scorer detecte contaminação textual e não aprove questões com placeholders, cid tokens ou headers residuais,
Para que apenas questões limpas sejam aceitas no banco.

**Critérios de aceite:**
- [ ] Penalização por placeholders ([Alternative not found]) em alternativas
- [ ] Penalização por contaminação: (cid:XX), InDesign, headers ENEM, timestamps
- [ ] Penalização por cascata: alt_A.length > 3 * alt_E.length
- [ ] Novos pesos: alt_count 0.20, text_quality 0.20, alt_quality 0.25, sequence 0.15, contamination 0.10, pydantic 0.10
- [ ] Threshold mais rigoroso: ACCEPT >= 0.85
- [ ] Testes com questões contaminadas e limpas

### Story 8.4: Deduplicação Inteligente de Cadernos

Como desenvolvedor,
Quero deduplicar questões entre cadernos mantendo a melhor extração,
Para que o banco tenha ~900 questões únicas em vez de ~4.700 duplicatas.

**Critérios de aceite:**
- [ ] Hash de conteúdo do enunciado normalizado como chave de dedup
- [ ] Na ingestão, manter a versão com maior confidence score
- [ ] Pick-best entre pdfplumber e pymupdf4llm para mesma questão
- [ ] Coluna `canonical_question_id` linkando duplicatas ao registro canônico
- [ ] Migration SQL idempotente para nova coluna
- [ ] Testes: dedup correta, pick-best, questões similares-mas-diferentes mantidas

### Story 8.5: Re-extração Seletiva

Como desenvolvedor,
Quero usar pymupdf4llm como extrator para anos onde pdfplumber falha (2021 cid:XX, 2024 InDesign),
Para recuperar texto legível em questões atualmente inutilizáveis.

**Critérios de aceite:**
- [ ] 2021: re-extração completa com pymupdf4llm (sem cid:XX)
- [ ] 2024 Dia 2: teste de pymupdf4llm para reduzir InDesign artifacts
- [ ] Comparador dual-extrator: rodar ambos e manter o de maior confidence média
- [ ] Matriz de decisão extrator × ano/dia documentada
- [ ] Questões 2021 com >= 80% de texto legível (vs ~10% atual)

### Story 8.6: Pipeline de Validação e Relatório de Qualidade

Como desenvolvedor,
Quero um script de auditoria e relatório automático de qualidade pós-extração,
Para medir o impacto das melhorias e detectar regressões.

**Critérios de aceite:**
- [ ] Script `scripts/audit_extraction_quality.py` com breakdown por ano/dia/caderno/extrator
- [ ] Métricas: % placeholders, % headers residuais, % cascata, % cid tokens, taxa deduplicação
- [ ] Targets: 0% placeholders, 0% headers, 0% cascata, 0% cid, ~80% dedup
- [ ] Relatório markdown gerado automaticamente após cada execução
- [ ] Golden set atualizado com alternativas e gabaritos validados manualmente
