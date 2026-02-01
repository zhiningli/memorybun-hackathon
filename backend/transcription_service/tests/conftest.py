"""
Shared test fixtures and configuration for Transcription Service

This module provides mock Redis fixtures to enable isolated testing
without requiring an external Redis instance.
"""
import os
import sys
from pathlib import Path
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from contextlib import asynccontextmanager

# IMPORTANT: Set TESTING=1 BEFORE importing any app modules
# This disables rate limiting and other test-unfriendly features
os.environ["TESTING"] = "1"

# Add the transcription_service directory to Python path so imports work
service_dir = Path(__file__).parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))


class MockRedisPipeline:
    """Mock Redis pipeline for atomic operations"""
    
    def __init__(self, mock_redis: 'MockRedis'):
        self._redis = mock_redis
        self._commands: list = []
    
    def hgetall(self, key: str):
        """Queue hgetall command"""
        self._commands.append(('hgetall', key))
        return self
    
    def hset(self, key: str, mapping: dict = None, **kwargs):
        """Queue hset command"""
        self._commands.append(('hset', key, mapping or kwargs))
        return self
    
    def expire(self, key: str, seconds: int):
        """Queue expire command"""
        self._commands.append(('expire', key, seconds))
        return self
    
    async def execute(self):
        """Execute all queued commands and return results"""
        results = []
        for cmd in self._commands:
            if cmd[0] == 'hgetall':
                result = await self._redis.hgetall(cmd[1])
                results.append(result)
            elif cmd[0] == 'hset':
                result = await self._redis.hset(cmd[1], mapping=cmd[2])
                results.append(result)
            elif cmd[0] == 'expire':
                result = await self._redis.expire(cmd[1], cmd[2])
                results.append(result)
        self._commands.clear()
        return results
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockRedis:
    """
    In-memory Redis mock that simulates Redis operations.
    Supports list operations (queue) and hash operations (session state).
    """
    
    def __init__(self):
        self._data: dict = {}  # Stores all Redis keys
        self._ttl: dict = {}   # Stores TTL for keys
        self._waiting_brpop: asyncio.Event = asyncio.Event()
    
    async def lpush(self, key: str, *values) -> int:
        """Push values to left of list"""
        if key not in self._data:
            self._data[key] = []
        for value in values:
            self._data[key].insert(0, value)
        self._waiting_brpop.set()  # Signal waiting brpop
        return len(self._data[key])
    
    async def brpop(self, key: str, timeout: int = 0):
        """Blocking pop from right of list"""
        if key in self._data and len(self._data[key]) > 0:
            value = self._data[key].pop()
            return (key, value)
        
        # Wait for data or timeout
        try:
            await asyncio.wait_for(self._waiting_brpop.wait(), timeout=timeout)
            self._waiting_brpop.clear()
            if key in self._data and len(self._data[key]) > 0:
                value = self._data[key].pop()
                return (key, value)
        except asyncio.TimeoutError:
            pass
        return None
    
    async def llen(self, key: str) -> int:
        """Get length of list"""
        if key not in self._data:
            return 0
        return len(self._data[key])
    
    async def lindex(self, key: str, index: int):
        """Get element at index in list"""
        if key not in self._data or len(self._data[key]) == 0:
            return None
        try:
            return self._data[key][index]
        except IndexError:
            return None
    
    async def delete(self, key: str) -> int:
        """Delete a key"""
        if key in self._data:
            del self._data[key]
            if key in self._ttl:
                del self._ttl[key]
            return 1
        return 0
    
    # Hash operations for session state
    async def hset(self, key: str, mapping: dict = None, **kwargs) -> int:
        """Set hash fields"""
        if key not in self._data:
            self._data[key] = {}
        if mapping:
            self._data[key].update(mapping)
        if kwargs:
            self._data[key].update(kwargs)
        return len(mapping) if mapping else len(kwargs)
    
    async def hget(self, key: str, field: str):
        """Get hash field value"""
        if key not in self._data:
            return None
        return self._data[key].get(field)
    
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        if key not in self._data:
            return {}
        return dict(self._data[key])
    
    async def hdel(self, key: str, *fields) -> int:
        """Delete hash fields"""
        if key not in self._data:
            return 0
        deleted = 0
        for field in fields:
            if field in self._data[key]:
                del self._data[key][field]
                deleted += 1
        return deleted
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on key (simulated - doesn't actually expire)"""
        if key in self._data:
            self._ttl[key] = seconds
            return True
        return False
    
    async def ping(self) -> bool:
        """Ping - always succeeds for mock"""
        return True
    
    def pipeline(self):
        """Return a mock pipeline for atomic operations"""
        return MockRedisPipeline(self)


class MockRedisClient:
    """
    Mock RedisClient that wraps MockRedis.
    Matches the interface of services.redis_client.RedisClient
    """
    
    def __init__(self):
        self._redis = MockRedis()
        self._connected = True
    
    async def connect(self) -> None:
        self._connected = True
    
    async def disconnect(self) -> None:
        self._connected = False
        self._redis._data.clear()
    
    async def health_check(self) -> bool:
        return self._connected
    
    def get_client(self):
        return self._redis
    
    @property
    def is_connected(self) -> bool:
        return self._connected


# Store the mock client instance per test for isolation
_mock_redis_client = None


def get_mock_redis_client():
    """Get the mock Redis client for current test"""
    global _mock_redis_client
    if _mock_redis_client is None:
        _mock_redis_client = MockRedisClient()
    return _mock_redis_client


@pytest.fixture(autouse=True)
async def mock_redis(request):
    """
    Automatically mock Redis for all tests.
    Each test gets a fresh, isolated mock Redis instance.
    
    Tests in test_redis_client.py are excluded from mocking since they
    specifically test the real Redis client.
    """
    global _mock_redis_client
    
    # Skip mocking for tests that specifically test the real Redis client
    if 'test_redis_client' in request.fspath.basename:
        yield None
        return
    
    # Create fresh mock for each test
    _mock_redis_client = MockRedisClient()
    
    # Patch get_redis_client to return our mock
    with patch('services.redis_client.get_redis_client', get_mock_redis_client):
        with patch('services.redis_client._redis_client', _mock_redis_client):
            yield _mock_redis_client
    
    # Clean up
    _mock_redis_client = None


@pytest.fixture
async def mock_redis_client():
    """
    Explicit fixture for tests that need direct access to mock client.
    """
    return get_mock_redis_client()
