"""Tests for ENEM downloader module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil

from enem_ingestion.downloader import EnemDownloader


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def downloader(temp_cache_dir):
    """Create EnemDownloader instance with temporary cache."""
    return EnemDownloader(cache_dir=temp_cache_dir)


def test_downloader_initialization(temp_cache_dir):
    """Test EnemDownloader initialization."""
    downloader = EnemDownloader(cache_dir=temp_cache_dir)
    assert downloader.cache_dir == temp_cache_dir
    assert downloader.cache_dir.exists()
    assert downloader.max_retries == 3


def test_get_enem_urls(downloader):
    """Test getting ENEM URLs."""
    urls = downloader.get_enem_urls()
    
    assert isinstance(urls, dict)
    assert 2024 in urls
    assert 2023 in urls
    assert 2022 in urls
    assert 2021 in urls
    assert 2020 in urls
    
    # Check structure of URL entries
    for year, files in urls.items():
        assert isinstance(files, list)
        for file_info in files:
            assert "type" in file_info
            assert "url" in file_info
            assert file_info["type"] in ["caderno_questoes", "gabarito"]


def test_get_cached_file_path(downloader):
    """Test cached file path generation."""
    url = "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D1_CD1.pdf"
    year = 2024
    
    path = downloader._get_cached_file_path(url, year)
    
    assert path.parent.name == "2024"
    assert path.name == "2024_PV_impresso_D1_CD1.pdf"
    assert path.is_relative_to(downloader.cache_dir)


def test_is_valid_pdf(downloader, temp_cache_dir):
    """Test PDF validation."""
    # Create a valid PDF file
    valid_pdf = temp_cache_dir / "valid.pdf"
    with open(valid_pdf, 'wb') as f:
        f.write(b'%PDF-1.4\ntest content')
    
    # Create an invalid file
    invalid_pdf = temp_cache_dir / "invalid.pdf"
    with open(invalid_pdf, 'wb') as f:
        f.write(b'not a pdf')
    
    assert downloader._is_valid_pdf(valid_pdf) is True
    assert downloader._is_valid_pdf(invalid_pdf) is False


@patch('enem_ingestion.downloader.requests.Session')
def test_download_file_success(mock_session_class, downloader):
    """Test successful file download."""
    # Mock response
    mock_response = Mock()
    mock_response.content = b'%PDF-1.4\ntest pdf content'
    mock_response.raise_for_status.return_value = None
    
    mock_session = Mock()
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session
    
    # Replace the session instance
    downloader.session = mock_session
    
    url = "https://example.com/test.pdf"
    year = 2024
    
    file_path, was_downloaded = downloader.download_file(url, year)
    
    assert file_path.exists()
    assert was_downloaded is True
    assert downloader._is_valid_pdf(file_path)


def test_download_file_cached(downloader, temp_cache_dir):
    """Test using cached file."""
    # Create a cached file
    year_dir = temp_cache_dir / "2024"
    year_dir.mkdir()
    cached_file = year_dir / "test.pdf"
    with open(cached_file, 'wb') as f:
        f.write(b'%PDF-1.4\ncached content')
    
    url = "https://example.com/test.pdf"
    year = 2024
    
    file_path, was_downloaded = downloader.download_file(url, year)
    
    assert file_path == cached_file
    assert was_downloaded is False


def test_get_download_status(downloader, temp_cache_dir):
    """Test download status reporting."""
    # Create some test files
    year_dir = temp_cache_dir / "2024"
    year_dir.mkdir()
    
    # Valid PDF
    valid_pdf = year_dir / "valid.pdf"
    with open(valid_pdf, 'wb') as f:
        f.write(b'%PDF-1.4\ntest')
    
    # Invalid file
    invalid_file = year_dir / "invalid.pdf"
    with open(invalid_file, 'wb') as f:
        f.write(b'not pdf')
    
    status = downloader.get_download_status()
    
    assert 2024 in status
    assert status[2024]["downloaded"] >= 1  # At least the valid PDF
    assert "expected" in status[2024]


@patch('enem_ingestion.downloader.requests.Session')
def test_download_year(mock_session_class, downloader):
    """Test downloading files for a specific year."""
    # Mock successful responses
    mock_response = Mock()
    mock_response.content = b'%PDF-1.4\ntest content'
    mock_response.raise_for_status.return_value = None
    
    mock_session = Mock()
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session
    
    downloader.session = mock_session
    
    results = downloader.download_year(2024)
    
    assert isinstance(results, list)
    assert len(results) > 0
    
    for file_info, local_path in results:
        assert isinstance(file_info, dict)
        assert "type" in file_info
        assert "url" in file_info
        assert local_path.exists()


def test_download_invalid_year(downloader):
    """Test downloading invalid year raises error."""
    with pytest.raises(ValueError, match="not in target years"):
        downloader.download_year(1990)