"""Tests for INEP web scraper."""

import pytest
from unittest.mock import Mock, patch

from enem_ingestion.web_scraper import INEPScraper


@pytest.fixture
def scraper():
    """Create INEPScraper instance."""
    return INEPScraper()


def test_scraper_initialization(scraper):
    """Test INEPScraper initialization."""
    assert scraper.session is not None
    assert len(scraper.enem_pages) > 0
    assert "User-Agent" in scraper.session.headers


def test_extract_pdf_links(scraper):
    """Test PDF link extraction from HTML."""
    html_content = '''
    <html>
        <body>
            <a href="/enem/2024_prova.pdf">ENEM 2024 Prova</a>
            <a href="https://example.com/enem_gabarito_2024.pdf">Gabarito</a>
            <a href="/other_file.txt">Not a PDF</a>
            <a href="/unrelated.pdf">Unrelated PDF</a>
        </body>
    </html>
    '''
    
    base_url = "https://download.inep.gov.br"
    links = scraper._extract_pdf_links(html_content, base_url)
    
    # Should find 2 PDF links related to ENEM
    assert len(links) == 2
    assert any("2024_prova.pdf" in link for link in links)
    assert any("enem_gabarito_2024.pdf" in link for link in links)


def test_categorize_file(scraper):
    """Test file categorization."""
    # Test gabarito file
    gabarito_info = scraper._categorize_file(
        "https://example.com/2024_GAB_1_DIA.pdf",
        "2024_GAB_1_DIA.pdf"
    )
    assert gabarito_info['type'] == 'gabarito'
    assert gabarito_info['year'] == 2024
    
    # Test caderno questoes file
    prova_info = scraper._categorize_file(
        "https://example.com/2023_PV_impresso_D1_CD1.pdf",
        "2023_PV_impresso_D1_CD1.pdf"
    )
    assert prova_info['type'] == 'caderno_questoes'
    assert prova_info['year'] == 2023
    assert prova_info['color'] == 'azul'
    
    # Test amarelo color detection
    amarelo_info = scraper._categorize_file(
        "https://example.com/2023_PV_impresso_D1_CD2.pdf",
        "2023_PV_impresso_D1_CD2.pdf"
    )
    assert amarelo_info['color'] == 'amarelo'


@patch('enem_ingestion.web_scraper.requests.Session')
def test_scrape_enem_urls(mock_session_class, scraper):
    """Test ENEM URL scraping."""
    # Mock HTML response
    mock_html = '''
    <html>
        <body>
            <a href="/enem/2024_PV_impresso_D1_CD1.pdf">ENEM 2024 Prova Azul</a>
            <a href="/enem/2024_GAB_1_DIA.pdf">ENEM 2024 Gabarito</a>
            <a href="/enem/2023_PV_impresso_D1_CD1.pdf">ENEM 2023 Prova</a>
        </body>
    </html>
    '''
    
    mock_response = Mock()
    mock_response.text = mock_html
    mock_response.raise_for_status.return_value = None
    
    mock_session = Mock()
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session
    
    scraper.session = mock_session
    
    result = scraper.scrape_enem_urls(target_years=[2024, 2023])
    
    assert isinstance(result, dict)
    # Should have found files for both years
    assert 2024 in result or 2023 in result


def test_get_fallback_urls(scraper):
    """Test fallback URL generation."""
    fallback = scraper.get_fallback_urls()
    
    assert isinstance(fallback, dict)
    assert 2024 in fallback
    assert len(fallback[2024]) > 0
    
    # Check structure of fallback entries
    for file_info in fallback[2024]:
        assert 'type' in file_info
        assert 'url' in file_info
        assert 'year' in file_info


@patch('enem_ingestion.web_scraper.requests.Session')
def test_validate_discovered_urls(mock_session_class, scraper):
    """Test URL validation."""
    # Mock successful HEAD responses
    mock_response = Mock()
    mock_response.status_code = 200
    
    mock_session = Mock()
    mock_session.head.return_value = mock_response
    mock_session_class.return_value = mock_session
    
    scraper.session = mock_session
    
    test_urls = {
        2024: [
            {
                'url': 'https://example.com/valid.pdf',
                'type': 'caderno_questoes',
                'year': 2024
            }
        ]
    }
    
    validated = scraper.validate_discovered_urls(test_urls)
    
    assert 2024 in validated
    assert len(validated[2024]) == 1


@patch('enem_ingestion.web_scraper.requests.Session')
def test_scraping_error_handling(mock_session_class, scraper):
    """Test error handling during scraping."""
    # Mock failed request
    mock_session = Mock()
    mock_session.get.side_effect = Exception("Network error")
    mock_session_class.return_value = mock_session
    
    scraper.session = mock_session
    
    # Should not raise exception, return empty dict
    result = scraper.scrape_enem_urls(target_years=[2024])
    assert isinstance(result, dict)