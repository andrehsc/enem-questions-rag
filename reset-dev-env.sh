#!/bin/bash
# Reset TeachersHub-ENEM Development Environment
# Uses EXACT credentials from shared/database/init/00-dev-credentials.md

echo "Ì¥Ñ Resetando ambiente de desenvolvimento..."

# Confirmar a√ß√£o
read -p "‚ö†Ô∏è Isso vai parar todos os containers e limpar volumes. Continuar? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "‚ùå Opera√ß√£o cancelada"
    exit 1
fi

# Parar e remover todos os containers
echo "Ìªë Parando containers..."
docker-compose down --remove-orphans

# Remover volumes
echo "Ì∑ëÔ∏è Removendo volumes..."
docker-compose down -v

# Remover imagens (opcional)
read -p "Ì∑ëÔ∏è Remover tamb√©m as imagens Docker? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Ì∑ëÔ∏è Removendo imagens..."
    docker-compose down --rmi all
fi

# Limpar cache e logs locais
echo "Ì∑π Limpando cache e logs locais..."
rm -rf data/cache/*
rm -rf logs/*
mkdir -p data/cache logs

# Limpar containers √≥rf√£os e volumes n√£o utilizados
echo "Ì∑π Limpeza geral do Docker..."
docker system prune -f

echo ""
echo "‚úÖ Ambiente resetado com sucesso!"
echo ""
echo "Ì≥ã Para reinicializar:"
echo "  ./setup.sh"
