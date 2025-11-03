"""
Caching utilities for the Content Research Pipeline.
"""

import asyncio
import functools
import json
import pickle
import time
import redis
from typing import Any, Callable, Dict, Optional, Union
from ..config.settings import settings
from ..config.logging import get_logger

logger = get_logger(__name__)

# In-memory cache storage (fallback)
_cache: Dict[str, tuple] = {}

# Redis cache client
_redis_client: Optional[redis.Redis] = None


def _get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create Redis client for caching.
    
    Returns:
        Redis client or None if connection fails
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=False,  # Use binary mode for pickle
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis cache client connected successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for caching: {e}")
            logger.info("Falling back to in-memory cache")
            _redis_client = None
    
    return _redis_client


def cache_result(expire_after: Optional[int] = None):
    """
    Decorator for caching function results with optional expiration.
    Uses Redis if available, otherwise falls back to in-memory cache.
    
    Args:
        expire_after: Expiration time in seconds. If None, uses settings default.
    """
    if expire_after is None:
        expire_after = settings.cache_expire_seconds
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = _create_cache_key(func.__name__, args, kwargs)
            redis_client = _get_redis_client()
            
            # Try Redis cache first
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.debug(f"Redis cache hit for {func.__name__}")
                        return pickle.loads(cached_data)
                    logger.debug(f"Redis cache miss for {func.__name__}")
                except Exception as e:
                    logger.warning(f"Redis cache read error: {e}, falling back to in-memory")
            
            # Fallback to in-memory cache
            if not redis_client and cache_key in _cache:
                result, timestamp = _cache[cache_key]
                if time.time() - timestamp < expire_after:
                    logger.debug(f"Memory cache hit for {func.__name__}")
                    return result
                else:
                    # Remove expired entry
                    del _cache[cache_key]
                    logger.debug(f"Memory cache expired for {func.__name__}")
            
            # Call the function and cache the result
            logger.debug(f"Cache miss for {func.__name__}, executing function")
            result = await func(*args, **kwargs)
            
            # Store in Redis if available
            if redis_client:
                try:
                    redis_client.setex(
                        cache_key,
                        expire_after,
                        pickle.dumps(result)
                    )
                    logger.debug(f"Stored result in Redis cache for {func.__name__}")
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")
            else:
                # Store in memory cache
                _cache[cache_key] = (result, time.time())
            
            return result
        
        return wrapper
    return decorator


def cache_sync_result(expire_after: Optional[int] = None):
    """
    Decorator for caching synchronous function results with optional expiration.
    Uses Redis if available, otherwise falls back to in-memory cache.
    
    Args:
        expire_after: Expiration time in seconds. If None, uses settings default.
    """
    if expire_after is None:
        expire_after = settings.cache_expire_seconds
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = _create_cache_key(func.__name__, args, kwargs)
            redis_client = _get_redis_client()
            
            # Try Redis cache first
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.debug(f"Redis cache hit for {func.__name__}")
                        return pickle.loads(cached_data)
                    logger.debug(f"Redis cache miss for {func.__name__}")
                except Exception as e:
                    logger.warning(f"Redis cache read error: {e}, falling back to in-memory")
            
            # Fallback to in-memory cache
            if not redis_client and cache_key in _cache:
                result, timestamp = _cache[cache_key]
                if time.time() - timestamp < expire_after:
                    logger.debug(f"Memory cache hit for {func.__name__}")
                    return result
                else:
                    # Remove expired entry
                    del _cache[cache_key]
                    logger.debug(f"Memory cache expired for {func.__name__}")
            
            # Call the function and cache the result
            logger.debug(f"Cache miss for {func.__name__}, executing function")
            result = func(*args, **kwargs)
            
            # Store in Redis if available
            if redis_client:
                try:
                    redis_client.setex(
                        cache_key,
                        expire_after,
                        pickle.dumps(result)
                    )
                    logger.debug(f"Stored result in Redis cache for {func.__name__}")
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")
            else:
                # Store in memory cache
                _cache[cache_key] = (result, time.time())
            
            return result
        
        return wrapper
    return decorator


