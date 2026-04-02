# Story: Ingestão automatizada de provas do ENEM

**Issue Reference:** [#5](https://github.com/andrehsc/enem-questions-rag/issues/5)  
**Status:** Draft  
**Agent Model Used:** GitHub Copilot  
**Created:** 2025-10-10

## Story

Como desenvolvedor,
Quero um pipeline automatizado para baixar e estruturar as provas dos últimos 5 anos do ENEM (PDF ou HTML do INEP),
Para que as questões fiquem disponíveis em uma base PostgreSQL para uso semântico e futuro registro no TeachersHub.

## Acceptance Criteria

- [ ] Pipeline realiza download dos arquivos do INEP
- [ ] Parsing e extração das questões, alternativas, gabaritos e metadados
- [ ] Armazenamento dos dados em tabelas otimizadas no PostgreSQL
- [ ] Testes unitários para parsing e ingestão
- [ ] Documentação do fluxo de ingestão

## Dev Notes

- Preferência por C# ou Python (compatibilidade com Semantic Kernel)
- Usar PostgreSQL para persistência (compatibilidade com TeachersHub)
- Foco nos últimos 5 anos do ENEM
- Dados públicos do INEP (PDFs ou HTML)
- Preparar para integração futura com Ollama e RAG

## Tasks

- [x] **Task 1: Configurar estrutura do projeto**
  - [x] Criar estrutura de diretórios
  - [x] Configurar ambiente Python/C#
  - [x] Configurar conexão PostgreSQL
  - [x] Configurar dependências (requests, psycopg2, etc.)

- [x] **Task 2: Implementar pipeline de download**
  - [x] Pesquisar URLs dos arquivos ENEM no INEP
  - [x] Implementar download automatizado
  - [x] Implementar cache para evitar re-downloads
  - [x] Validar integridade dos arquivos baixados

- [ ] **Task 3: Implementar parser de questões**
  - [ ] Analisar estrutura dos PDFs/HTML do ENEM
  - [ ] Extrair questões, alternativas e gabaritos
  - [ ] Extrair metadados (ano, disciplina, contexto)
  - [ ] Normalizar dados para estrutura consistente

- [ ] **Task 4: Configurar banco PostgreSQL**
  - [ ] Criar schema otimizado para questões
  - [ ] Implementar tabelas para questões, alternativas, gabaritos
  - [ ] Configurar índices para performance
  - [ ] Preparar campos para embeddings futuros

- [ ] **Task 5: Implementar ingestão no banco**
  - [ ] Conectar parser ao PostgreSQL
  - [ ] Implementar inserção em batch
  - [ ] Validar dados antes da inserção
  - [ ] Tratar duplicatas e atualizações

- [ ] **Task 6: Implementar testes**
  - [ ] Testes unitários para parser
  - [ ] Testes de integração com banco
  - [ ] Testes do pipeline completo
  - [ ] Testes de performance

- [ ] **Task 7: Documentar solução**
  - [ ] Documentar arquitetura da solução
  - [ ] Documentar fluxo de ingestão
  - [ ] Documentar schema do banco
  - [ ] Criar README com instruções de uso

## Testing
- [ ] Parser extrai dados corretamente dos PDFs/HTML
- [ ] Pipeline completa sem erros para amostra de dados
- [ ] Dados inseridos no PostgreSQL com integridade
- [ ] Performance adequada para volumes esperados
- [ ] Testes automatizados passam

## Dev Agent Record

### Debug Log References
- Initial setup and environment configuration
- INEP data source research and analysis
- PostgreSQL schema design decisions
- Parser implementation challenges
- Performance optimization strategies

### Completion Notes
- [ ] All tasks completed with tests passing
- [ ] Documentation updated and comprehensive
- [ ] Database schema optimized for future RAG integration
- [ ] Code follows project standards and best practices

### File List

**Core Configuration & Structure:**
- `src/enem_ingestion/config.py` - Configuration management
- `src/enem_ingestion/database.py` - Database models and connection management
- `src/enem_ingestion/downloader.py` - ENEM file download module with caching
- `src/enem_ingestion/web_scraper.py` - Dynamic URL discovery from INEP website
- `src/enem_ingestion/__init__.py` - Package initialization
- `pyproject.toml` - Project configuration and dependencies
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore patterns
- `README.md` - Project documentation

**Scripts:**
- `scripts/init_database.py` - Database initialization script
- `scripts/test_download.py` - Test and validate download functionality

**Tests:**
- `tests/__init__.py` - Test package
- `tests/test_config.py` - Configuration tests
- `tests/test_database.py` - Database model tests
- `tests/test_downloader.py` - Download functionality tests
- `tests/test_web_scraper.py` - Web scraping tests

**Directory Structure:**
- `src/enem_ingestion/` - Main source code
- `tests/` - Test files
- `scripts/` - Utility scripts
- `data/downloads/` - Download cache directory
- `data/cache/` - General cache directory
- `logs/` - Application logs
- `config/` - Configuration files

### Change Log

- 2025-10-10: Story created based on issue #5
- 2025-10-10: Task 1 completed - Project structure configured with Python environment, PostgreSQL database models, configuration management, and comprehensive testing setup
- 2025-10-10: Task 2 completed - Implemented complete download pipeline with web scraping for dynamic URL discovery, file caching, integrity validation, and comprehensive error handling