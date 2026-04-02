# ENEM Questions RAG System

Sistema RAG (Retrieval-Augmented Generation) completo para questões do ENEM 2020-2024 com extração e processamento de imagens, integrado à plataforma educacional TeachersHub.

## Status do Sistema

**Sistema Totalmente Funcional**
- 108 PDFs ENEM processados (2020-2024)
- 54 exames | 2.532 questões | 12.660 alternativas | 4.856 gabaritos | 1.417 imagens
- Performance otimizada: 8 workers paralelos, batch size 12
- Sistema completo de backups e restauração

## Roadmap RAG Pipeline

| Épico | Descrição | Status |
|-------|-----------|--------|
| Épico 1 | Fundação Vetorial — pgvector + Chunk Builder | Concluído |
| Épico 2 | Pipeline de Embeddings — Geração e Ingestão | Concluído |
| Épico 3 | Busca Semântica — Feature 1 | Draft |
| Épico 4 | Geração com RAG — Features 2 e 3 | Draft |

> **Arquitetura:** [`_bmad-output/planning-artifacts/architecture.md`](_bmad-output/planning-artifacts/architecture.md)
> **Epics & Stories:** [`_bmad-output/planning-artifacts/epics.md`](_bmad-output/planning-artifacts/epics.md)
> **Implementation Artifacts:** [`_bmad-output/implementation-artifacts/`](_bmad-output/implementation-artifacts/)

## Arquitetura

```
enem-questions-rag/
├── teachershub-integration/     # Codigo .NET integracao TeachersHub
│   ├── TeachersHub.ENEM.Api/    # Controllers e middleware
│   ├── TeachersHub.ENEM.Core/   # Business logic
│   └── TeachersHub.ENEM.Data/   # Data access layer
├── python-ml-services/          # Microsservicos Python ML/RAG
│   ├── rag-service/             # RAG e analise semantica (Epic 3)
│   ├── semantic-search/         # Busca inteligente
│   └── content-generation/      # Suporte IA generativa
├── src/enem_ingestion/          # Core do sistema de ingestao
│   ├── database_integration.py  # Conexao e operacoes com PostgreSQL
│   ├── pdf_processor.py         # Processamento de PDFs
│   ├── content_extractor.py     # Extracao de questoes e alternativas
│   └── image_extractor.py       # Extracao e processamento de imagens
├── scripts/                     # Scripts de execucao
│   ├── full_ingestion_report.py # Ingestao completa com relatorios
│   └── test_*.py               # Scripts de teste e validacao
├── data/
│   ├── downloads/              # PDFs ENEM organizados por ano
│   └── extracted_images/       # Imagens extraidas (ignorado no git)
├── shared/                      # Recursos compartilhados
│   ├── docker/                  # Dockerfiles
│   ├── database/                # Scripts SQL
│   └── monitoring/              # Configs observabilidade
├── backups/                    # Backups completos do sistema
├── docs/                        # Documentacao tecnica e stories
└── docker-compose.yml          # PostgreSQL + servicos containerizados
```

## Quick Start

### 1. Configuracao do Ambiente

```bash
# Clone o repositorio
git clone https://github.com/andrehsc/enem-questions-rag.git
cd enem-questions-rag

# Instale dependencias Python
pip install -r requirements.txt

# Inicie os servicos
docker-compose up -d
```

### 2. Execute a Ingestao Completa

```bash
# Processamento completo com relatorios
python scripts/full_ingestion_report.py
```

### 3. Verifique os Resultados

```bash
# Teste a extracao de imagens
python scripts/test_image_extraction.py

# Validacao completa do sistema
python scripts/test_complete_ingestion.py
```

## Performance e Otimizacoes

- **Processamento Paralelo**: 8 workers simultaneos
- **Batch Processing**: Lotes de 12 itens para operacoes em massa
- **Deduplicacao**: Hash MD5 para evitar imagens duplicadas
- **Conversao de Cores**: CMYK → RGB automatica para compatibilidade
- **Coordenadas**: Ordenacao por posicao Y para sequencia correta

## Schema do Banco de Dados

```sql
-- Schema: enem_questions
CREATE TABLE exam_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE,
    year INTEGER,
    exam_type VARCHAR(50),
    day INTEGER,
    color_code VARCHAR(10)
);

CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    exam_id INTEGER REFERENCES exam_metadata(id),
    question_number INTEGER,
    question_text TEXT,
    subject VARCHAR(100)
);

CREATE TABLE alternatives (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    letter CHAR(1),
    text TEXT
);

CREATE TABLE answer_keys (
    id SERIAL PRIMARY KEY,
    exam_id INTEGER REFERENCES exam_metadata(id),
    question_number INTEGER,
    correct_answer CHAR(1)
);

CREATE TABLE question_images (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    image_filename VARCHAR(255),
    image_path VARCHAR(500),
    page_number INTEGER,
    image_hash VARCHAR(32)
);
```

