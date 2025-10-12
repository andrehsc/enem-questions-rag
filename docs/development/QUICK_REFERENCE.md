# Ì∑ô BMad Quick Reference: Developer Agents

> ‚ö° **Fast lookup para regras cr√≠ticas**

## Ì∫´ **NUNCA FAZER**

```bash
‚ùå cat > arquivo.py << EOF
‚ùå echo "c√≥digo" > script.py  
‚ùå python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
‚ùå pip install nova_dependencia
```

## ‚úÖ **SEMPRE FAZER**

```bash
‚úÖ replace_string_in_file
‚úÖ docker ps
‚úÖ docker exec -it teachershub-enem-postgres
‚úÖ list_dir, grep_search, semantic_search, read_file
```

## Ì∞≥ **Containers Ativos**

```yaml
teachershub-enem-postgres: 5433
enem-api: 8001 (se ativo)
```

## Ì≥ã **Checklist R√°pido**

- [ ] Headers UTF-8 em Python?
- [ ] Investigou c√≥digo existente?
- [ ] Testou no Docker?
- [ ] Atualizou documenta√ß√£o?

## Ì∂ò **Em D√∫vida?**

> **Pergunta**: "Devo executar fora do Docker?"
> **Resposta padr√£o**: N√£o, use containers

---

**Ì∑ô BMad Master - Padr√µes consistentes, resultados excepcionais**
