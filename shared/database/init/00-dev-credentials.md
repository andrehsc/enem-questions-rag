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

## Service Ports
- **TeachersHub API**: 5000
- **ENEM RAG Service**: 8000
- **PostgreSQL**: 5432
- **Redis**: 6379

## Network Configuration
- **Network Name**: teachershub-network
- **Subnet**: 172.20.0.0/16

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

# Services
TEACHERSHUB_API_PORT=5000
ENEM_RAG_PORT=8000
```

**CRITICAL**: Never change these credentials during development. Always reference this file.
