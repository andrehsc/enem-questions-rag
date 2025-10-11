#!/usr/bin/env python3
"""
Script de inicializacao completa do sistema ENEM RAG
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Adicionar diretorios ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_dependencies():
    """Verifica se todas as dependencias estao instaladas"""
    required_packages = ['fastapi', 'psycopg2', 'redis', 'pandas', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"OK - {package}")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"FALTANDO - {package}")
    
    return len(missing_packages) == 0

async def check_database_connection():
    """Verifica conexao com PostgreSQL"""
    try:
        import psycopg2
        
        DATABASE_CONFIG = {
            'host': 'localhost',
            'port': 5433,
            'database': 'teachershub_enem',
            'user': 'enem_rag_service',
            'password': 'enem123'
        }
        
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM enem_questions.questions")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        logger.info(f"OK - PostgreSQL ({count} questoes)")
        return True
        
    except Exception as e:
        logger.error(f"ERRO - PostgreSQL: {str(e)}")
        return False

async def check_redis_connection():
    """Verifica conexao com Redis"""
    try:
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.ping()
        logger.info("OK - Redis")
        return True
        
    except Exception as e:
        logger.error(f"ERRO - Redis: {str(e)}")
        return False

async def generate_system_report():
    """Gera relatorio completo do sistema"""
    logger.info("="*60)
    logger.info("RELATORIO DE INICIALIZACAO DO SISTEMA ENEM RAG")
    logger.info("="*60)
    
    logger.info("Verificando dependencias...")
    deps_ok = await check_dependencies()
    
    logger.info("Verificando PostgreSQL...")
    db_ok = await check_database_connection()
    
    logger.info("Verificando Redis...")
    redis_ok = await check_redis_connection()
    
    checks = {
        "Dependencias Python": deps_ok,
        "Conexao PostgreSQL": db_ok,
        "Conexao Redis": redis_ok
    }
    
    logger.info("\nRESUMO:")
    
    total_checks = len(checks)
    passed_checks = sum(1 for status in checks.values() if status)
    
    for check_name, status in checks.items():
        status_symbol = "OK" if status else "ERRO"
        logger.info(f"   {status_symbol} - {check_name}")
    
    logger.info(f"\nSTATUS GERAL: {passed_checks}/{total_checks} verificacoes OK")
    
    if passed_checks == total_checks:
        logger.info("SISTEMA TOTALMENTE OPERACIONAL!")
        return_code = 0
    else:
        logger.warning("SISTEMA COM PROBLEMAS")
        return_code = 1
    
    logger.info("\nPROXIMOS PASSOS:")
    logger.info("   1. Verificar servicos: docker-compose up -d")
    logger.info("   2. Iniciar API: python api/fastapi_app.py")
    logger.info("   3. Acessar: http://localhost:8000/docs")
    logger.info("="*60)
    
    return return_code

async def main():
    """Funcao principal"""
    try:
        return_code = await generate_system_report()
        return return_code
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
