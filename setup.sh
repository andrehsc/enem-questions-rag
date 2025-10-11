#!/bin/bash
# TeachersHub-ENEM Integration Setup Script
# Uses EXACT credentials from shared/database/init/00-dev-credentials.md

set -e

echo "��� Inicializando ambiente TeachersHub-ENEM Integration..."

# Verificar se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# Verificar arquivo de credenciais
if [ ! -f "shared/database/init/00-dev-credentials.md" ]; then
    echo "❌ Arquivo de credenciais não encontrado!"
    exit 1
fi

echo "��� Credenciais verificadas - usando configuração padrão"

# Criar diretórios necessários se não existirem
echo "��� Criando estrutura de diretórios..."
mkdir -p python-ml-services/rag-service
mkdir -p teachershub-integration/TeachersHub.ENEM.Api
mkdir -p shared/monitoring
mkdir -p data/cache
mkdir -p logs

# Parar containers existentes se estiverem rodando
echo "��� Parando containers existentes..."
docker-compose down --remove-orphans || true

# Limpar volumes se necessário (opcional)
read -p "���️ Deseja limpar volumes existentes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down -v
    echo "✅ Volumes limpos"
fi

# Build e start dos serviços
echo "��� Construindo imagens Docker..."
docker-compose build --no-cache

echo "��� Iniciando serviços..."
docker-compose up -d

# Aguardar health checks
echo "⏱️ Aguardando serviços ficarem saudáveis..."
timeout=180
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✅ Serviços inicializados com sucesso!"
        break
    fi
    
    echo "⏳ Aguardando... ($elapsed/$timeout segundos)"
    sleep 10
    elapsed=$((elapsed + 10))
done

if [ $elapsed -ge $timeout ]; then
    echo "⚠️ Timeout aguardando serviços. Verificando logs..."
    docker-compose logs
    exit 1
fi

# Verificar conectividade
echo "��� Testando conectividade entre serviços..."
bash test-connectivity.sh

echo ""
echo "��� Ambiente TeachersHub-ENEM configurado com sucesso!"
echo ""
echo "��� Status dos serviços:"
docker-compose ps
echo ""
echo "📋 Próximos passos:"
echo "  - TeachersHub API: http://localhost:5001"
echo "  - ENEM RAG Service: http://localhost:8001"  
echo "  - PostgreSQL: localhost:5433"
echo "  - Redis: localhost:6380"
echo ""
echo "��� Comandos úteis:"
echo "  ./logs.sh          - Ver logs de todos os serviços"
echo "  ./test-connectivity.sh - Testar conectividade"
echo "  ./reset-dev-env.sh - Resetar ambiente completo"
