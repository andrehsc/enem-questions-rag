#!/bin/bash
# TeachersHub-ENEM Logs Viewer
# Shows aggregated logs from all services

echo "��� Logs do TeachersHub-ENEM Integration"
echo "======================================"

if [ $# -eq 0 ]; then
    echo "��� Mostrando logs de todos os serviços..."
    echo ""
    docker-compose logs --tail=50 --follow
else
    case $1 in
        "teachershub"|"api")
            echo "��� Logs TeachersHub API:"
            docker-compose logs --tail=100 --follow teachershub-api
            ;;
        "enem"|"rag")
            echo "�� Logs ENEM RAG Service:"
            docker-compose logs --tail=100 --follow enem-rag-service
            ;;
        "postgres"|"db")
            echo "��� Logs PostgreSQL:"
            docker-compose logs --tail=100 --follow postgres
            ;;
        "redis")
            echo "��� Logs Redis:"
            docker-compose logs --tail=100 --follow redis
            ;;
        "errors")
            echo "��� Mostrando apenas erros..."
            docker-compose logs --tail=200 | grep -i error
            ;;
        "health")
            echo "��� Status de saúde dos serviços:"
            docker-compose ps
            echo ""
            echo "��� Health checks:"
            docker-compose exec postgres pg_isready -U postgres || echo "❌ PostgreSQL não saudável"
            docker-compose exec redis redis-cli ping || echo "❌ Redis não saudável"
            curl -f http://localhost:5001/health 2>/dev/null && echo "✅ TeachersHub API saudável" || echo "❌ TeachersHub API não saudável"
            curl -f http://localhost:8001/health 2>/dev/null && echo "✅ ENEM RAG Service saudável" || echo "❌ ENEM RAG Service não saudável"
            ;;
        *)
            echo "❓ Uso: ./logs.sh [serviço]"
            echo ""
            echo "Serviços disponíveis:"
            echo "  teachershub, api    - TeachersHub .NET API"
            echo "  enem, rag          - ENEM RAG Service"
            echo "  postgres, db       - PostgreSQL Database"
            echo "  redis             - Redis Cache"
            echo "  errors            - Apenas mensagens de erro"
            echo "  health            - Status de saúde"
            echo ""
            echo "Sem parâmetros: mostra logs de todos os serviços"
            ;;
    esac
fi
