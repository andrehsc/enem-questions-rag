#!/bin/bash
# MigraÃ§Ã£o dos Scripts ENEM para Nova Arquitetura HÃ­brida
# Atualiza credenciais para compatibilidade com docker-compose TeachersHub-ENEM

echo "í´„ Migrando scripts ENEM para nova arquitetura hÃ­brida..."

# Backup do .env atual
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "í³‹ Backup do .env criado"
fi

# Criar novo .env compatÃ­vel com arquitetura hÃ­brida
cat > .env << 'ENVEOF'
# ========================================
# TeachersHub-ENEM Integration - Environment Variables
# Using EXACT credentials from shared/database/init/00-dev-credentials.md
# ========================================

# Database Configuration - ENEM RAG Service Schema
DATABASE_URL=postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem
POSTGRES_DB=teachershub_enem
POSTGRES_USER=enem_rag_service
POSTGRES_PASSWORD=enem123
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# Legacy compatibility (for scripts that still use old vars)
DB_HOST=localhost
DB_PORT=5433
DB_NAME=teachershub_enem
DB_USER=enem_rag_service
DB_PASSWORD=enem123

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=1

# Application Configuration
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO

# File Storage
DATA_PATH=./data
DOWNLOADS_PATH=./data/downloads
CACHE_PATH=./data/cache

# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
PARSING_TIMEOUT=300

# RAG Configuration
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
VECTOR_DB_PATH=./data/vectors
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# TeachersHub Integration Endpoints
TEACHERSHUB_API_URL=http://localhost:5001
ENEM_RAG_SERVICE_URL=http://localhost:8001
ENVEOF

echo "âœ… Novo .env criado com credenciais hÃ­bridas"

# Atualizar manage-db.sh para usar novas portas
echo "í´§ Atualizando manage-db.sh..."
sed -i 's/localhost:8080/localhost:8081/g' scripts/manage-db.sh 2>/dev/null || \
sed -i.bak 's/localhost:8080/localhost:8081/g' scripts/manage-db.sh
sed -i 's/localhost:5432/localhost:5433/g' scripts/manage-db.sh 2>/dev/null || \
sed -i.bak 's/localhost:5432/localhost:5433/g' scripts/manage-db.sh
sed -i 's/enem_user:enem_password_2024@localhost:5432\/enem_questions_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' scripts/manage-db.sh 2>/dev/null || \
sed -i.bak 's/enem_user:enem_password_2024@localhost:5432\/enem_questions_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' scripts/manage-db.sh

# Lista de arquivos Python que precisam ser atualizados
PYTHON_FILES=(
    "scripts/database_queries.py"
    "scripts/answer_processor_clean.py"
    "scripts/full_ingestion_report.py"
    "api/database.py"
)

# Atualizar arquivos Python
for file in "${PYTHON_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "í° Atualizando $file..."
        
        # Backup
        cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"
        
        # SubstituiÃ§Ãµes
        sed -i 's/enem_user:enem_password_2024@localhost:5432\/enem_questions_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' "$file" 2>/dev/null || \
        sed -i.bak 's/enem_user:enem_password_2024@localhost:5432\/enem_questions_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' "$file"
        
        sed -i 's/postgres:postgres123@localhost:5432\/enem_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' "$file" 2>/dev/null || \
        sed -i.bak 's/postgres:postgres123@localhost:5432\/enem_rag/enem_rag_service:enem123@localhost:5433\/teachershub_enem/g' "$file"
    fi
done

# Atualizar scripts SQL
echo "í·„ï¸ Atualizando scripts SQL..."
if [ -f "scripts/01-init-database.sql" ]; then
    cp "scripts/01-init-database.sql" "scripts/01-init-database.sql.backup.$(date +%Y%m%d_%H%M%S)"
    sed -i 's/enem_questions_rag/teachershub_enem/g' "scripts/01-init-database.sql" 2>/dev/null || \
    sed -i.bak 's/enem_questions_rag/teachershub_enem/g' "scripts/01-init-database.sql"
fi

# Atualizar config.py para usar variÃ¡veis de ambiente
if [ -f "src/enem_ingestion/config.py" ]; then
    echo "âš™ï¸ Atualizando config.py..."
    cp "src/enem_ingestion/config.py" "src/enem_ingestion/config.py.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Criar versÃ£o atualizada
    cat > "src/enem_ingestion/config.py" << 'CONFIGEOF'
"""Configuration management for ENEM ingestion pipeline - TeachersHub Integration."""

import os
from pathlib import Path
from typing import Optional, List


class Settings:
    """Application settings loaded from environment variables - TeachersHub-ENEM Integration."""

    def __init__(self):
        # Database configuration - Using TeachersHub-ENEM hybrid credentials
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://enem_rag_service:enem123@localhost:5433/teachershub_enem"
        )
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5433"))
        self.db_name = os.getenv("DB_NAME", "teachershub_enem")
        self.db_user = os.getenv("DB_USER", "enem_rag_service")
        self.db_password = os.getenv("DB_PASSWORD", "enem123")

        # Redis configuration
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6380"))
        self.redis_db = int(os.getenv("REDIS_DB", "1"))

        # INEP data sources
        self.inep_base_url = os.getenv("INEP_BASE_URL", "https://www.gov.br/inep/pt-br")
        self.download_cache_dir = Path(os.getenv("DOWNLOAD_CACHE_DIR", "./data/downloads"))

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file_path = os.getenv("LOG_FILE", "./logs/enem_ingestion.log")
        self.log_file = Path(log_file_path) if log_file_path else None

        # TeachersHub Integration
        self.teachershub_api_url = os.getenv("TEACHERSHUB_API_URL", "http://localhost:5001")
        self.enem_rag_service_url = os.getenv("ENEM_RAG_SERVICE_URL", "http://localhost:8001")


# Global settings instance
settings = Settings()
CONFIGEOF
fi

echo ""
echo "âœ… MigraÃ§Ã£o concluÃ­da!"
echo ""
echo "í³‹ Resumo das mudanÃ§as:"
echo "  - Porta PostgreSQL: 5432 â†’ 5433"
echo "  - Porta Redis: 6379 â†’ 6380"  
echo "  - Database: enem_questions_rag â†’ teachershub_enem"
echo "  - User: enem_user â†’ enem_rag_service"
echo "  - Password: enem_password_2024 â†’ enem123"
echo "  - Schema: public â†’ enem_questions"
echo ""
echo "í´ PrÃ³ximos passos:"
echo "  1. Executar: docker compose up -d postgres redis"
echo "  2. Executar: ./test-connectivity.sh"
echo "  3. Reexecutar ingestÃ£o: python scripts/init_system.py"
echo ""
echo "í³ Backups criados para todos os arquivos modificados"
