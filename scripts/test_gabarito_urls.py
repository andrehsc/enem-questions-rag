#!/usr/bin/env python3
"""Test script to find correct gabarito URL patterns."""

import logging
import sys
import requests
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_url_exists(url):
    """Test if a URL exists by making a HEAD request."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)


def main():
    """Test various gabarito URL patterns."""
    base_url = "https://download.inep.gov.br/enem/provas_e_gabaritos/"
    
    # Years to test
    years = [2020, 2021, 2022, 2023, 2024]
    
    # Different naming patterns to test
    patterns = [
        # Pattern found by user
        "{year}_GB_impresso_D1_CD1.pdf",
        "{year}_GB_impresso_D1_CD2.pdf",
        
        # Variations
        "{year}_GAB_impresso_D1_CD1.pdf", 
        "{year}_GAB_impresso_D1_CD2.pdf",
        "{year}_GABARITO_D1_CD1.pdf",
        "{year}_GABARITO_D1_CD2.pdf",
        
        # Original failing pattern
        "{year}_GAB_1_DIA_IMPRESSO.pdf",
        
        # Other variations
        "{year}_GB_D1_CD1.pdf",
        "{year}_GB_D1_CD2.pdf",
        "{year}_GAB_D1_CD1.pdf",
        "{year}_GAB_D1_CD2.pdf",
    ]
    
    print("Ì¥ç TESTANDO PADR√ïES DE URL PARA GABARITOS")
    print("=" * 60)
    
    successful_urls = []
    
    for year in years:
        print(f"\nÌ≥Ö ANO {year}")
        print("-" * 30)
        
        for pattern in patterns:
            url = base_url + pattern.format(year=year)
            exists, status = test_url_exists(url)
            
            if exists:
                print(f"‚úÖ {pattern.format(year=year)} - ENCONTRADO!")
                successful_urls.append((year, pattern, url))
            else:
                print(f"‚ùå {pattern.format(year=year)} - {status}")
    
    print("\n" + "=" * 60)
    print("Ì≥ä RESUMO - URLS V√ÅLIDAS ENCONTRADAS")
    print("=" * 60)
    
    if successful_urls:
        for year, pattern, url in successful_urls:
            print(f"‚úÖ {year}: {pattern}")
            print(f"   URL: {url}")
    else:
        print("‚ùå Nenhuma URL v√°lida encontrada")
    
    print(f"\nÌ≥à Total encontradas: {len(successful_urls)}")


if __name__ == "__main__":
    main()
