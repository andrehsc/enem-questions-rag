#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialização completa do sistema ENEM RAG
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Adicionar diretórios ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'api'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_dependencies():
    """Verifica se todas as dependências estão instaladas"""
    required_packages = [
        'fastapi', 'uvicorn', 'psycopg2', 'redis', 'pandas', 'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package} - OK")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} - FALTANDO")
    
    if missing_packages:
        logger.error(f"Pacotes faltando: {', '.join(missing_packages)}")
        logger.error("Execute: pip install -r requirements.txt")
        return False
    
    return True

async def check_database_connection():
    """Verifica conexão com PostgreSQL"""
    try:
        import psycopg2
        
        DATABASE_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', 5432),
            'database': os.getenv('DB_NAME', 'enem_rag'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASS', 'postgres123')
        }
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM questoes")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        logger.info(f"✓ PostgreSQL - OK ({count} questões)")
        return True
        
    except Exception as e:
        logger.error(f"✗ PostgreSQL - ERRO: {str(e)}")
        return False

async def check_redis_connection():
    """Verifica conexão com Redis"""
    try:
        import redis
        
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        redis_client.ping()
        logger.info("✓ Redis - OK")
        return True
        
    except Exception as e:
        logger.error(f"✗ Redis - ERRO: {str(e)}")
        return False

async def initialize_rag_features():
    """Inicializa os módulos RAG"""
    try:
        from src.rag_features import initialize_all_components
        
        # Verificar se chave OpenAI está configurada
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            logger.warning("⚠ OPENAI_API_KEY não configurada - recursos de geração limitados")
        
        status = initialize_all_components(openai_api_key=openai_key)
        
        for component, result in status.items():
            if "error" in str(result):
                logger.error(f"✗ {component} - ERRO: {result}")
            else:
                logger.info(f"✓ {component} - OK")
        
        return True
        
    except ImportError:
        logger.warning("⚠ Módulos RAG não disponíveis - instale: pip install -r src/rag_features/requirements.txt")
        return False
    except Exception as e:
        logger.error(f"✗ RAG Features - ERRO: {str(e)}")
        return False

async def check_ml_models():
    """Verifica status dos modelos ML"""
    try:
        from src.ml_models import get_models_status
        
        status = get_models_status()
        
        for model_name, model_info in status.items():
            if model_info['trained']:
                logger.info(f"✓ {model_name} - TREINADO")
            else:
                logger.warning(f"⚠ {model_name} - NÃO TREINADO")
        
        return True
        
    except ImportError:
        logger.warning("⚠ Módulos ML não disponíveis - instale: pip install -r src/ml_models/requirements.txt")
        return False
    except Exception as e:
        logger.error(f"✗ ML Models - ERRO: {str(e)}")
        return False

async def test_api_endpoints():
    """Testa alguns endpoints da API"""
    try:
        sys.path.append(str(project_root / 'api'))
        from fastapi_app import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Testar endpoint de health
        response = client.get("/health")
        if response.status_code == 200:
            logger.info("✓ API Health - OK")
        else:
            logger.error(f"✗ API Health - ERRO: {response.status_code}")
        
        # Testar endpoint de stats (pode falhar se DB não estiver disponível)
        try:
            response = client.get("/stats")
            if response.status_code == 200:
                logger.info("✓ API Stats - OK")
            else:
                logger.warning(f"⚠ API Stats - {response.status_code}")
        except:
            logger.warning("⚠ API Stats - não testado")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ API Tests - ERRO: {str(e)}")
        return False

async def generate_system_report():
    """Gera relatório completo do sistema"""
    logger.info("\n" + "="*60)
    logger.info("RELATÓRIO DE INICIALIZAÇÃO DO SISTEMA ENEM RAG")
    logger.info("="*60)
    
    checks = {
        "Dependências Python": await check_dependencies(),
        "Conexão PostgreSQL": await check_database_connection(),
        "Conexão Redis": await check_redis_connection(),
        "Módulos RAG": await initialize_rag_features(),
        "Modelos ML": await check_ml_models(),
        "API Endpoints": await test_api_endpoints()
    }
    
    logger.info("\n��� RESUMO:")
    
    total_checks = len(checks)
    passed_checks = sum(1 for status in checks.values() if status)
    
    for check_name, status in checks.items():
        status_symbol = "✓" if status else "✗"
        logger.info(f"   {status_symbol} {check_name}")
    
    logger.info(f"\n��� STATUS GERAL: {passed_checks}/{total_checks} verificações OK")
    
    if passed_checks == total_checks:
        logger.info("��� SISTEMA TOTALMENTE OPERACIONAL!")
        return_code = 0
    elif passed_checks >= total_checks * 0.7:
        logger.warning("⚠ SISTEMA PARCIALMENTE OPERACIONAL")
        return_code = 1
    else:
        logger.error("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        return_code = 2
    
    logger.info("\n��� PRÓXIMOS PASSOS:")
    
    if not checks["Dependências Python"]:
        logger.info("   1. Instalar dependências: pip install -r requirements.txt")
    
    if not checks["Conexão PostgreSQL"]:
        logger.info("   2. Verificar PostgreSQL: docker-compose up -d")
        logger.info("   3. Executar ingestão: python scripts/data_ingestion.py")
    
    if not checks["Conexão Redis"]:
        logger.info("   4. Verificar Redis: docker-compose up -d")
    
    if not checks["Módulos RAG"]:
        logger.info("   5. Instalar RAG: pip install -r src/rag_features/requirements.txt")
    
    if not checks["Modelos ML"]:
        logger.info("   6. Treinar modelos ML (opcional)")
    
    logger.info("   7. Iniciar API: python api/fastapi_app.py")
    logger.info("   8. Acessar: http://localhost:8000/docs")
    
    logger.info("\n" + "="*60)
    
    return return_code

async def main():
    """Função principal"""
    try:
        return_code = await generate_system_report()
        sys.exit(return_code)
    except KeyboardInterrupt:
        logger.info("\n⏹ Inicialização interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
