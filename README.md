# ENEM Questions RAG System ���

Sistema RAG (Retrieval-Augmented Generation) completo para questões do ENEM 2020-2024 com extração e processamento de imagens.

## ��� Status do Sistema

✅ **Sistema Totalmente Funcional**
- 108 PDFs ENEM processados (2020-2024)
- 54 exames | 2.532 questões | 12.660 alternativas | 4.856 gabaritos | 1.417 imagens
- Performance otimizada: 8 workers paralelos, batch size 12
- Sistema completo de backups e restauração

## ���️ Arquitetura

```
enem-questions-rag/
├── src/enem_ingestion/          # Core do sistema de ingestão
│   ├── database_integration.py  # Conexão e operações com PostgreSQL
│   ├── pdf_processor.py         # Processamento de PDFs
│   ├── content_extractor.py     # Extração de questões e alternativas
│   └── image_extractor.py       # Extração e processamento de imagens
├── scripts/                     # Scripts de execução
│   ├── full_ingestion_report.py # Ingestão completa com relatórios
│   └── test_*.py               # Scripts de teste e validação
├── data/
│   ├── downloads/              # PDFs ENEM organizados por ano
│   └── extracted_images/       # Imagens extraídas (ignorado no git)
├── backups/                    # Backups completos do sistema
└── docker-compose.yml          # PostgreSQL containerizado
```

## ��� Quick Start

### 1. Configuração do Ambiente

```bash
# Clone o repositório
git clone https://github.com/andrehsc/enem-questions-rag.git
cd enem-questions-rag

# Instale dependências
pip install -r requirements.txt

# Inicie o PostgreSQL
docker-compose up -d
```

### 2. Execute a Ingestão Completa

```bash
# Processamento completo com relatórios
python scripts/full_ingestion_report.py
```

### 3. Verifique os Resultados

```bash
# Teste a extração de imagens
python scripts/test_image_extraction.py

# Validação completa do sistema
python scripts/test_complete_ingestion.py
```

## ��� Performance e Otimizações

- **Processamento Paralelo**: 8 workers simultâneos
- **Batch Processing**: Lotes de 12 itens para operações em massa
- **Deduplicação**: Hash MD5 para evitar imagens duplicadas
- **Conversão de Cores**: CMYK → RGB automática para compatibilidade
- **Coordenadas**: Ordenação por posição Y para sequência correta

## ���️ Schema do Banco de Dados

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

## ��� Sistema de Backups

### Backup Completo
```bash
# Dentro do container
docker-compose exec postgres pg_dump -U postgres -d enem_questions > backup_complete.sql

# Restauração
docker-compose exec -T postgres psql -U postgres -d enem_questions < backup_complete.sql
```

### Backups Disponíveis
- `backups/2025-01-11/enem_questions_complete_backup.sql` (146MB)
- `backups/2025-01-11/enem_questions_schema_only.sql` (9.1KB)
- Script automatizado: `backups/2025-01-11/restore_backup.sh`

## ���️ Processamento de Imagens

O sistema extrai imagens automaticamente durante a ingestão:

```python
# Configuração da extração
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

# Extração com conversão CMYK→RGB
images = image_extractor.extract_images_from_pdf(pdf_path, exam_id)
```

## ��� Tecnologias Utilizadas

- **Python 3.8+**: Linguagem principal
- **PostgreSQL 16**: Banco de dados principal
- **Docker & Docker Compose**: Containerização
- **PyMuPDF (fitz)**: Processamento de PDFs
- **Pillow (PIL)**: Processamento de imagens
- **ThreadPoolExecutor**: Processamento paralelo
- **Regex**: Extração de padrões de texto

## ��� Casos de Uso

1. **Análise de Questões**: Consultas SQL complexas sobre padrões das questões
2. **Sistema RAG**: Base de conhecimento para LLMs
3. **Análise de Imagens**: Processamento de gráficos e diagramas
4. **Estudos Estatísticos**: Análise longitudinal das provas ENEM
5. **Aplicações Educacionais**: Sistemas de ensino adaptativos

## ��� Estatísticas Detalhadas

| Métrica | Valor |
|---------|-------|
| **Anos Cobertos** | 2020-2024 |
| **Total de Arquivos** | 108 PDFs |
| **Provas Processadas** | 54 exames |
| **Questões Extraídas** | 2.532 questões |
| **Alternativas** | 12.660 opções |
| **Gabaritos** | 4.856 respostas |
| **Imagens Processadas** | 1.417 imagens |
| **Tamanho do Backup** | 146MB |

## ��� Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## ��� Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## ��� Links Úteis

- [INEP - Instituto Nacional de Estudos e Pesquisas Educacionais](https://www.gov.br/inep/pt-br)
- [Provas e Gabaritos ENEM](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

## 🧙 **BMad Guide: Developer Agents**

### 🎯 **Regras Mandatórias para Agentes**

> 📖 **Guia Completo**: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md)  
> ⚡ **Quick Reference**: [`docs/development/QUICK_REFERENCE.md`](docs/development/QUICK_REFERENCE.md)

| 🚫 **Nunca Fazer** | ✅ **Sempre Fazer** |
|---------------------|----------------------|
| `cat > arquivo.py` | `replace_string_in_file` |
| Apps fora do Docker | `docker exec -it container` |
| Criar sem investigar | `list_dir, grep_search, semantic_search` |

### 🔧 **Core Principles**

1. **🛡️ Encoding Seguro**: Headers UTF-8 obrigatórios em Python
2. **🔄 Reuso Prioritário**: Investigar antes de criar qualquer código
3. **🐳 Docker First**: Containers para todos os testes e validações

### 🏗️ **Ambiente de Desenvolvimento**

```bash
# Verificar containers ativos
docker ps

# Subir ambiente completo
docker-compose up -d

# Conectar ao PostgreSQL
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem

# Logs dos serviços
docker logs teachershub-enem-postgres
```

### 📚 **Estrutura do Código**

```
src/enem_ingestion/
├── parser.py              # Parser otimizado com 4 estratégias
├── db_integration_final.py # Integração com banco melhorada
└── text_normalizer.py     # Normalização de texto

tests/
├── test_parser.py         # Testes do parser
├── test_text_normalizer.py # Testes de normalização
└── test_*.py             # Suites especializadas
```

### 🚀 **Scripts Utilitários**

```bash
# Reprocessar dados 2024
python reprocess_2024_data.py

# Análise de qualidade
python analyze_2024_quality.py

# Testes específicos
python test_parser_2024.py
python test_day2_parser.py
```

---

**Desenvolvido com ❤️ para a comunidade educacional brasileira**
