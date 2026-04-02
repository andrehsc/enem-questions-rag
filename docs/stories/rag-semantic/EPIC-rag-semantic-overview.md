# Epic 3: Capacidades RAG e Análise Semântica — Overview

## Objetivo

Implementa funcionalidades avançadas de inteligência artificial aproveitando os microsserviços Python existentes para análise semântica, busca inteligente baseada em RAG, e sistema de recomendações de questões relacionadas, tudo integrado perfeitamente ao frontend TeachersHub para uma experiência de usuário enriquecida.

## Stories

| Story | Título | Dependências | Status |
|-------|--------|--------------|--------|
| [3.1](3.1.microsservico-rag.md) | Microsserviço RAG | Épico 1 completo | Draft |
| [3.2](3.2.busca-semantica-integrada.md) | Busca Semântica Integrada | Story 3.1, Stories 2.2, 2.3 | Draft |
| [3.3](3.3.sistema-recomendacoes.md) | Sistema de Recomendações | Story 3.1, Story 2.3 | Draft |

## Dependências do Épico

- **Épico 1 completo** — ambiente híbrido Docker, JWT auth, comunicação inter-serviços
- **Épico 2 parcial** — Stories 2.2 (endpoints REST) e 2.3 (interface de busca básica)

## Decisões Técnicas

### Modelo de Embedding
- `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- Suporte nativo a português brasileiro
- Dimensão 384, balanceia performance e qualidade

### Vector Store
- pgvector no PostgreSQL compartilhado (tabela `question_embeddings`, coluna `embedding vector(384)`)
- Índice HNSW via pgvector para busca aproximada eficiente (`CREATE INDEX ... USING hnsw`)

### Cache Strategy
- Redis para cache de resultados de busca (TTL 1h)
- IMemoryCache .NET para proxy de recomendações (TTL 10min)
- Cache keys baseados em hash da query + filtros

### Resilience Pattern
- Circuit breaker no cliente .NET (abre após 5 falhas/30s)
- Retry policy: 3 tentativas com exponential backoff
- Timeout: 5 segundos por chamada ao RAG service
- Graceful degradation: busca simples disponível quando RAG indisponível

## NFRs do Épico

| NFR | Meta | Observações |
|-----|------|-------------|
| NFR3 | < 3s para consultas RAG | Cache Redis impacta positivamente |
| NFR1 | Sem degradação do TeachersHub | Chamadas assíncronas e circuit breaker |
| NFR2 | 100 professores simultâneos | Cache Redis alivia carga do modelo |

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-04-02 | 1.0 | Epic overview inicial | Scrum Master |
