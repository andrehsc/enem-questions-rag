# ��� Guia de Troubleshooting - Docker & API

## ��� Problemas Comuns e Soluções

### 1. Docker não está funcionando

**Sintomas:**
- `docker: command not found`
- `Cannot connect to the Docker daemon`
- `request returned 500 Internal Server Error`

**Soluções:**
```bash
# Windows: Reiniciar Docker Desktop
# 1. Fechar Docker Desktop completamente
# 2. Abrir como Administrador
# 3. Aguardar inicialização completa (ícone verde)

# Verificar se está rodando
docker info

# Se não funcionar, reiniciar serviços (PowerShell como Admin)
Restart-Service *docker*
```

### 2. Containers não sobem

**Sintomas:**
- `docker-compose up` falha
- Containers ficam em status "Exited"

**Soluções:**
```bash
# Limpar tudo e recomeçar
docker-compose down -v
docker system prune -f
docker volume prune -f

# Reconstruir containers
docker-compose up --build

# Ver logs de erro específicos
docker-compose logs postgres
docker-compose logs api
docker-compose logs redis
```

### 3. API não responde

**Sintomas:**
- `Connection refused` ao acessar http://localhost:8000
- API container em status "Restarting"

**Diagnóstico:**
```bash
# Verificar logs da API
docker-compose logs api

# Verificar se PostgreSQL está ready
docker-compose exec postgres pg_isready -U postgres

# Verificar conectividade dentro do container
docker-compose exec api ping postgres
docker-compose exec api ping redis

# Testar manualmente dentro do container
docker-compose exec api python -c "
import psycopg2
try:
    conn = psycopg2.connect(host='postgres', user='postgres', password='postgres123', database='enem_rag')
    print('✅ PostgreSQL OK')
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL Error: {e}')
"
```

### 4. PostgreSQL não inicializa

**Sintomas:**
- Postgres container para logo após iniciar
- Erro "database system is starting up"

**Soluções:**
```bash
# Verificar logs do PostgreSQL
docker-compose logs postgres

# Limpar dados do PostgreSQL (CUIDADO: apaga dados)
docker-compose down -v
docker volume rm enem-questions-rag_postgres_data

# Verificar permissões do arquivo init
ls -la database/complete-init.sql

# Recriar container
docker-compose up postgres
```

### 5. Redis não conecta

**Sintomas:**
- API não consegue conectar ao Redis
- Cache não está funcionando

**Soluções:**
```bash
# Verificar Redis
docker-compose exec redis redis-cli ping

# Verificar logs
docker-compose logs redis

# Testar conectividade
docker-compose exec api python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('✅ Redis OK')
except Exception as e:
    print(f'❌ Redis Error: {e}')
"
```

### 6. Problemas de performance

**Sintomas:**
- API muito lenta
- Containers consumindo muita CPU/RAM

**Soluções:**
```bash
# Verificar uso de recursos
docker stats

# Limitar recursos no docker-compose.yml
# Adicionar:
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'

# Verificar espaço em disco
docker system df
```

## ���️ Scripts de Diagnóstico

### Script Automatizado
```bash
# Executar diagnóstico completo
python docker-troubleshoot.py

# Ou usar script bash
./start-docker.sh
```

### Comandos Manuais Essenciais

```bash
# Status geral
docker-compose ps
docker-compose logs -f

# Verificar saúde dos serviços
curl http://localhost:8000/health
docker-compose exec postgres pg_isready -U postgres
docker-compose exec redis redis-cli ping

# Reiniciar serviço específico
docker-compose restart api
docker-compose restart postgres
docker-compose restart redis

# Acessar containers
docker-compose exec api bash
docker-compose exec postgres psql -U postgres -d enem_rag
docker-compose exec redis redis-cli

# Limpar completamente
docker-compose down -v
docker system prune -a -f --volumes
```

## ��� Monitoramento

### Health Checks
- **API**: http://localhost:8000/health
- **PostgreSQL**: `docker-compose exec postgres pg_isready -U postgres`
- **Redis**: `docker-compose exec redis redis-cli ping`

### Logs importantes
```bash
# API startup
docker-compose logs api | grep "startup complete"

# PostgreSQL ready
docker-compose logs postgres | grep "ready to accept connections"

# Redis startup
docker-compose logs redis | grep "Ready to accept connections"
```

### Portas utilizadas
- **8000**: FastAPI
- **5432**: PostgreSQL
- **6379**: Redis

## ��� Quick Start Garantido

Se nada funcionar, execute esta sequência:

```bash
# 1. Parar tudo
docker-compose down -v

# 2. Limpar Docker completamente
docker system prune -a -f --volumes

# 3. Verificar se Docker está OK
docker info

# 4. Se erro, reiniciar Docker Desktop e aguardar

# 5. Subir infraestrutura
docker-compose up -d

# 6. Aguardar 60 segundos para inicialização completa

# 7. Verificar
docker-compose ps
curl http://localhost:8000/health
```

## ��� Suporte

Se os problemas persistirem:

1. Executar: `python docker-troubleshoot.py` (opção 8 - diagnóstico completo)
2. Coletar logs: `docker-compose logs > debug.log`
3. Verificar versões: `docker --version && docker-compose --version`
4. Reportar issue com os logs coletados
