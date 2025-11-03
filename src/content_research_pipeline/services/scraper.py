"""
Web scraping service for extracting content from URLs.
"""

import asyncio
from typing import Optional
from datetime import datetime
import requests
import trafilatura

from ..config.settings import settings
from ..config.logging import get_logger
from ..data.models import ScrapedContent, ContentType
from ..utils.caching import cache_result

logger = get_logger(__name__)


class ScraperService:
    """Service for scraping web content."""
    
    def __init__(self):
        """Initialize the scraper service."""
        self.timeout = 30
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    @cache_result(expire_after=7200)  # Cache for 2 hours
    async def scrape_url(self, url: str) -> ScrapedContent:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapedContent model with extracted text
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Fetch the URL content in a thread pool
            downloaded = await asyncio.to_thread(
                self._download_url,
                url
            )
            
            if downloaded is None:
                return ScrapedContent(
                    type=ContentType.ERROR,
                    url=url,
                    raw_text="",
                    error_message="Failed to download URL",
                    scraped_at=datetime.now()
                )
            
            # Extract text content using trafilatura
            text_content = await asyncio.to_thread(
                trafilatura.extract,
                downloaded,
                include_comments=False,
                include_tables=True
            )
            
            if text_content is None or len(text_content.strip()) == 0:
                return ScrapedContent(
                    type=ContentType.ERROR,
                    url=url,
                    raw_text="",
                    error_message="No text content extracted",
                    scraped_at=datetime.now()
                )
            
            # Also extract metadata
            metadata = trafilatura.extract_metadata(downloaded)
            
            # Build the scraped content
            scraped = ScrapedContent(
                type=ContentType.TEXT,
                url=url,
                raw_text=text_content,
                text_content=text_content,
                scraped_at=datetime.now()
            )
            
            logger.info(f"Successfully scraped {len(text_content)} characters from {url}")
            return scraped
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return ScrapedContent(
                type=ContentType.ERROR,
                url=url,
                raw_text="",
                error_message=str(e),
                scraped_at=datetime.now()
            )
    
    def _download_url(self, url: str) -> Optional[str]:
        """
        Download URL content.
        
        Args:
            url: URL to download
            
        Returns:
            HTML content or None if failed
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            logger.warning(f"Failed to download {url}: {str(e)}")
            return None
    
    async def scrape_urls(self, urls: list) -> list[ScrapedContent]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of ScrapedContent models
        """
        logger.info(f"Scraping {len(urls)} URLs")
        
        # Create tasks for all URLs
        tasks = [self.scrape_url(url) for url in urls]
        
        # Execute scraping concurrently with a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def scrape_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[scrape_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions and return valid results
        scraped_contents = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraping task failed: {result}")
            elif isinstance(result, ScrapedContent):
                scraped_contents.append(result)
        
        successful = sum(1 for s in scraped_contents if s.type != ContentType.ERROR)
        logger.info(f"Successfully scraped {successful}/{len(urls)} URLs")
        
        return scraped_contents


# Global scraper service instance
scraper_service = ScraperService()
