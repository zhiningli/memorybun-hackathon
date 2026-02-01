"""
Tests for Redis Client Wrapper

Note: These tests require a running Redis instance.
For CI/CD, use a Redis container or mock Redis.

To run these tests:
1. Start Redis: docker-compose up -d redis (from backend directory)
2. Or run Redis locally on localhost:6379
"""

import pytest
import pytest_asyncio
from services.redis_client import RedisClient, get_redis_client, initialize_redis, close_redis


# Check if Redis is available before running tests
REDIS_AVAILABLE = None


async def check_redis_available():
    """Check if Redis is available by trying to connect"""
    try:
        client = RedisClient()
        await client.connect()
        await client.disconnect()
        return True
    except Exception:
        return False


@pytest_asyncio.fixture
async def redis_client():
    """Fixture that provides a Redis client instance"""
    if not await check_redis_available():
        pytest.skip("Redis is not available. Start Redis with: docker-compose up -d redis")
    
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_redis_client_connection(redis_client):
    """Test that Redis client can connect"""
    if not await check_redis_available():
        pytest.skip("Redis is not available")
    assert redis_client.is_connected
    assert await redis_client.health_check()


@pytest.mark.asyncio
async def test_redis_client_health_check(redis_client):
    """Test Redis health check"""
    assert await redis_client.health_check() is True


@pytest.mark.asyncio
async def test_redis_client_get_client(redis_client):
    """Test getting the underlying Redis client"""
    client = redis_client.get_client()
    assert client is not None
    
    # Test that we can use the client
    result = await client.ping()
    assert result is True


@pytest.mark.asyncio
async def test_redis_client_basic_operations(redis_client):
    """Test basic Redis operations"""
    client = redis_client.get_client()
    
    # Test SET and GET
    await client.set("test_key", "test_value")
    value = await client.get("test_key")
    assert value == "test_value"
    
    # Test DELETE
    await client.delete("test_key")
    value = await client.get("test_key")
    assert value is None


@pytest.mark.asyncio
async def test_redis_client_singleton():
    """Test that get_redis_client returns singleton"""
    client1 = get_redis_client()
    client2 = get_redis_client()
    assert client1 is client2


@pytest.mark.asyncio
async def test_redis_client_disconnect():
    """Test that disconnect works correctly"""
    if not await check_redis_available():
        pytest.skip("Redis is not available")
    
    client = RedisClient()
    await client.connect()
    assert client.is_connected
    
    await client.disconnect()
    assert not client.is_connected
    
    # Should raise error when trying to get client after disconnect
    with pytest.raises(RuntimeError):
        client.get_client()


@pytest.mark.asyncio
async def test_redis_client_initialize_and_close():
    """Test initialize_redis and close_redis functions"""
    if not await check_redis_available():
        pytest.skip("Redis is not available")
    
    # Make sure we start fresh
    await close_redis()
    
    # Initialize
    await initialize_redis()
    
    # Verify it's connected
    client = get_redis_client()
    assert client.is_connected
    health = await client.health_check()
    assert health is True
    
    # Close
    await close_redis()
    
    # Verify it's disconnected (don't check health after close as event loop may be closing)
    assert not client.is_connected

