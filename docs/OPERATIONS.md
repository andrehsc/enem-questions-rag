# ENEM RAG System - Operations Guide

## Deploy em Produção

### Pré-requisitos
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM disponível
- 20GB espaço em disco

### Deploy Inicial
```bash
# 1. Clone do repositório
git clone https://github.com/andrehsc/enem-questions-rag.git
cd enem-questions-rag

# 2. Configuração de ambiente
cp .env.example .env
# Editar .env com configurações de produção

# 3. Deploy completo
docker-compose up -d

# 4. Verificar saúde dos serviços
docker-compose ps
curl http://localhost:8000/health
```

### Monitoramento

#### Health Checks
```bash
# API
curl http://localhost:8000/health

# PostgreSQL
docker exec enem-postgres pg_isready -U postgres

# Redis
docker exec enem-redis redis-cli ping
```

#### Logs
```bash
# Logs da API
docker-compose logs -f api

# Logs do PostgreSQL
docker-compose logs -f postgres

# Logs do Redis
docker-compose logs -f redis
```

#### Métricas
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
- **API Metrics**: http://localhost:8000/metrics

### Backup e Recovery

#### Backup Manual
```bash
# Executar backup
docker exec enem-postgres pg_dump -U postgres enem_rag > backup_$(date +%Y%m%d).sql

# Backup com compressão
docker exec enem-postgres pg_dump -U postgres enem_rag | gzip > backup_$(date +%Y%m%d).sql.gz
```

#### Backup Automatizado
```bash
# Configurar cron job
0 2 * * * /path/to/scripts/backup/backup.sh
```

#### Restore
```bash
# Restaurar backup
docker exec -i enem-postgres psql -U postgres -d enem_rag < backup.sql

# Restaurar backup comprimido
gunzip -c backup.sql.gz | docker exec -i enem-postgres psql -U postgres -d enem_rag
```

### Manutenção

#### Atualização da Aplicação
```bash
# 1. Backup antes da atualização
./scripts/backup/backup.sh

# 2. Pull das mudanças
git pull origin main

# 3. Rebuild e restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. Verificar health
curl http://localhost:8000/health
```

#### Limpeza de Cache
```bash
# Limpar cache Redis
docker exec enem-redis redis-cli FLUSHDB

# Restart do Redis
docker-compose restart redis
```

#### Otimização do Banco
```bash
# Análise das tabelas
docker exec enem-postgres psql -U postgres -d enem_rag -c "ANALYZE;"

# Verificar índices
docker exec enem-postgres psql -U postgres -d enem_rag -f /app/database/optimize-search.sql
```

### Troubleshooting

#### API não responde
```bash
# Verificar status
docker-compose ps api

# Verificar logs
docker-compose logs api

# Restart do serviço
docker-compose restart api
```

#### Erro de conexão com banco
```bash
# Verificar PostgreSQL
docker-compose logs postgres

# Verificar conectividade
docker exec api ping postgres

# Restart do PostgreSQL
docker-compose restart postgres
```

#### Cache Redis com problemas
```bash
# Verificar Redis
docker-compose logs redis

# Testar conexão
docker exec api ping redis

# Restart do Redis
docker-compose restart redis
```

### Alertas e Notificações

#### Configurar Alertas
- CPU > 80%
- Memória > 90%
- Disco > 85%
- API response time > 2s
- Database connections > 80%

#### Canais de Notificação
- Email: admin@empresa.com
- Slack: #alerts
- PagerDuty: production-alerts

### Security

#### Configurações de Segurança
```bash
# Alterar senhas padrão
# Configurar firewall
# Habilitar SSL/TLS
# Configurar rate limiting
```

#### Backup de Segurança
- Backups criptografados
- Armazenamento off-site
- Testes de restore regulares

### Performance Tuning

#### PostgreSQL
```sql
-- Configurações de performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

#### Redis
```bash
# Configurações de memória
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Disaster Recovery

#### Plano de Contingência
1. **RTO**: 30 minutos
2. **RPO**: 4 horas
3. **Backup locations**: Local + Cloud
4. **Contacts**: Lista de emergência

#### Procedimento de Recovery
1. Avaliar extensão do problema
2. Notificar equipe
3. Restaurar do backup mais recente
4. Verificar integridade dos dados
5. Testar funcionalidades críticas
6. Comunicar restauração

### Contacts

- **SysAdmin**: admin@empresa.com
- **DevOps**: devops@empresa.com
- **On-call**: +55 11 99999-9999
