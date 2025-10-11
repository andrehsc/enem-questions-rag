#!/bin/bash
# Script para iniciar infraestrutura Docker do ENEM RAG

echo "Ì∫Ä ENEM RAG - Iniciando Infraestrutura Docker"
echo "=" * 50

# Verificar se Docker est√° rodando
if ! docker info > /dev/null 2>&1; then
    echo "‚ùå Docker n√£o est√° rodando. Inicie o Docker Desktop primeiro."
    exit 1
fi

echo "‚úÖ Docker est√° rodando"

# Parar containers existentes
echo "Ìªë Parando containers existentes..."
docker-compose down

# Limpar sistema se necess√°rio
echo "Ì∑π Limpando recursos..."
docker system prune -f

# Iniciar containers
echo "‚ñ∂Ô∏è Iniciando containers..."
docker-compose up -d

# Aguardar inicializa√ß√£o
echo "‚è≥ Aguardando inicializa√ß√£o (30 segundos)..."
sleep 30

# Verificar status
echo "Ì≥ä Status dos containers:"
docker-compose ps

# Verificar logs
echo "Ì≥ã Logs recentes:"
docker-compose logs --tail=5

echo ""
echo "‚úÖ Infraestrutura iniciada!"
echo "ÔøΩÔøΩ Acesse:"
echo "  - API: http://localhost:8000"
echo "  - Swagger: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "Ì¥ß Comandos √∫teis:"
echo "  - Ver logs: docker-compose logs -f"
echo "  - Parar: docker-compose down"
echo "  - Status: docker-compose ps"
