"""
Web scraper for discovering ENEM exam URLs from INEP website.

This module scrapes the INEP website to discover download URLs for ENEM exams
dynamically, rather than relying on hardcoded URLs.
"""

import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import settings

logger = logging.getLogger(__name__)


class INEPScraper:
    """Scrapes INEP website for ENEM download URLs."""

    def __init__(self):
        """Initialize the scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Known INEP pages for ENEM downloads
        self.enem_pages = [
            "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos",
            "https://download.inep.gov.br/enem/",
            "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem"
        ]

    def _extract_pdf_links(self, html_content: str, base_url: str) -> List[str]:
        """
        Extract PDF download links from HTML content.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
            
        Returns:
            List of PDF URLs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            
            # Check if it's a PDF link and looks like ENEM content
            if (href.lower().endswith('.pdf') and 
                any(keyword in href.lower() for keyword in ['enem', 'prova', 'gabarito', 'questoes'])):
                pdf_links.append(href)
        
        return pdf_links

    def _categorize_file(self, url: str, filename: str) -> Dict[str, str]:
        """
        Categorize a file based on its URL and filename.
        
        Args:
            url: File URL
            filename: Filename
            
        Returns:
            Dictionary with file metadata
        """
        filename_lower = filename.lower()
        url_lower = url.lower()
        
        file_info = {
            'url': url,
            'filename': filename,
            'type': 'unknown',
            'year': None,
            'application': '1_aplicacao',
            'color': None
        }
        
        # Extract year from filename or URL
        year_match = re.search(r'20(2[0-4])', url_lower + filename_lower)
        if year_match:
            file_info['year'] = int(year_match.group(0))
        
        # Determine file type
        if any(keyword in filename_lower for keyword in ['gabarito', 'gab']):
            file_info['type'] = 'gabarito'
        elif any(keyword in filename_lower for keyword in ['prova', 'questoes', 'caderno', 'pv']):
            file_info['type'] = 'caderno_questoes'
            
            # Try to determine color/version
            if any(color in filename_lower for color in ['azul', 'cd1']):
                file_info['color'] = 'azul'
            elif any(color in filename_lower for color in ['amarelo', 'cd2']):
                file_info['color'] = 'amarelo'
            elif any(color in filename_lower for color in ['branco', 'cd3']):
                file_info['color'] = 'branco'
            elif any(color in filename_lower for color in ['rosa', 'cd4']):
                file_info['color'] = 'rosa'
        
        return file_info

    def scrape_enem_urls(self, target_years: Optional[List[int]] = None) -> Dict[int, List[Dict[str, str]]]:
        """
        Scrape INEP website for ENEM download URLs.
        
        Args:
            target_years: List of years to scrape. If None, uses config default.
            
        Returns:
            Dictionary mapping years to list of file info dictionaries
        """
        if target_years is None:
            target_years = settings.target_years
        
        all_urls = set()
        
        # Scrape each known page
        for page_url in self.enem_pages:
            try:
                logger.info(f"Scraping {page_url}")
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                pdf_links = self._extract_pdf_links(response.text, page_url)
                all_urls.update(pdf_links)
                
                logger.info(f"Found {len(pdf_links)} PDF links on {page_url}")
                
            except Exception as e:
                logger.warning(f"Error scraping {page_url}: {e}")
                continue
        
        # Categorize and filter files
        categorized_files = {}
        
        for url in all_urls:
            try:
                filename = urlparse(url).path.split('/')[-1]
                file_info = self._categorize_file(url, filename)
                
                # Filter by target years
                if file_info['year'] and file_info['year'] in target_years:
                    year = file_info['year']
                    if year not in categorized_files:
                        categorized_files[year] = []
                    categorized_files[year].append(file_info)
                    
            except Exception as e:
                logger.warning(f"Error categorizing {url}: {e}")
                continue
        
        # Log results
        total_files = sum(len(files) for files in categorized_files.values())
        logger.info(f"Discovered {total_files} ENEM files across {len(categorized_files)} years")
        
        for year, files in categorized_files.items():
            types = {}
            for file_info in files:
                file_type = file_info['type']
                types[file_type] = types.get(file_type, 0) + 1
            logger.info(f"Year {year}: {types}")
        
        return categorized_files

    def validate_discovered_urls(self, urls_dict: Dict[int, List[Dict[str, str]]]) -> Dict[int, List[Dict[str, str]]]:
        """
        Validate discovered URLs by checking if they're accessible.
        
        Args:
            urls_dict: Dictionary of discovered URLs
            
        Returns:
            Dictionary with only accessible URLs
        """
        validated_urls = {}
        
        for year, files in urls_dict.items():
            validated_files = []
            
            for file_info in files:
                try:
                    # HEAD request to check if URL is accessible
                    response = self.session.head(file_info['url'], timeout=10)
                    if response.status_code == 200:
                        validated_files.append(file_info)
                        logger.debug(f"Validated: {file_info['url']}")
                    else:
                        logger.warning(f"URL not accessible: {file_info['url']} (status: {response.status_code})")
                        
                except Exception as e:
                    logger.warning(f"Error validating {file_info['url']}: {e}")
                    continue
            
            if validated_files:
                validated_urls[year] = validated_files
        
        return validated_urls

    def get_fallback_urls(self) -> Dict[int, List[Dict[str, str]]]:
        """
        Get fallback hardcoded URLs if scraping fails.
        
        Returns:
            Dictionary with fallback URLs
        """
        # These are known working URLs as fallback
        fallback_urls = {
            2020: [
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2020_PV_impresso_D1_CD1.pdf",
                    "year": 2020,
                    "filename": "2020_PV_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2020_GB_impresso_D1_CD1.pdf",
                    "year": 2020,
                    "filename": "2020_GB_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2020_GB_impresso_D1_CD2.pdf",
                    "year": 2020,
                    "filename": "2020_GB_impresso_D1_CD2.pdf"
                }
            ],
            2021: [
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2021_PV_impresso_D1_CD1.pdf",
                    "year": 2021,
                    "filename": "2021_PV_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2021_GB_impresso_D1_CD1.pdf",
                    "year": 2021,
                    "filename": "2021_GB_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2021_GB_impresso_D1_CD2.pdf",
                    "year": 2021,
                    "filename": "2021_GB_impresso_D1_CD2.pdf"
                }
            ],
            2022: [
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2022_PV_impresso_D1_CD1.pdf",
                    "year": 2022,
                    "filename": "2022_PV_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2022_GB_impresso_D1_CD1.pdf",
                    "year": 2022,
                    "filename": "2022_GB_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2022_GB_impresso_D1_CD2.pdf",
                    "year": 2022,
                    "filename": "2022_GB_impresso_D1_CD2.pdf"
                }
            ],
            2023: [
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2023_PV_impresso_D1_CD1.pdf",
                    "year": 2023,
                    "filename": "2023_PV_impresso_D1_CD1.pdf"
                },
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2023_PV_impresso_D1_CD2.pdf",
                    "year": 2023,
                    "filename": "2023_PV_impresso_D1_CD2.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2023_GB_impresso_D1_CD1.pdf",
                    "year": 2023,
                    "filename": "2023_GB_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2023_GB_impresso_D1_CD2.pdf",
                    "year": 2023,
                    "filename": "2023_GB_impresso_D1_CD2.pdf"
                }
            ],
            2024: [
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D1_CD1.pdf",
                    "year": 2024,
                    "filename": "2024_PV_impresso_D1_CD1.pdf"
                },
                {
                    "type": "caderno_questoes",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D1_CD2.pdf",
                    "year": 2024,
                    "filename": "2024_PV_impresso_D1_CD2.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "azul",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D1_CD1.pdf",
                    "year": 2024,
                    "filename": "2024_GB_impresso_D1_CD1.pdf"
                },
                {
                    "type": "gabarito",
                    "application": "1_aplicacao",
                    "color": "amarelo",
                    "url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D1_CD2.pdf",
                    "year": 2024,
                    "filename": "2024_GB_impresso_D1_CD2.pdf"
                }
            ]
        }
        
        logger.info("Using fallback URLs")
        return fallback_urls