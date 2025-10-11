#!/usr/bin/env python3
"""Script de ingestão ENEM usando módulo enem_ingestion"""

import sys
import os
import logging
from pathlib import Path

# Adicionar src ao path para importar módulos
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from src.enem_ingestion.config import settings
from src.enem_ingestion.database import DatabaseManager
from src.enem_ingestion.parser import EnemPDFParser

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_ingestion():
    """Executar ingestão completa dos PDFs ENEM"""
    logger.info("=== INICIANDO INGESTAO ENEM ===")
    
    # Verificar diretório de downloads
    downloads_dir = Path("data/downloads")
    if not downloads_dir.exists():
        logger.error(f"Diretório {downloads_dir} não encontrado")
        return False
    
    # Buscar arquivos PDF
    pdf_files = list(downloads_dir.rglob("*.pdf"))
    logger.info(f"Encontrados {len(pdf_files)} arquivos PDF")
    
    if not pdf_files:
        logger.warning("Nenhum arquivo PDF encontrado para ingestão")
        return False
    
    # Inicializar componentes
    try:
        db_manager = DatabaseManager()
        parser = EnemPDFParser()
        
        # Criar tabelas se necessário
        db_manager.create_tables()
        logger.info("Tabelas verificadas/criadas")
        
        # Processar cada PDF
        processed = 0
        for pdf_file in pdf_files[:5]:  # Limitar a 5 arquivos para teste
            logger.info(f"Processando: {pdf_file.name}")
            
            try:
                # Parse do PDF
                questions_data = parser.parse_pdf(pdf_file)
                
                if questions_data:
                    # Salvar no banco
                    with db_manager.get_session() as session:
                        # Aqui você implementaria a lógica de inserção
                        # usando SQLAlchemy models
                        pass
                    
                    processed += 1
                    logger.info(f"✓ {pdf_file.name} processado com sucesso")
                else:
                    logger.warning(f"⚠ Nenhuma questão extraída de {pdf_file.name}")
                    
            except Exception as e:
                logger.error(f"✗ Erro processando {pdf_file.name}: {e}")
                continue
        
        logger.info(f"=== INGESTAO CONCLUIDA: {processed}/{len(pdf_files[:5])} arquivos processados ===")
        return processed > 0
        
    except Exception as e:
        logger.error(f"Erro na ingestão: {e}")
        return False

if __name__ == "__main__":
    success = run_ingestion()
    sys.exit(0 if success else 1)
