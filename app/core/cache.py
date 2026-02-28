"""
Redis Cache Service

Provides caching functionality using Redis for improved performance
on read-heavy endpoints.
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.core.config import settings


class CacheService:
    """Redis cache service for async operations"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        try:
            redis_client = await self.get_redis()
            value = await redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            # Log error but don't break the application
            print(f"Cache GET error for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: int = 300  # 5 minutes default
    ) -> bool:
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache (will be serialized to JSON)
            ttl: Time to live in seconds (default: 300)

        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self.get_redis()
            serialized = json.dumps(value, default=str)  # default=str handles datetime
            await redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            redis_client = await self.get_redis()
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache DELETE error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Pattern to match (e.g., "school:*")

        Returns:
            Number of keys deleted
        """
        try:
            redis_client = await self.get_redis()
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await redis_client.delete(*keys)
            return 0
        except RuntimeError as e:
            # Event loop is closed - this can happen during test cleanup
            if "Event loop is closed" in str(e):
                return 0
            print(f"Cache DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0
        except Exception as e:
            print(f"Cache DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0

    async def clear_all(self) -> bool:
        """
        Clear all cache (use with caution!)

        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self.get_redis()
            await redis_client.flushdb()
            return True
        except Exception as e:
            print(f"Cache CLEAR_ALL error: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                # Ignore errors during cleanup (e.g., event loop already closed)
                print(f"Cache close error (ignored): {e}")
            finally:
                self._redis = None


# Singleton instance
cache_service = CacheService()


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        MD5 hash of the arguments
    """
    # Create a string representation of all arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # Create MD5 hash for consistent key length
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(prefix: str, ttl: int = 300, key_builder: Optional[Callable] = None):
    """
    Decorator for caching function results

    Args:
        prefix: Cache key prefix (e.g., "school", "student")
        ttl: Time to live in seconds (default: 300 = 5 minutes)
        key_builder: Optional custom function to build cache key

    Usage:
        @cached(prefix="school", ttl=600)
        async def get_school(school_id: int):
            # ... fetch from database ...
            return school

    Cache key format: {prefix}:{generated_hash}
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                cache_key = f"{prefix}:{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Cache miss - execute function
            result = await func(*args, **kwargs)

            # Store in cache (only if result is not None)
            if result is not None:
                await cache_service.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


async def invalidate_cache(prefix: str, *args, **kwargs):
    """
    Invalidate cache for a specific resource

    Args:
        prefix: Cache key prefix
        *args: Arguments to identify the specific cache entry
        **kwargs: Keyword arguments

    Usage:
        await invalidate_cache("school", school_id=1)
    """
    cache_key = f"{prefix}:{generate_cache_key(*args, **kwargs)}"
    await cache_service.delete(cache_key)


async def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache entries matching a pattern

    Args:
        pattern: Redis pattern (e.g., "school:*", "student:123:*")

    Usage:
        await invalidate_cache_pattern("school:*")  # Clear all school caches
    """
    try:
        await cache_service.delete_pattern(pattern)
    except RuntimeError as e:
        # Event loop is closed - ignore during test cleanup
        if "Event loop is closed" not in str(e):
            raise
    except Exception:
        # Silently ignore cache invalidation errors
        # The cache will expire naturally via TTL
        pass
