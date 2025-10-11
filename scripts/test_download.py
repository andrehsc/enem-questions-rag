#!/usr/bin/env python3
"""Test script for ENEM downloader functionality."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enem_ingestion.config import settings
from enem_ingestion.downloader import EnemDownloader

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Test the ENEM downloader."""
    try:
        logger.info("Testing ENEM downloader...")
        
        # Create downloader
        downloader = EnemDownloader()
        
        # Check current status
        logger.info("Checking download status...")
        status = downloader.get_download_status()
        
        for year, year_status in status.items():
            logger.info(f"Year {year}: {year_status['downloaded']}/{year_status['expected']} files")
        
        # Test URL discovery
        logger.info("Testing URL discovery...")
        urls = downloader.get_enem_urls()
        total_urls = sum(len(files) for files in urls.values())
        logger.info(f"Found {total_urls} URLs across {len(urls)} years")
        
        # Test downloading one file (2024 first file)
        logger.info("Testing single file download...")
        if 2024 in urls and urls[2024]:
            test_url = urls[2024][0]['url']
            try:
                file_path, was_downloaded = downloader.download_file(test_url, 2024)
                logger.info(f"Test download: {'SUCCESS' if file_path.exists() else 'FAILED'}")
                logger.info(f"File path: {file_path}")
                logger.info(f"Was downloaded: {was_downloaded}")
            except Exception as e:
                logger.warning(f"Test download failed (expected for demo): {e}")
        
        logger.info("Downloader test completed!")
        
    except Exception as e:
        logger.error(f"Error testing downloader: {e}")
        raise


if __name__ == "__main__":
    main()