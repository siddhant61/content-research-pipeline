"""
Tests for scraper service.
"""

import pytest
from unittest.mock import patch, Mock
from src.content_research_pipeline.services.scraper import ScraperService
from src.content_research_pipeline.data.models import ScrapedContent, ContentType


class TestScraperService:
    """Test scraper service functionality."""
    
    @pytest.fixture
    def scraper_service(self):
        """Create a scraper service instance."""
        return ScraperService()
    
    @pytest.mark.asyncio
    async def test_scrape_url_success(self, scraper_service):
        """Test successful URL scraping."""
        test_url = "https://example.com"
        test_html = "<html><body><p>Test content</p></body></html>"
        
        with patch.object(scraper_service, '_download_url', return_value=test_html):
            result = await scraper_service.scrape_url(test_url)
            
            assert isinstance(result, ScrapedContent)
            assert result.url == test_url
            assert result.type == ContentType.TEXT
            assert len(result.raw_text) > 0
    
    @pytest.mark.asyncio
    async def test_scrape_url_failure(self, scraper_service):
        """Test URL scraping failure."""
        test_url = "https://example.com"
        
        with patch.object(scraper_service, '_download_url', return_value=None):
            result = await scraper_service.scrape_url(test_url)
            
            assert isinstance(result, ScrapedContent)
            assert result.type == ContentType.ERROR
            assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_scrape_urls_multiple(self, scraper_service):
        """Test scraping multiple URLs."""
        test_urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
        
        test_html = "<html><body><p>Test content</p></body></html>"
        
        with patch.object(scraper_service, '_download_url', return_value=test_html):
            results = await scraper_service.scrape_urls(test_urls)
            
            assert len(results) == len(test_urls)
            assert all(isinstance(r, ScrapedContent) for r in results)
    
    def test_download_url_success(self, scraper_service):
        """Test successful URL download."""
        test_url = "https://example.com"
        test_html = "<html><body>Test</body></html>"
        
        mock_response = Mock()
        mock_response.text = test_html
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response):
            result = scraper_service._download_url(test_url)
            
            assert result == test_html
    
    def test_download_url_failure(self, scraper_service):
        """Test URL download failure."""
        test_url = "https://example.com"
        
        with patch('requests.get', side_effect=Exception("Network error")):
            result = scraper_service._download_url(test_url)
            
            assert result is None
