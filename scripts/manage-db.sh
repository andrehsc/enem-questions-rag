#!/bin/bash
# ========================================
# ENEM Questions RAG - Database Management Script
# ========================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_usage() {
    echo -e "${BLUE}ENEM Questions RAG - Database Management${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     - Start PostgreSQL and Adminer containers"
    echo "  stop      - Stop all containers"
    echo "  restart   - Restart all containers"
    echo "  logs      - Show container logs"
    echo "  status    - Show container status"
    echo "  connect   - Connect to PostgreSQL via psql"
    echo "  reset     - Reset database (destroy and recreate)"
    echo "  backup    - Create database backup"
    echo "  restore   - Restore database from backup"
    echo "  test      - Test database connection"
    echo ""
}

start_db() {
    echo -e "${GREEN}🚀 Starting ENEM PostgreSQL Database...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✅ Database started successfully!${NC}"
    echo -e "${BLUE}📊 Adminer web interface: http://localhost:8080${NC}"
    echo -e "${BLUE}🔗 Database URL: postgresql://enem_user:enem_password_2024@localhost:5432/enem_questions_rag${NC}"
}

stop_db() {
    echo -e "${YELLOW}🛑 Stopping containers...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Containers stopped${NC}"
}

restart_db() {
    echo -e "${YELLOW}🔄 Restarting containers...${NC}"
    docker-compose restart
    echo -e "${GREEN}✅ Containers restarted${NC}"
}

show_logs() {
    echo -e "${BLUE}📋 Container logs:${NC}"
    docker-compose logs -f
}

show_status() {
    echo -e "${BLUE}📊 Container status:${NC}"
    docker-compose ps
}

connect_db() {
    echo -e "${BLUE}🔌 Connecting to PostgreSQL...${NC}"
    docker exec -it enem-postgres psql -U enem_user -d enem_questions_rag
}

reset_db() {
    echo -e "${RED}⚠️  This will destroy all data! Are you sure? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🗑️  Resetting database...${NC}"
        docker-compose down -v
        docker-compose up -d
        echo -e "${GREEN}✅ Database reset complete${NC}"
    else
        echo -e "${BLUE}ℹ️  Operation cancelled${NC}"
    fi
}

backup_db() {
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    echo -e "${BLUE}💾 Creating backup: $BACKUP_FILE${NC}"
    docker exec enem-postgres pg_dump -U enem_user enem_questions_rag > "backups/$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup created: backups/$BACKUP_FILE${NC}"
}

restore_db() {
    echo -e "${BLUE}📁 Available backups:${NC}"
    ls -la backups/*.sql 2>/dev/null || echo "No backups found"
    echo ""
    echo "Enter backup filename to restore:"
    read -r backup_file
    if [[ -f "backups/$backup_file" ]]; then
        echo -e "${BLUE}📥 Restoring from: $backup_file${NC}"
        docker exec -i enem-postgres psql -U enem_user enem_questions_rag < "backups/$backup_file"
        echo -e "${GREEN}✅ Database restored${NC}"
    else
        echo -e "${RED}❌ Backup file not found${NC}"
    fi
}

test_connection() {
    echo -e "${BLUE}🔍 Testing database connection...${NC}"
    if docker exec enem-postgres pg_isready -U enem_user -d enem_questions_rag >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Database is ready${NC}"
        echo -e "${BLUE}📊 Database info:${NC}"
        docker exec enem-postgres psql -U enem_user -d enem_questions_rag -c "SELECT version();"
        docker exec enem-postgres psql -U enem_user -d enem_questions_rag -c "SELECT current_database(), current_user, now();"
    else
        echo -e "${RED}❌ Database is not ready${NC}"
    fi
}

# Create backups directory if it doesn't exist
mkdir -p backups

# Main script logic
case "${1:-}" in
    start)
        start_db
        ;;
    stop)
        stop_db
        ;;
    restart)
        restart_db
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    connect)
        connect_db
        ;;
    reset)
        reset_db
        ;;
    backup)
        backup_db
        ;;
    restore)
        restore_db
        ;;
    test)
        test_connection
        ;;
    *)
        print_usage
        exit 1
        ;;
esac