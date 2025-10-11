#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para testar tipos especiais de ENEM (Libras, PPL, Braille)."""

import logging
import sys
from pathlib import Path
import requests

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings
from enem_ingestion.downloader import EnemDownloader

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_url_status(url):
    """Test if URL is accessible using HEAD request."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code, response.reason
    except requests.exceptions.Timeout:
        return 408, "Timeout"
    except requests.exceptions.ConnectionError:
        return 0, "Connection Error"
    except Exception as e:
        return -1, str(e)


def test_urls_set(urls_dict, type_name):
    """Test a set of URLs and report results."""
    total_tested = 0
    successful = 0
    failed = 0
    failed_list = []
    
    for year, files in urls_dict.items():
        if not files:
            continue
            
        print(f"\nANO {year} ({type_name})")
        
        for file_info in files:
            url = file_info["url"]
            total_tested += 1
            
            status_code, reason = test_url_status(url)
            
            # Prepare info display
            accessibility = file_info.get('accessibility', 'regular')
            file_type = file_info.get('type', 'unknown')
            day = file_info.get('day', '?')
            color = file_info.get('color', '?')
            
            info_str = f"{file_type} D{day} {color}"
            if accessibility != 'regular':
                info_str += f" ({accessibility})"
            
            if status_code == 200:
                print(f"   OK - {info_str}")
                successful += 1
            else:
                print(f"   FAIL - {info_str} - {status_code} {reason}")
                failed += 1
                failed_list.append({
                    'year': year,
                    'url': url,
                    'info': info_str,
                    'status': f"{status_code} {reason}"
                })
    
    # Summary
    print(f"\nRESUMO {type_name.upper()}")
    print(f"   Total testado: {total_tested}")
    print(f"   Sucessos: {successful}")
    print(f"   Falhas: {failed}")
    
    if failed_list:
        print(f"\nURLs QUE FALHARAM ({type_name})")
        for item in failed_list:
            print(f"   {item['year']}: {item['info']} - {item['status']}")
            print(f"      {item['url']}")
        print()


def main():
    """Test all URLs including special types."""
    print("ANALISE DE URLs DO ENEM - TIPOS ESPECIAIS")
    print("=" * 60)
    
    # Create downloader
    downloader = EnemDownloader()
    
    # Test regular types (first 10 for comparison)
    print("\nTIPOS REGULARES (AMOSTRA)")
    print("-" * 40)
    regular_urls = downloader.get_enem_urls(use_scraper=False, include_special=False)
    sample_regular = {}
    if 2024 in regular_urls:
        sample_regular[2024] = regular_urls[2024][:10]  # First 10 for sample
    test_urls_set(sample_regular, "Regular Sample")
    
    # Test special types
    print("\nTIPOS ESPECIAIS (2024)")
    print("-" * 40)
    special_urls = downloader.get_enem_urls(use_scraper=False, include_special=True)
    
    # Filter only special types for 2024
    special_2024 = {}
    if 2024 in special_urls:
        special_2024[2024] = [
            file_info for file_info in special_urls[2024] 
            if 'accessibility' in file_info
        ]
    
    test_urls_set(special_2024, "Special")


if __name__ == "__main__":
    main()
