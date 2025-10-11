#!/bin/bash
# Backup automatizado do PostgreSQL

set -e

# Configurações
BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="enem_rag"
DB_USER="postgres"
DB_HOST="postgres"

# Criar diretório de backup se não existir
mkdir -p $BACKUP_DIR

# Backup completo do banco
echo "Iniciando backup do banco de dados..."
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > "$BACKUP_DIR/enem_backup_$DATE.sql"

# Compactar backup
gzip "$BACKUP_DIR/enem_backup_$DATE.sql"

# Manter apenas os últimos 7 backups
find $BACKUP_DIR -name "enem_backup_*.sql.gz" -mtime +7 -delete

echo "Backup concluído: enem_backup_$DATE.sql.gz"

# Verificar integridade do backup
if [ -f "$BACKUP_DIR/enem_backup_$DATE.sql.gz" ]; then
    echo "Backup criado com sucesso!"
    ls -lh "$BACKUP_DIR/enem_backup_$DATE.sql.gz"
else
    echo "ERRO: Backup não foi criado!"
    exit 1
fi