## Sistema de Backups

### Backup Completo
```bash
# Dentro do container
docker-compose exec postgres pg_dump -U postgres -d enem_questions > backup_complete.sql

# Restauracao
docker-compose exec -T postgres psql -U postgres -d enem_questions < backup_complete.sql
```

### Backups Disponiveis
- `backups/2025-01-11/enem_questions_complete_backup.sql` (146MB)
- `backups/2025-01-11/enem_questions_schema_only.sql` (9.1KB)
- Script automatizado: `backups/2025-01-11/restore_backup.sh`

## Processamento de Imagens

O sistema extrai imagens automaticamente durante a ingestao:

```python
# Configuracao da extracao
image_extractor = ImageExtractor(
    output_dir="data/extracted_images",
    database_config={
        'host': 'localhost',
        'port': 5433,
        'user': 'postgres',
        'password': 'postgres123',
        'database': 'enem_questions'
    }
)

# Extracao com conversao CMYK->RGB
images = image_extractor.extract_images_from_pdf(pdf_path, exam_id)
```

## Tecnologias Utilizadas

- **Python 3.8+**: Linguagem principal pipeline de ingestao
- **PostgreSQL 16**: Banco de dados principal
- **Docker & Docker Compose**: Containerizacao
- **PyMuPDF (fitz)**: Processamento de PDFs
- **Pillow (PIL)**: Processamento de imagens
- **ThreadPoolExecutor**: Processamento paralelo
- **FastAPI**: Framework API para microsservicos Python
- **sentence-transformers**: Embeddings semanticos (Epic 3)
- **pgvector**: Extensao PostgreSQL para busca vetorial semantica (Epic 3)
- **Redis**: Cache de embeddings e performance
- **.NET 8 / ASP.NET Core**: Backend TeachersHub Integration
- **React/TypeScript**: Frontend TeachersHub
- **Semantic Kernel**: Integracao IA generativa .NET (Epic 4)

## Casos de Uso

1. **Analise de Questoes**: Consultas SQL complexas sobre padroes das questoes
2. **Sistema RAG**: Base de conhecimento para LLMs com busca semantica
3. **Analise de Imagens**: Processamento de graficos e diagramas
4. **Estudos Estatisticos**: Analise longitudinal das provas ENEM
5. **Aplicacoes Educacionais**: Sistemas de ensino adaptativos com TeachersHub

## Estatisticas Detalhadas

| Metrica | Valor |
|---------|-------|
| **Anos Cobertos** | 2020-2024 |
| **Total de Arquivos** | 108 PDFs |
| **Provas Processadas** | 54 exames |
| **Questoes Extraidas** | 2.532 questoes |
| **Alternativas** | 12.660 opcoes |
| **Gabaritos** | 4.856 respostas |
| **Imagens Processadas** | 1.417 imagens |
| **Tamanho do Backup** | 146MB |

## Contribuicao

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudancas (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licenca

Este projeto esta sob a licenca MIT. Veja o arquivo `LICENSE` para mais detalhes.

## Links Uteis

- [INEP - Instituto Nacional de Estudos e Pesquisas Educacionais](https://www.gov.br/inep/pt-br)
- [Provas e Gabaritos ENEM](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

---

## BMad Guide: Developer Agents

### Regras Mandatorias para Agentes

> **Guia Completo**: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md)
> **Quick Reference**: [`docs/development/QUICK_REFERENCE.md`](docs/development/QUICK_REFERENCE.md)

| Nunca Fazer | Sempre Fazer |
|---------------------|----------------------|
| `cat > arquivo.py` | `replace_string_in_file` |
| Apps fora do Docker | `docker exec -it container` |
| Criar sem investigar | `list_dir, grep_search, semantic_search` |

### Core Principles

1. **Encoding Seguro**: Headers UTF-8 obrigatorios em Python
2. **Reuso Prioritario**: Investigar antes de criar qualquer codigo
3. **Docker First**: Containers para todos os testes e validacoes

### Ambiente de Desenvolvimento

```bash
# Verificar containers ativos
docker ps

# Subir ambiente completo
docker-compose up -d

# Conectar ao PostgreSQL
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem

# Logs dos servicos
docker logs teachershub-enem-postgres
```

### Estrutura do Codigo

```
src/enem_ingestion/
├── parser.py              # Parser otimizado com 4 estrategias
├── db_integration_final.py # Integracao com banco melhorada
└── text_normalizer.py     # Normalizacao de texto

tests/
├── test_parser.py         # Testes do parser
├── test_text_normalizer.py # Testes de normalizacao
└── test_*.py             # Suites especializadas
```

### Scripts Utilitarios

```bash
# Reprocessar dados 2024
python reprocess_2024_data.py

# Analise de qualidade
python analyze_2024_quality.py

# Testes especificos
python test_parser_2024.py
python test_day2_parser.py
```

---

**Desenvolvido com dedicacao para a comunidade educacional brasileira**
