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
