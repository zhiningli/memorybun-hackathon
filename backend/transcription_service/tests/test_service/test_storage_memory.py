import pytest
import asyncio
import time
from services.storage.memory import MemoryStorage

class TestMemoryStorage:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        """Test simple save and retrieval"""
        storage = MemoryStorage(ttl_seconds=3600)
        data = b"test data"
        
        file_id = await storage.save("file1", data, "text/plain")
        assert file_id == "file1"
        
        retrieved_data = await storage.get("file1")
        assert retrieved_data == data

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deletion"""
        storage = MemoryStorage()
        await storage.save("file2", b"data", "text/plain")
        
        assert await storage.delete("file2") is True
        assert await storage.delete("file2") is False  # Already deleted
        
        # Verify it's gone
        with pytest.raises(FileNotFoundError):
            await storage.get("file2")

    @pytest.mark.asyncio
    async def test_ttl_cleanup(self):
        """Test that expired items are cleaned up on next save"""
        # Short TTL
        storage = MemoryStorage(ttl_seconds=1)
        
        # Save item 1
        await storage.save("file1", b"data1", "text/plain")
        
        # Verify it exists
        d = await storage.get("file1")
        assert d == b"data1"
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Verify it still technically exists in memory (cleanup is lazy)
        # Note: Our implementation cleans up on SAVE, checking get() doesn't trigger cleanup
        # But get() typically doesn't check expiry? Let's check implementation behavior
        # Implementation of get: just returns if in dict.
        # Implementation of cleanup: called on save()
        
        # Save item 2 - this should trigger cleanup of item 1
        await storage.save("file2", b"data2", "text/plain")
        
        # Item 1 should be gone now
        with pytest.raises(FileNotFoundError):
             await storage.get("file1")
             
        # Item 2 should be there
        d2 = await storage.get("file2")
        assert d2 == b"data2"

    @pytest.mark.asyncio
    async def test_cleanup_respects_valid_items(self):
        """Test that valid items are NOT cleaned up"""
        storage = MemoryStorage(ttl_seconds=10)
        
        await storage.save("file1", b"data1", "text/plain")
        time.sleep(0.1)
        await storage.save("file2", b"data2", "text/plain")
        
        # Both should exist
        await storage.get("file1")
        await storage.get("file2")