def _create_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """
    Create a cache key from function name and arguments.
    
    Args:
        func_name: Name of the function
        args: Positional arguments
        kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    # Convert arguments to strings for hashing
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))
    
    # Create a simple hash-like key
    cache_key = f"{func_name}:{args_str}:{kwargs_str}"
    return cache_key


def clear_cache():
    """Clear all cached results."""
    global _cache
    _cache.clear()
    logger.info("Cache cleared")


def clear_expired_cache():
    """Clear only expired cache entries."""
    global _cache
    current_time = time.time()
    expired_keys = []
    
    for key, (result, timestamp) in _cache.items():
        if current_time - timestamp >= settings.cache_expire_seconds:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _cache[key]
    
    logger.info(f"Removed {len(expired_keys)} expired cache entries")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    current_time = time.time()
    expired_count = 0
    total_size = 0
    
    for key, (result, timestamp) in _cache.items():
        if current_time - timestamp >= settings.cache_expire_seconds:
            expired_count += 1
        
        # Estimate size (rough approximation)
        try:
            total_size += len(str(result))
        except:
            pass
    
    return {
        "total_entries": len(_cache),
        "expired_entries": expired_count,
        "active_entries": len(_cache) - expired_count,
        "estimated_size_bytes": total_size,
        "cache_expire_seconds": settings.cache_expire_seconds
    }


def remove_from_cache(func_name: str, *args, **kwargs):
    """
    Remove a specific entry from cache.
    
    Args:
        func_name: Name of the function
        *args: Positional arguments used when calling the function
        **kwargs: Keyword arguments used when calling the function
    """
    cache_key = _create_cache_key(func_name, args, kwargs)
    if cache_key in _cache:
        del _cache[cache_key]
        logger.debug(f"Removed cache entry for {func_name}")


class CacheManager:
    """Cache manager for more advanced caching operations with Redis backend."""
    
    def __init__(self):
        self.cache = _cache
        self.redis_client = _get_redis_client()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache by key."""
        # Try Redis first
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to in-memory
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < settings.cache_expire_seconds:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, expire_after: Optional[int] = None) -> None:
        """Set value in cache with optional expiration."""
        if expire_after is None:
            expire_after = settings.cache_expire_seconds
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(key, expire_after, pickle.dumps(value))
                logger.debug(f"Set cache entry in Redis: {key}")
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Fallback to in-memory
        self.cache[key] = (value, time.time())
        logger.debug(f"Set cache entry in memory: {key}")
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        deleted = False
        
        # Try Redis first
        if self.redis_client:
            try:
                deleted = self.redis_client.delete(key) > 0
                logger.debug(f"Deleted cache entry from Redis: {key}")
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        # Also delete from in-memory cache
        if key in self.cache:
            del self.cache[key]
            deleted = True
            logger.debug(f"Deleted cache entry from memory: {key}")
        
        return deleted
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache and is not expired."""
        # Try Redis first
        if self.redis_client:
            try:
                return self.redis_client.exists(key) > 0
            except Exception as e:
                logger.warning(f"Redis exists error: {e}")
        
        # Fallback to in-memory
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < settings.cache_expire_seconds:
                return True
            else:
                del self.cache[key]
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        # Clear Redis cache (use pattern matching)
        if self.redis_client:
            try:
                # Note: This clears the entire Redis DB, be careful in production
                # In production, you might want to use a namespace/prefix
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor, count=100)
                    if keys:
                        self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
                logger.info("Redis cache cleared via CacheManager")
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
        
        # Clear in-memory cache
        self.cache.clear()
        logger.info("Memory cache cleared via CacheManager")
    
    def cleanup(self) -> int:
        """Clean up expired entries and return count removed."""
        # Redis handles expiration automatically, so we only cleanup in-memory
        current_time = time.time()
        expired_keys = []
        
        for key, (result, timestamp) in self.cache.items():
            if current_time - timestamp >= settings.cache_expire_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries from memory")
        return len(expired_keys)


# Global cache manager instance
cache_manager = CacheManager()


# Background task to periodically clean expired cache entries
async def cache_cleanup_task():
    """Background task to clean up expired cache entries."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            cache_manager.cleanup()
        except asyncio.CancelledError:
            logger.info("Cache cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}")


# Start cleanup task when module is imported
_cleanup_task = None

def start_cache_cleanup():
    """Start the background cache cleanup task."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(cache_cleanup_task())
        logger.info("Started cache cleanup background task")

def stop_cache_cleanup():
    """Stop the background cache cleanup task."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Stopped cache cleanup background task") 