"""
Download module for ENEM exam files from INEP website.

This module handles downloading ENEM exam PDFs from the official INEP website,
with caching and integrity validation.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import settings
from .web_scraper import INEPScraper

logger = logging.getLogger(__name__)


class EnemDownloader:
    """Downloads ENEM exam files from INEP website."""

    def __init__(self, cache_dir: Optional[Path] = None, max_retries: int = 3):
        """
        Initialize the downloader.
        
        Args:
            cache_dir: Directory to cache downloaded files
            max_retries: Maximum number of retry attempts
        """
        self.cache_dir = cache_dir or settings.download_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_enem_urls(self, use_scraper: bool = True, include_special: bool = True) -> Dict[int, List[Dict[str, str]]]:
        """
        Get URLs for ENEM exam files from INEP website.
        
        Args:
            use_scraper: Whether to use web scraper to discover URLs dynamically
            include_special: Whether to include special accessibility types (Libras, PPL, Braille)
        
        Returns:
            Dictionary mapping years to list of exam file info
        """
        if use_scraper:
            try:
                logger.info("Using web scraper to discover ENEM URLs...")
                scraper = INEPScraper()
                urls = scraper.scrape_enem_urls(settings.target_years)
                
                if urls:
                    logger.info(f"Web scraper found URLs for {len(urls)} years")
                    return urls
                else:
                    logger.warning("Web scraper found no URLs, falling back to hardcoded URLs")
            except Exception as e:
                logger.error(f"Web scraper failed: {e}, falling back to hardcoded URLs")
        
        # Fallback to hardcoded URLs with comprehensive coverage
        logger.info("Using hardcoded ENEM URLs...")
        return self._generate_comprehensive_urls(include_special)

    def _generate_comprehensive_urls(self, include_special: bool = True) -> Dict[int, List[Dict[str, str]]]:
        """Generate comprehensive URL list for all ENEM exam types."""
        urls = {}
        
        # Standard exam patterns for all years
        for year in settings.target_years:
            year_urls = []
            
            # Regular application - Standard 4 colors for both days
            for day in [1, 2]:
                cd_start = 1 if day == 1 else 5
                for cd in range(cd_start, cd_start + 4):
                    # Prova
                    year_urls.append({
                        "type": "caderno_questoes",
                        "application": "regular",
                        "day": day,
                        "color": f"CD{cd}",
                        "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_PV_impresso_D{day}_CD{cd}.pdf"
                    })
                    # Gabarito
                    year_urls.append({
                        "type": "gabarito", 
                        "application": "regular",
                        "day": day,
                        "color": f"CD{cd}",
                        "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_GB_impresso_D{day}_CD{cd}.pdf"
                    })
            
            # Special accessibility types (only for 2024 initially, will expand based on discovery)
            if include_special and year == 2024:
                # Braille and Reader (Caderno 9 - Day 1, Caderno 11 - Day 2)
                for day, cd in [(1, 9), (2, 11)]:
                    year_urls.extend([
                        {
                            "type": "caderno_questoes",
                            "application": "regular",
                            "day": day,
                            "color": f"CD{cd}",
                            "accessibility": "braille_ledor",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_PV_impresso_D{day}_CD{cd}.pdf"
                        },
                        {
                            "type": "gabarito",
                            "application": "regular", 
                            "day": day,
                            "color": f"CD{cd}",
                            "accessibility": "braille_ledor",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_GB_impresso_D{day}_CD{cd}.pdf"
                        }
                    ])
                
                # Libras (Caderno 10 - Day 1, Caderno 12 - Day 2)
                for day, cd in [(1, 10), (2, 12)]:
                    year_urls.extend([
                        {
                            "type": "caderno_questoes",
                            "application": "regular",
                            "day": day,
                            "color": f"CD{cd}",
                            "accessibility": "libras",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_PV_impresso_D{day}_CD{cd}.pdf"
                        },
                        {
                            "type": "gabarito",
                            "application": "regular",
                            "day": day, 
                            "color": f"CD{cd}",
                            "accessibility": "libras",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_GB_impresso_D{day}_CD{cd}.pdf"
                        }
                    ])
                
                # PPL (Reaplicação) - Standard 4 colors for both days
                for day in [1, 2]:
                    cd_start = 1 if day == 1 else 5
                    for cd in range(cd_start, cd_start + 4):
                        year_urls.extend([
                            {
                                "type": "caderno_questoes",
                                "application": "reaplicacao_PPL",
                                "day": day,
                                "color": f"CD{cd}",
                                "accessibility": "PPL",
                                "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_PV_reaplicacao_PPL_D{day}_CD{cd}.pdf"
                            },
                            {
                                "type": "gabarito",
                                "application": "reaplicacao_PPL",
                                "day": day,
                                "color": f"CD{cd}",
                                "accessibility": "PPL", 
                                "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_GB_reaplicacao_PPL_D{day}_CD{cd}.pdf"
                            }
                        ])
                
                # PPL Braille (CD9 and CD11)
                for day, cd in [(1, 9), (2, 11)]:
                    year_urls.extend([
                        {
                            "type": "caderno_questoes",
                            "application": "reaplicacao_PPL",
                            "day": day,
                            "color": f"CD{cd}",
                            "accessibility": "PPL_braille_ledor",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_PV_reaplicacao_PPL_D{day}_CD{cd}_braile_e_ledor.pdf"
                        },
                        {
                            "type": "gabarito",
                            "application": "reaplicacao_PPL",
                            "day": day,
                            "color": f"CD{cd}",
                            "accessibility": "PPL_braille_ledor",
                            "url": f"https://download.inep.gov.br/enem/provas_e_gabaritos/{year}_GB_reaplicacao_PPL_D{day}_CD{cd}_braile_e_ledor.pdf"
                        }
                    ])
            
            urls[year] = year_urls
        
        return urls


    def _get_cached_file_path(self, url: str, year: int) -> Path:
        """Get the local cache path for a file."""
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = f"enem_{year}_file.pdf"
        
        return self.cache_dir / str(year) / filename

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _is_valid_pdf(self, file_path: Path) -> bool:
        """Check if file is a valid PDF."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except Exception as e:
            logger.warning(f"Error validating PDF {file_path}: {e}")
            return False

    def download_file(self, url: str, year: int, force_download: bool = False) -> Tuple[Path, bool]:
        """
        Download a single file from URL.
        
        Args:
            url: URL to download
            year: Year of the exam
            force_download: Force download even if cached
            
        Returns:
            Tuple of (file_path, was_downloaded)
        """
        cache_path = self._get_cached_file_path(url, year)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists and is valid
        if cache_path.exists() and not force_download:
            if self._is_valid_pdf(cache_path):
                logger.info(f"Using cached file: {cache_path}")
                return cache_path, False
            else:
                logger.warning(f"Cached file invalid, re-downloading: {cache_path}")
        
        logger.info(f"Downloading {url} to {cache_path}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Write file
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            # Validate downloaded file
            if not self._is_valid_pdf(cache_path):
                cache_path.unlink()  # Delete invalid file
                raise ValueError(f"Downloaded file is not a valid PDF: {url}")
            
            logger.info(f"Successfully downloaded: {cache_path}")
            return cache_path, True
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            if cache_path.exists():
                cache_path.unlink()  # Clean up failed download
            raise

    def download_year(self, year: int, force_download: bool = False) -> List[Tuple[Dict[str, str], Path]]:
        """
        Download all files for a specific year.
        
        Args:
            year: Year to download
            force_download: Force download even if cached
            
        Returns:
            List of tuples (file_info, local_path)
        """
        if year not in settings.target_years:
            raise ValueError(f"Year {year} not in target years: {settings.target_years}")
        
        enem_urls = self.get_enem_urls()
        if year not in enem_urls:
            raise ValueError(f"No URLs configured for year {year}")
        
        results = []
        for file_info in enem_urls[year]:
            try:
                local_path, was_downloaded = self.download_file(
                    file_info['url'], year, force_download
                )
                results.append((file_info, local_path))
                
                # Be respectful to the server
                if was_downloaded:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Failed to download {file_info['url']}: {e}")
                # Continue with other files
                continue
        
        logger.info(f"Downloaded {len(results)} files for year {year}")
        return results

    def download_all_years(self, force_download: bool = False) -> Dict[int, List[Tuple[Dict[str, str], Path]]]:
        """
        Download files for all target years.
        
        Args:
            force_download: Force download even if cached
            
        Returns:
            Dictionary mapping years to list of (file_info, local_path) tuples
        """
        results = {}
        
        for year in settings.target_years:
            try:
                logger.info(f"Processing year {year}")
                results[year] = self.download_year(year, force_download)
            except Exception as e:
                logger.error(f"Failed to process year {year}: {e}")
                results[year] = []
        
        total_files = sum(len(files) for files in results.values())
        logger.info(f"Download complete. Total files: {total_files}")
        
        return results

    def get_download_status(self) -> Dict[int, Dict[str, int]]:
        """
        Get status of downloaded files.
        
        Returns:
            Dictionary with download status for each year
        """
        status = {}
        enem_urls = self.get_enem_urls()
        
        for year in settings.target_years:
            year_cache_dir = self.cache_dir / str(year)
            
            if not year_cache_dir.exists():
                status[year] = {"expected": len(enem_urls.get(year, [])), "downloaded": 0}
                continue
            
            pdf_files = list(year_cache_dir.glob("*.pdf"))
            valid_files = [f for f in pdf_files if self._is_valid_pdf(f)]
            
            status[year] = {
                "expected": len(enem_urls.get(year, [])),
                "downloaded": len(valid_files),
                "invalid": len(pdf_files) - len(valid_files)
            }
        
        return status