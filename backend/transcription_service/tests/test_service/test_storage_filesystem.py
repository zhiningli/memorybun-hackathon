import pytest
import asyncio
from pathlib import Path
from services.storage.filesystem import FileSystemStorage

class TestFileSystemStorage:
    @pytest.mark.asyncio
    async def test_save_and_get(self, tmp_path):
        """Test simple save and retrieval using temporary directory"""
        storage = FileSystemStorage(base_path=tmp_path)
        data = b"test filesystem data"
        file_id = "test_file.txt"
        
        # Test Save
        saved_id = await storage.save(file_id, data, "text/plain")
        assert saved_id == file_id
        assert (tmp_path / file_id).exists()
        assert (tmp_path / file_id).read_bytes() == data
        
        # Test Get
        retrieved_data = await storage.get(file_id)
        assert retrieved_data == data

    @pytest.mark.asyncio
    async def test_delete(self, tmp_path):
        """Test deletion"""
        storage = FileSystemStorage(base_path=tmp_path)
        data = b"delete me"
        file_id = "delete_test.txt"
        
        await storage.save(file_id, data, "text/plain")
        assert (tmp_path / file_id).exists()
        
        # Test Delete
        assert await storage.delete(file_id) is True
        assert not (tmp_path / file_id).exists()
        
        # Delete non-existent
        assert await storage.delete(file_id) is False

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked"""
        storage = FileSystemStorage(base_path=tmp_path)
        data = b"hacker data"
        
        with pytest.raises(ValueError, match="Invalid file_id"):
            await storage.save("../hack.txt", data, "text/plain")
            
        with pytest.raises(ValueError, match="Invalid file_id"):
            await storage.save("subdir/hack.txt", data, "text/plain")

    @pytest.mark.asyncio
    async def test_get_non_existent(self, tmp_path):
        """Test getting non-existent file"""
        storage = FileSystemStorage(base_path=tmp_path)
        
        with pytest.raises(FileNotFoundError):
            await storage.get("phantom.txt")
