"""
Tests for caching utilities with Redis backend.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pickle

from src.content_research_pipeline.utils.caching import (
    cache_result,
    cache_sync_result,
    CacheManager,
    _create_cache_key
)


class TestCaching:
    """Test caching utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = MagicMock()
        self.mock_redis.ping.return_value = True
    
    def test_create_cache_key(self):
        """Test cache key creation."""
        key = _create_cache_key("test_func", (1, 2), {"arg": "value"})
        
        assert "test_func" in key
        assert isinstance(key, str)
    
    @pytest.mark.asyncio
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    async def test_cache_result_redis_hit(self, mock_get_redis):
        """Test cache hit with Redis backend."""
        mock_get_redis.return_value = self.mock_redis
        
        cached_value = "cached_result"
        self.mock_redis.get.return_value = pickle.dumps(cached_value)
        
        @cache_result()
        async def test_func():
            return "new_result"
        
        result = await test_func()
        
        assert result == cached_value
        self.mock_redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    async def test_cache_result_redis_miss(self, mock_get_redis):
        """Test cache miss with Redis backend."""
        mock_get_redis.return_value = self.mock_redis
        
        self.mock_redis.get.return_value = None
        
        @cache_result()
        async def test_func():
            return "new_result"
        
        result = await test_func()
        
        assert result == "new_result"
        self.mock_redis.get.assert_called_once()
        self.mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    async def test_cache_result_fallback_to_memory(self, mock_get_redis):
        """Test fallback to in-memory cache when Redis is unavailable."""
        mock_get_redis.return_value = None
        
        call_count = 0
        
        @cache_result()
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "result"
        
        # First call - cache miss
        result1 = await test_func()
        assert result1 == "result"
        assert call_count == 1
        
        # Second call - cache hit (from memory)
        result2 = await test_func()
        assert result2 == "result"
        assert call_count == 1  # Function not called again
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_sync_result_redis_hit(self, mock_get_redis):
        """Test synchronous cache hit with Redis backend."""
        mock_get_redis.return_value = self.mock_redis
        
        cached_value = "cached_result"
        self.mock_redis.get.return_value = pickle.dumps(cached_value)
        
        @cache_sync_result()
        def test_func():
            return "new_result"
        
        result = test_func()
        
        assert result == cached_value
        self.mock_redis.get.assert_called_once()
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_sync_result_redis_miss(self, mock_get_redis):
        """Test synchronous cache miss with Redis backend."""
        mock_get_redis.return_value = self.mock_redis
        
        self.mock_redis.get.return_value = None
        
        @cache_sync_result()
        def test_func():
            return "new_result"
        
        result = test_func()
        
        assert result == "new_result"
        self.mock_redis.get.assert_called_once()
        self.mock_redis.setex.assert_called_once()


class TestCacheManager:
    """Test CacheManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = MagicMock()
        self.mock_redis.ping.return_value = True
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_get_redis(self, mock_get_redis):
        """Test getting value from Redis cache."""
        mock_get_redis.return_value = self.mock_redis
        
        value = "test_value"
        self.mock_redis.get.return_value = pickle.dumps(value)
        
        manager = CacheManager()
        result = manager.get("test_key")
        
        assert result == value
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_set_redis(self, mock_get_redis):
        """Test setting value in Redis cache."""
        mock_get_redis.return_value = self.mock_redis
        
        manager = CacheManager()
        manager.set("test_key", "test_value", expire_after=3600)
        
        self.mock_redis.setex.assert_called_once()
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_delete_redis(self, mock_get_redis):
        """Test deleting value from Redis cache."""
        mock_get_redis.return_value = self.mock_redis
        
        self.mock_redis.delete.return_value = 1
        
        manager = CacheManager()
        result = manager.delete("test_key")
        
        assert result is True
        self.mock_redis.delete.assert_called_once()
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_exists_redis(self, mock_get_redis):
        """Test checking if key exists in Redis cache."""
        mock_get_redis.return_value = self.mock_redis
        
        self.mock_redis.exists.return_value = 1
        
        manager = CacheManager()
        result = manager.exists("test_key")
        
        assert result is True
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_clear_redis(self, mock_get_redis):
        """Test clearing Redis cache."""
        mock_get_redis.return_value = self.mock_redis
        
        # Mock scan to return some keys
        self.mock_redis.scan.return_value = (0, [b"key1", b"key2"])
        
        manager = CacheManager()
        manager.clear()
        
        self.mock_redis.delete.assert_called()
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_fallback_to_memory(self, mock_get_redis):
        """Test CacheManager falls back to in-memory cache."""
        mock_get_redis.return_value = None
        
        manager = CacheManager()
        
        # Set a value
        manager.set("test_key", "test_value")
        
        # Get the value
        result = manager.get("test_key")
        
        assert result == "test_value"
    
    @patch('src.content_research_pipeline.utils.caching._get_redis_client')
    def test_cache_manager_cleanup(self, mock_get_redis):
        """Test cleanup of expired entries."""
        mock_get_redis.return_value = None
        
        manager = CacheManager()
        count = manager.cleanup()
        
        # Should return 0 for empty cache
        assert count >= 0
