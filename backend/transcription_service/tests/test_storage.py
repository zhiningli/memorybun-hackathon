"""
Tests for Storage Providers
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from services.storage.factory import get_storage_provider
from services.storage.local import LocalStorageProvider
from services.storage.s3 import S3StorageProvider

# ==================== Local Storage Tests ====================

@pytest.mark.asyncio
async def test_local_storage_save_get_delete(tmp_path):
    """Test full lifecycle of local storage."""
    base_url = "http://testserver"
    provider = LocalStorageProvider(base_path=tmp_path, base_url=base_url)
    
    filename = "test.txt"
    data = b"Hello World"
    
    # Save
    key = await provider.save(filename, data)
    assert key == filename
    assert (tmp_path / filename).exists()
    
    # Get
    read_data = await provider.get(key)
    assert read_data == data
    
    # Public URL
    url = provider.get_public_url(key)
    assert url == f"{base_url}/api/v1/transcribe/screenshots/{filename}"
    
    # Delete
    deleted = await provider.delete(key)
    assert deleted is True
    assert not (tmp_path / filename).exists()
    
    # Delete non-existent
    deleted = await provider.delete("fake.txt")
    assert deleted is False

# ==================== S3 Storage Tests ====================

@pytest.mark.asyncio
async def test_s3_storage_provider_init():
    """Test S3 provider initialization."""
    with patch("boto3.client") as mock_boto:
        provider = S3StorageProvider("my-bucket", "us-east-1", prefix="test/")
        assert provider.bucket_name == "my-bucket"
        assert provider.prefix == "test/"
        mock_boto.assert_called_with("s3", region_name="us-east-1")

@pytest.mark.asyncio
async def test_s3_storage_save():
    """Test S3 save operation."""
    with patch("boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        provider = S3StorageProvider("my-bucket", "us-east-1")
        
        # Test save
        await provider.save("file.png", b"data", "image/png")
        
        # Verify put_object called (async wrapper calls sync method)
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args[1]
        assert call_args["Bucket"] == "my-bucket"
        assert call_args["Key"] == "file.png"
        assert call_args["Body"] == b"data"
        assert call_args["ContentType"] == "image/png"

@pytest.mark.asyncio
async def test_s3_storage_public_url():
    """Test S3 public URL generation."""
    with patch("boto3.client"):
        provider = S3StorageProvider("my-bucket", "us-east-1")
        url = provider.get_public_url("folder/image.png")
        assert url == "https://my-bucket.s3.us-east-1.amazonaws.com/folder/image.png"

# ==================== Factory Tests ====================

def test_storage_factory(tmp_path):
    """Test factory creates correct instances."""
    # Local
    local = get_storage_provider("FILESYSTEM", base_path=tmp_path, base_url="http://loc")
    assert isinstance(local, LocalStorageProvider)
    
    # S3
    with patch("boto3.client"):
        s3 = get_storage_provider("S3", s3_bucket="b", s3_region="r")
        assert isinstance(s3, S3StorageProvider)
    
    # Invalid
    with pytest.raises(ValueError):
        get_storage_provider("UNKNOWN")
