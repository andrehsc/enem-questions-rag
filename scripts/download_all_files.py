#!/usr/bin/env python3
"""Script para baixar todos os arquivos ENEM disponíveis."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings
from enem_ingestion.downloader import EnemDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Download all available ENEM files."""
    logger.info("Iniciando download de todos os arquivos ENEM...")
    
    try:
        # Create downloader
        downloader = EnemDownloader()
        
        # Get URLs (usando hardcoded para evitar scraping issues)
        urls = downloader.get_enem_urls(use_scraper=False)
        
        total_files = sum(len(files) for files in urls.values())
        logger.info(f"Total de arquivos configurados: {total_files}")
        
        successful_downloads = 0
        failed_downloads = 0
        cached_files = 0
        
        # Download each year
        for year in settings.target_years:
            logger.info(f"\n=== PROCESSANDO ANO {year} ===")
            
            if year not in urls:
                logger.warning(f"Nenhuma URL configurada para {year}")
                continue
            
            year_files = urls[year]
            logger.info(f"Arquivos para {year}: {len(year_files)}")
            
            for i, file_info in enumerate(year_files):
                file_type = file_info['type']
                color = file_info.get('color', 'N/A')
                url = file_info['url']
                
                logger.info(f"\n{i+1}/{len(year_files)} - {file_type} {color}")
                logger.info(f"URL: {url}")
                
                try:
                    file_path, was_downloaded = downloader.download_file(url, year)
                    
                    if was_downloaded:
                        successful_downloads += 1
                        logger.info(f"✅ BAIXADO: {file_path.name}")
                    else:
                        cached_files += 1
                        logger.info(f"📁 CACHE: {file_path.name}")
                    
                except Exception as e:
                    failed_downloads += 1
                    error_msg = str(e)
                    
                    if '404' in error_msg:
                        logger.error(f"❌ URL NÃO EXISTE: {file_type} {color}")
                    elif '403' in error_msg:
                        logger.error(f"❌ ACESSO NEGADO: {file_type} {color}")
                    else:
                        logger.error(f"❌ ERRO: {error_msg}")
        
        # Final summary
        logger.info(f"\n=== RESUMO FINAL ===")
        logger.info(f"Total configurado: {total_files}")
        logger.info(f"✅ Baixados com sucesso: {successful_downloads}")
        logger.info(f"📁 Já em cache: {cached_files}")
        logger.info(f"❌ Falharam: {failed_downloads}")
        logger.info(f"📊 Taxa de sucesso: {((successful_downloads + cached_files) / total_files * 100):.1f}%")
        
        # Show final status
        logger.info(f"\n=== STATUS FINAL ===")
        final_status = downloader.get_download_status()
        for year, year_status in final_status.items():
            downloaded = year_status['downloaded']
            expected = year_status['expected']
            logger.info(f"Ano {year}: {downloaded}/{expected} arquivos ({downloaded/expected*100:.1f}%)")
        
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        raise


if __name__ == "__main__":
    main()