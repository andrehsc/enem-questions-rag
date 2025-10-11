#!/bin/bash
# TeachersHub-ENEM Connectivity Test
# Tests connectivity between services using EXACT credentials

echo "��� Testando conectividade TeachersHub-ENEM Integration..."
echo "Using credentials from: shared/database/init/00-dev-credentials.md"
echo ""

# Contador de testes
tests_passed=0
tests_total=0

# Função para testar conectividade
test_connectivity() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    echo -n "��� $test_name... "
    tests_total=$((tests_total + 1))
    
    if eval "$test_command" 2>/dev/null | grep -q "$expected_pattern"; then
        echo "✅ PASS"
        tests_passed=$((tests_passed + 1))
    else
        echo "❌ FAIL"
        echo "   Command: $test_command"
    fi
}

# Aguardar containers ficarem ready
echo "⏱️ Aguardando containers ficarem prontos..."
sleep 10

# Teste 1: PostgreSQL básico
test_connectivity "PostgreSQL Connection" \
    "docker-compose exec -T postgres pg_isready -U postgres" \
    "accepting connections"

# Teste 2: Redis básico  
test_connectivity "Redis Connection" \
    "docker-compose exec -T redis redis-cli ping" \
    "PONG"

# Teste 3: PostgreSQL com usuário TeachersHub
test_connectivity "TeachersHub Database User" \
    "docker-compose exec -T postgres psql -U postgres -c \"SELECT usename FROM pg_user WHERE usename='teachershub_app';\"" \
    "teachershub_app"

# Teste 4: PostgreSQL com usuário ENEM
test_connectivity "ENEM RAG Database User" \
    "docker-compose exec -T postgres psql -U postgres -c \"SELECT usename FROM pg_user WHERE usename='enem_rag_service';\"" \
    "enem_rag_service"

# Teste 5: Schemas criados
test_connectivity "Database Schemas" \
    "docker-compose exec -T postgres psql -U postgres -d teachershub_enem -c \"SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('teachers_hub', 'enem_questions', 'shared_resources');\"" \
    "teachers_hub"

# Teste 6: Extensões instaladas (pg_trgm é suficiente para operação)
test_connectivity "PostgreSQL Extensions" \
    "docker-compose exec -T postgres psql -U postgres -d teachershub_enem -c \"SELECT extname FROM pg_extension WHERE extname = 'pg_trgm';\"" \
    "pg_trgm"

# Teste 7: Redis conectividade de aplicação
test_connectivity "Redis Application Access" \
    "docker-compose exec -T redis redis-cli -n 1 ping" \
    "PONG"

# Testes de conectividade HTTP (se serviços estiverem rodando)
if docker-compose ps | grep -q "teachershub-api.*Up"; then
    test_connectivity "TeachersHub API Health" \
        "curl -s http://localhost:5001/health" \
        "healthy\|ok\|running"
else
    echo "⏭️ TeachersHub API não está rodando - pulando teste HTTP"
fi

if docker-compose ps | grep -q "enem-rag-service.*Up"; then
    test_connectivity "ENEM RAG Service Health" \
        "curl -s http://localhost:8001/health" \
        "healthy\|ok\|running"
else
    echo "⏭️ ENEM RAG Service não está rodando - pulando teste HTTP"
fi

# Teste de conectividade de rede Docker
test_connectivity "Docker Network" \
    "docker network inspect teachershub-enem-network" \
    "teachershub-enem-network"

# Resumo dos resultados
echo ""
echo "��� Resumo dos Testes:"
echo "====================="
echo "✅ Testes passou: $tests_passed"
echo "��� Total de testes: $tests_total"

if [ $tests_passed -eq $tests_total ]; then
    echo "��� Todos os testes passaram! Sistema funcionando corretamente."
    exit 0
else
    echo "⚠️ $((tests_total - tests_passed)) teste(s) falharam. Verificar configuração."
    echo ""
    echo "��� Comandos para debug:"
    echo "  ./logs.sh errors  - Ver logs de erro"
    echo "  ./logs.sh health  - Verificar saúde dos serviços"
    echo "  docker-compose ps - Status dos containers"
    exit 1
fi
