# Diretrizes para Agentes Desenvolvedores

## ÌæØ **Resumo Executivo**

Este documento estabelece regras **OBRIGAT√ìRIAS** para agentes desenvolvedores trabalhando no projeto ENEM Questions RAG. Estas diretrizes visam:

- Prevenir problemas de encoding recorrentes
- Maximizar reuso de c√≥digo e infraestrutura existente  
- Manter consist√™ncia no uso do ambiente Dockerizado
- Garantir qualidade e manutenibilidade do c√≥digo

## Ì≥ä **Ferramentas e Infraestrutura Dispon√≠vel**

### Ì∞≥ **Docker Environment**
```yaml
Servi√ßos Ativos:
- PostgreSQL: localhost:5433 (teachershub-enem-postgres)
- Redis: localhost:6380 (se configurado)
- API: localhost:8001 (FastAPI + GraphQL)
```

### Ì∑ÑÔ∏è **Database Schema**
```sql
enem_questions.exam_metadata     # Metadados dos exames
enem_questions.questions         # Quest√µes extra√≠das
enem_questions.question_alternatives # Alternativas A-E
enem_questions.answer_keys       # Gabaritos oficiais
```

### Ìª†Ô∏è **Scripts Utilit√°rios Prontos**
```bash
reprocess_2024_data.py          # Reprocessamento com parser otimizado
analyze_2024_quality.py         # An√°lise de qualidade dos dados
test_parser_2024.py            # Testes espec√≠ficos para 2024
test_day2_parser.py            # Testes para quest√µes de matem√°tica/ci√™ncias
full_ingestion_report.py       # Ingest√£o completa com relat√≥rios
```

### Ì∑™ **Test Suites Existentes**
```python
tests/test_parser.py           # Testes do parser principal
tests/test_text_normalizer.py  # Testes de normaliza√ß√£o
tests/test_*.py               # Testes especializados
```

## Ì¥Ñ **Workflow de Investiga√ß√£o Obrigat√≥rio**

**ANTES DE CRIAR QUALQUER C√ìDIGO NOVO:**

```bash
# 1. Verificar estrutura existente
list_dir /caminho/relevante

# 2. Buscar implementa√ß√µes similares
grep_search "fun√ß√£o_similar|classe_similar" --recursive

# 3. Busca sem√¢ntica por funcionalidades
semantic_search "funcionalidade desejada"

# 4. Analisar c√≥digo existente
read_file arquivo_relevante.py
```

## Ì∞≥ **Docker-First Workflow**

### ‚úÖ **Sequ√™ncia Correta:**

```bash
# 1. Verificar containers ativos
docker ps

# 2. Subir ambiente se necess√°rio
docker-compose up -d

# 3. Executar testes/an√°lises no container
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem

# 4. Validar mudan√ßas no ambiente containerizado
```

### ‚ùå **Evitar:**
- Instalar depend√™ncias na m√°quina local
- Subir aplica√ß√µes fora do Docker sem justificativa
- Ignorar containers existentes

## Ì≥Å **Exemplos de Reuso Correto**

### Exemplo 1: Nova An√°lise de Dados
```python
# ‚ùå ERRADO: Criar nova conex√£o
def nova_analise():
    conn = psycopg2.connect("postgresql://...")
    
# ‚úÖ CORRETO: Reusar DatabaseIntegration
from src.enem_ingestion.db_integration_final import DatabaseIntegration

def nova_analise():
    db = DatabaseIntegration()  # Reusa conex√£o existente
```

### Exemplo 2: Novo Teste
```python
# ‚ùå ERRADO: Criar teste isolado
def test_nova_funcionalidade():
    # c√≥digo duplicado...

# ‚úÖ CORRETO: Expandir suite existente
# Adicionar em tests/test_parser.py
class TestParser:
    def test_nova_funcionalidade(self):
        # reusar setup existente
```

## ÌæØ **Checklist de Valida√ß√£o**

Antes de qualquer commit:

- [ ] **Encoding**: Headers UTF-8 em arquivos Python?
- [ ] **Reuso**: Investiguei implementa√ß√µes existentes?
- [ ] **Docker**: Testei no ambiente containerizado?
- [ ] **Documenta√ß√£o**: Atualizei coment√°rios/README?
- [ ] **Performance**: Validei impacto nos dados existentes?

## Ì∫® **Red Flags - Comportamentos que Geram Rejei√ß√£o**

1. **Criar arquivos Python via terminal** (`cat`, `echo`)
2. **Duplicar funcionalidades** sem investigar existentes
3. **Testar fora do Docker** sem justificativa
4. **N√£o documentar** modifica√ß√µes significativas
5. **Quebrar compatibilidade** com dados existentes

## Ì≤° **Dicas de Produtividade**

### Comandos √öteis
```bash
# Verificar logs do PostgreSQL
docker logs teachershub-enem-postgres

# Conectar diretamente ao banco
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem

# Verificar tamanho da base
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'enem_questions' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Padr√µes de C√≥digo
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module description
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)
```

---

**Estas diretrizes s√£o OBRIGAT√ìRIAS e aplicam-se a todos os agentes desenvolvedores.**
