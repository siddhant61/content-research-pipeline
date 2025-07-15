"""
Search service for Google Search API integration.
"""

from typing import List, Dict, Any, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.utilities import GoogleSearchAPIWrapper

from ..config.settings import settings
from ..config.logging import get_logger
from ..data.models import SearchResult, ImageResult, VideoResult
from ..utils.caching import cache_result

logger = get_logger(__name__)


class SearchService:
    """Service for handling search operations."""
    
    def __init__(self):
        """Initialize the search service."""
        self.search_wrapper = GoogleSearchAPIWrapper()
        self.cse_service = build("customsearch", "v1", developerKey=settings.google_api_key)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(HttpError)
    )
    def _rate_limited_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Perform rate-limited search with retry logic."""
        try:
            logger.info(f"Performing search for query: {query}")
            results = self.search_wrapper.results(query, num_results=num_results)
            logger.info(f"Search completed. Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise
    
    async def search_web(self, query: str, num_results: int = None) -> List[SearchResult]:
        """Search the web for general results."""
        if num_results is None:
            num_results = settings.max_search_results
            
        try:
            # Run search in thread pool to avoid blocking
            results = await asyncio.to_thread(
                self._rate_limited_search, 
                query, 
                num_results
            )
            
            # Convert to SearchResult models
            search_results = []
            for result in results:
                try:
                    search_result = SearchResult(
                        title=result.get("title", "No Title"),
                        snippet=result.get("snippet", "No Description"),
                        link=result.get("link", ""),
                        source=result.get("displayLink", "Unknown Source")
                    )
                    search_results.append(search_result)
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            return search_results
            
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            return []
    
    async def search_news(self, query: str, num_results: int = None) -> List[SearchResult]:
        """Search for news articles."""
        if num_results is None:
            num_results = settings.max_search_results
            
        # Add news site restrictions for better results
        news_query = f"{query} site:news.google.com OR site:reuters.com OR site:apnews.com OR site:bbc.com OR site:cnn.com"
        
        try:
            results = await asyncio.to_thread(
                self._rate_limited_search, 
                news_query, 
                num_results
            )
            
            news_results = []
            for result in results:
                try:
                    news_result = SearchResult(
                        title=result.get("title", "No Title"),
                        snippet=result.get("snippet", "No Description"),
                        link=result.get("link", ""),
                        source=result.get("displayLink", "Unknown Source")
                    )
                    news_results.append(news_result)
                except Exception as e:
                    logger.warning(f"Failed to parse news result: {e}")
                    continue
            
            logger.info(f"Found {len(news_results)} news articles")
            return news_results
            
        except Exception as e:
            logger.error(f"News search failed: {str(e)}")
            return []
    
    @cache_result(expire_after=3600)
    async def search_images(self, query: str, num_results: int = 10) -> List[ImageResult]:
        """Search for images."""
        logger.info(f"Searching for images: {query}")
        
        try:
            # Run image search in thread pool
            def _search_images():
                return self.cse_service.cse().list(
                    q=query,
                    cx=settings.google_cse_id,
                    searchType="image",
                    num=num_results
                ).execute()
            
            res = await asyncio.to_thread(_search_images)
            
            image_results = []
            for item in res.get('items', []):
                try:
                    image_result = ImageResult(
                        title=item.get("title", "No Title"),
                        link=item.get("link", ""),
                        thumbnail=item.get("image", {}).get("thumbnailLink", ""),
                        source=item.get("displayLink", "Unknown Source")
                    )
                    image_results.append(image_result)
                except Exception as e:
                    logger.warning(f"Failed to parse image result: {e}")
                    continue
            
            logger.info(f"Found {len(image_results)} images")
            return image_results
            
        except Exception as e:
            logger.error(f"Image search failed: {str(e)}")
            return []
    
    @cache_result(expire_after=3600)
    async def search_videos(self, query: str, num_results: int = 5) -> List[VideoResult]:
        """Search for videos."""
        logger.info(f"Searching for videos: {query}")
        
        try:
            # Search for YouTube videos specifically
            video_query = f"{query} video site:youtube.com"
            results = await asyncio.to_thread(
                self._rate_limited_search, 
                video_query, 
                num_results
            )
            
            video_results = []
            for result in results:
                try:
                    # Only include YouTube links
                    if "youtube.com" in result.get("link", ""):
                        video_result = VideoResult(
                            title=result.get("title", "No Title"),
                            link=result.get("link", ""),
                            thumbnail=result.get("pagemap", {}).get("videoobject", [{}])[0].get("thumbnailurl", ""),
                            snippet=result.get("snippet", "No Description"),
                            source=result.get("displayLink", "Unknown Source")
                        )
                        video_results.append(video_result)
                except Exception as e:
                    logger.warning(f"Failed to parse video result: {e}")
                    continue
            
            logger.info(f"Found {len(video_results)} videos")
            return video_results
            
        except Exception as e:
            logger.error(f"Video search failed: {str(e)}")
            return []
    
    async def search_all(self, query: str) -> Dict[str, Any]:
        """Search for all types of content simultaneously."""
        logger.info(f"Performing comprehensive search for: {query}")
        
        # Run all searches in parallel
        web_task = asyncio.create_task(self.search_web(query))
        news_task = asyncio.create_task(self.search_news(query))
        images_task = asyncio.create_task(self.search_images(query))
        videos_task = asyncio.create_task(self.search_videos(query))
        
        try:
            web_results, news_results, image_results, video_results = await asyncio.gather(
                web_task, news_task, images_task, videos_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from individual searches
            if isinstance(web_results, Exception):
                logger.error(f"Web search failed: {web_results}")
                web_results = []
            
            if isinstance(news_results, Exception):
                logger.error(f"News search failed: {news_results}")
                news_results = []
            
            if isinstance(image_results, Exception):
                logger.error(f"Image search failed: {image_results}")
                image_results = []
            
            if isinstance(video_results, Exception):
                logger.error(f"Video search failed: {video_results}")
                video_results = []
            
            return {
                "web_results": web_results,
                "news_results": news_results,
                "image_results": image_results,
                "video_results": video_results
            }
            
        except Exception as e:
            logger.error(f"Comprehensive search failed: {str(e)}")
            return {
                "web_results": [],
                "news_results": [],
                "image_results": [],
                "video_results": []
            }


# Global search service instance
search_service = SearchService() 