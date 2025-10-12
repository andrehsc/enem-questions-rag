# Ì∑ô BMad Guide: Developer Agents

## Ì≥ã **Metadados**

| Campo | Valor |
|-------|--------|
| Vers√£o | 1.0 |
| Audience | Developer Agents (AI/Human) |
| Projeto | ENEM Questions RAG |
| Status | Ì¥¥ **MANDAT√ìRIO** |
| Atualizado | 2024-10-12 |

## ÌæØ **Objetivos**

Este guia BMad estabelece **regras n√£o-negoci√°veis** para agentes desenvolvedores, focando em:

- Ìª°Ô∏è **Preven√ß√£o**: Eliminar problemas de encoding recorrentes
- Ì¥Ñ **Efici√™ncia**: Maximizar reuso de c√≥digo e infraestrutura
- Ì∞≥ **Consist√™ncia**: Manter padr√£o Docker-first
- Ì≥à **Qualidade**: Garantir manutenibilidade e documenta√ß√£o

---

## Ì≥ñ **Se√ß√£o 1: Encoding Seguro**

### Ì∫´ **Anti-Patterns (Proibido)**

```bash
# ‚ùå NUNCA FAZER
cat > arquivo.py << EOF
echo "c√≥digo" > script.py
```

### ‚úÖ **Patterns Obrigat√≥rios**

```python
# Headers obrigat√≥rios em TODO arquivo Python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descri√ß√£o do m√≥dulo
"""
```

### Ì¥ß **Ferramentas Aprovadas**

- `replace_string_in_file` ‚Üí Para modificar arquivos Python
- `write_file` ‚Üí Para criar novos arquivos Python
- Sempre validar encoding UTF-8

---

## Ì≥ñ **Se√ß√£o 2: Reuso Priorit√°rio**

### Ì¥ç **Workflow de Investiga√ß√£o**

**SEQU√äNCIA OBRIGAT√ìRIA antes de criar qualquer c√≥digo:**

```bash
1. list_dir ‚Üí Mapear estrutura existente
2. grep_search ‚Üí Buscar implementa√ß√µes similares
3. semantic_search ‚Üí Encontrar c√≥digo relacionado
4. read_file ‚Üí Analisar implementa√ß√µes
```

### ÌøóÔ∏è **Hierarquia de Reuso**

| Prioridade | Tipo | A√ß√£o |
|------------|------|------|
| P1 | Scripts existentes | Modificar/expandir |
| P2 | Configura√ß√µes Docker | Usar docker-compose.yml |
| P3 | Conex√µes DB | Reusar DatabaseIntegration |
| P4 | APIs/GraphQL | Expandir schemas |
| P5 | Test Suites | Adicionar aos existentes |

### Ì≥ù **Documenta√ß√£o Obrigat√≥ria**

- **README.md** ‚Üí Atualizar com mudan√ßas
- **Coment√°rios** ‚Üí Documentar modifica√ß√µes
- **Examples** ‚Üí Incluir casos de uso
- **API Docs** ‚Üí Atualizar quando relevante

---

## Ì≥ñ **Se√ß√£o 3: Docker-First Environment**

### Ì∞≥ **Containers Dispon√≠veis**

```yaml
teachershub-enem-postgres:
  port: 5433
  user: enem_rag_service
  database: teachershub_enem

enem-api (quando ativo):
  port: 8001
  type: FastAPI + GraphQL
```

### ‚úÖ **Workflow Correto**

```bash
# 1. Status check
docker ps

# 2. Start services
docker-compose up -d

# 3. Execute inside containers
docker exec -it teachershub-enem-postgres psql -U enem_rag_service -d teachershub_enem

# 4. Debug with logs
docker logs teachershub-enem-postgres
```

### Ì∫´ **Comportamentos Proibidos**

- ‚ùå Aplica√ß√µes na m√°quina local sem justificativa
- ‚ùå Instalar deps localmente quando h√° containers
- ‚ùå Ignorar containers funcionais
- ‚ùå Criar inst√¢ncias duplicadas

### ‚ùì **Exce√ß√µes (Confirmar Sempre)**

> **Pergunta obrigat√≥ria**: "Devo executar fora do Docker?"

- Scripts de an√°lise espec√≠ficos
- Ferramentas pontuais de desenvolvimento

---

## Ì≥ñ **Se√ß√£o 4: Quality Gates**

### Ì≥ã **Checklist Pr√©-Commit**

- [ ] **Encoding**: Headers UTF-8 presentes?
- [ ] **Reuso**: Implementa√ß√µes existentes investigadas?
- [ ] **Docker**: Testes executados em containers?
- [ ] **Docs**: README/coment√°rios atualizados?
- [ ] **Performance**: Impacto validado?

### ÌøóÔ∏è **Ferramentas de Valida√ß√£o**

```bash
# Executar antes de commit
python scripts/validate_environment.py
```

### Ì≥ä **M√©tricas de Qualidade**

| M√©trica | Target | Ferramenta |
|---------|--------|------------|
| Encoding Coverage | 100% | validate_environment.py |
| Docker Usage | 95% | Manual review |
| Documentation | 90% | README updates |

---

## Ì≥ñ **Se√ß√£o 5: Recursos do Projeto**

### Ìª†Ô∏è **Scripts Utilit√°rios Prontos**

```bash
reprocess_2024_data.py          # Reprocessamento otimizado
analyze_2024_quality.py         # An√°lise de qualidade
test_parser_2024.py            # Testes 2024
test_day2_parser.py            # Testes matem√°tica/ci√™ncias
```

### Ì∑ÑÔ∏è **Database Schema**

```sql
enem_questions.exam_metadata       # Metadados dos exames
enem_questions.questions           # Quest√µes extra√≠das
enem_questions.question_alternatives # Alternativas A-E
enem_questions.answer_keys         # Gabaritos oficiais
```

### Ì∑™ **Test Suites**

```python
tests/test_parser.py              # Parser principal
tests/test_text_normalizer.py     # Normaliza√ß√£o
tests/test_*.py                   # Suites especializadas
```

---

## Ì∫® **Enforcement**

### ‚ö†Ô∏è **Status das Regras**

**ESTAS DIRETRIZES S√ÉO MANDAT√ìRIAS - N√ÉO S√ÉO SUGEST√ïES**

### Ì¥í **Consequ√™ncias**

- Contribui√ß√µes n√£o-conformes ser√£o **rejeitadas**
- Corre√ß√£o obrigat√≥ria antes da aceita√ß√£o
- Review adicional para viola√ß√µes recorrentes

### Ì∂ò **Suporte**

1. Consultar `README.md` para contexto
2. Analisar exemplos similares no projeto
3. **Perguntar sempre em caso de d√∫vida**

---

**Ì∑ô BMad Master - Maximizando efici√™ncia atrav√©s de padr√µes consistentes**
