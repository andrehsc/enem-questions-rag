# Development Credentials Reference
# ALWAYS USE THESE EXACT CREDENTIALS FOR CONSISTENCY

## Database Credentials
- **Main Database**: teachershub_enem
- **PostgreSQL Admin**: postgres / postgres123
- **TeachersHub App User**: teachershub_app / teachershub123
- **ENEM RAG Service User**: enem_rag_service / enem123

## Redis Configuration
- **Host**: redis
- **Port**: 6379
- **Password**: (none - development only)

## JWT Configuration
- **Secret Key**: TeachersHub-ENEM-Integration-Secret-Key-2024
- **Issuer**: TeachersHub.ENEM.Api
- **Audience**: TeachersHub.ENEM.Client

## Service Ports (External/Host Ports)
- **TeachersHub API**: 5001 (external) -> 5000 (internal)
- **ENEM RAG Service**: 8001 (external) -> 8000 (internal)
- **PostgreSQL**: 5433 (external) -> 5432 (internal)
- **Redis**: 6380 (external) -> 6379 (internal)

## Network Configuration
- **Network Name**: teachershub-enem-network
- **Subnet**: 172.21.0.0/16

## Container Names
- **PostgreSQL**: teachershub-enem-postgres
- **Redis**: teachershub-enem-redis
- **TeachersHub API**: teachershub-enem-api
- **ENEM RAG Service**: teachershub-enem-rag

## Environment Variables Template
```env
# Database
POSTGRES_DB=teachershub_enem
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Application Users
TEACHERSHUB_DB_USER=teachershub_app
TEACHERSHUB_DB_PASSWORD=teachershub123
ENEM_DB_USER=enem_rag_service
ENEM_DB_PASSWORD=enem123

# JWT
JWT_SECRET_KEY=TeachersHub-ENEM-Integration-Secret-Key-2024
JWT_ISSUER=TeachersHub.ENEM.Api
JWT_AUDIENCE=TeachersHub.ENEM.Client

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Services (External Ports)
TEACHERSHUB_API_PORT=5001
ENEM_RAG_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
```

**CRITICAL**: Never change these credentials during development. Always reference this file.

## Migration Information

### ENEM Scripts Migration
Os scripts de ingestão ENEM foram atualizados para usar a nova arquitetura híbrida:

**Antes (Legacy):**
- Database: `enem_questions_rag`
- User: `enem_user` / `enem_password_2024`
- Port: `5432`
- Schema: `public`

**Depois (Híbrido):**
- Database: `teachershub_enem`
- User: `enem_rag_service` / `enem123`
- Port: `5433` (external)
- Schema: `enem_questions`

### Migration Scripts
- **`./migrate-enem-scripts.sh`** - Atualiza todos os scripts e configurações
- **`./reingest-enem-data.sh`** - Reexecuta ingestão completa no novo schema
