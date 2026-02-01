"""
Redis Client Wrapper - Async Redis connection with connection pooling.

Provides a singleton Redis client instance for the transcription service.
Handles connection pooling, health checks, and graceful error handling.
"""

import redis.asyncio as aioredis
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper with connection pooling.
    
    Singleton pattern - use get_redis_client() to get the instance.
    """
    
    def __init__(self):
        """Initialize Redis client (don't call directly, use get_redis_client())"""
        self._client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
    
    async def connect(self) -> None:
        """
        Establish Redis connection with connection pooling.
        
        Raises:
            redis.ConnectionError: If connection fails
        """
        if self._client is not None:
            logger.warning("Redis client already connected")
            return
        
        try:
            # Create connection pool for better performance
            self._connection_pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=10,
                socket_timeout=settings.redis_socket_timeout,
                socket_connect_timeout=settings.redis_socket_connect_timeout,
                decode_responses=True,  # Automatically decode responses to strings
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Create Redis client from pool
            self._client = aioredis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True
            )
            
            # Test connection
            await self._client.ping()
            logger.info(f"Redis client connected to {settings.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            self._connection_pool = None
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection and connection pool"""
        if self._client:
            try:
                await self._client.aclose()
                logger.info("Redis client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis client: {e}")
            finally:
                self._client = None
        
        if self._connection_pool:
            try:
                await self._connection_pool.aclose()
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")
            finally:
                self._connection_pool = None
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if self._client is None:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    def get_client(self) -> aioredis.Redis:
        """
        Get the Redis client instance.
        
        Returns:
            Redis client instance
            
        Raises:
            RuntimeError: If client is not connected
        """
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected (without health check)"""
        return self._client is not None


# Global singleton instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance (singleton pattern).
    
    Returns:
        RedisClient instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def initialize_redis() -> None:
    """
    Initialize Redis connection (call during app startup).
    
    Raises:
        redis.ConnectionError: If connection fails
    """
    client = get_redis_client()
    await client.connect()


async def close_redis() -> None:
    """Close Redis connection (call during app shutdown)"""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None

